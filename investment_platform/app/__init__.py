"""
Investment Platform - Flask Application Factory
"""
import os
from flask import Flask, send_from_directory

from app.database import init_db, create_all, close_session, get_scoped_session

# For backward compatibility - db.session can still be used
class DBCompat:
    """Compatibility layer for db.session usage."""

    @property
    def session(self):
        return get_scoped_session()

db = DBCompat()


def create_app(config_class=None):
    """
    Application factory pattern for Flask app.

    Args:
        config_class: Configuration class to use. Defaults to Config.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        from app.config import Config
        config_class = Config
    # Instantiate config class so that @property decorators work
    app.config.from_object(config_class())

    # Initialize database
    init_db(app)

    # Initialize security (includes CORS, session security, headers, rate limiting)
    from app.security import configure_security
    configure_security(app)

    # Register blueprints
    from app.api.portfolio_routes import portfolio_bp
    from app.api.holdings_routes import holdings_bp
    from app.api.trades_routes import trades_bp
    from app.api.strategy_routes import strategy_bp
    from app.api.market_data_routes import market_data_bp
    from app.api.trading_routes import trading_bp
    from app.api.health_routes import health_bp
    from app.api.backtest_routes import backtest_bp
    from app.api.auth_routes import auth_bp

    app.register_blueprint(portfolio_bp, url_prefix='/api/portfolio')
    app.register_blueprint(holdings_bp, url_prefix='/api/holdings')
    app.register_blueprint(trades_bp, url_prefix='/api/trades')
    app.register_blueprint(strategy_bp, url_prefix='/api/strategies')
    app.register_blueprint(market_data_bp, url_prefix='/api/market')
    app.register_blueprint(trading_bp, url_prefix='/api/trading')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(backtest_bp, url_prefix='/api/backtest')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # Create database tables
    create_all()

    # Seed sample account for demo
    seed_sample_account()

    # Serve static HTML frontend
    static_folder = os.path.join(os.path.dirname(__file__), 'static')

    @app.route('/')
    def index():
        return send_from_directory(static_folder, 'index.html')

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(static_folder, filename)

    # Teardown - close session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_session()

    # Register error handlers
    register_error_handlers(app)

    # Setup logging
    setup_logging(app)

    return app


def seed_sample_account():
    """Create a pre-seeded sample account for demo purposes."""
    from app.database import is_csv_backend, get_csv_storage
    from app.models.user import User
    from decimal import Decimal
    from datetime import datetime, timezone

    try:
        existing = User.get_by_username('sample')
        if existing:
            return  # Already seeded

        user = User.create('sample', 'sample123')
        sample_user_id = str(user['id'])

        if is_csv_backend():
            storage = get_csv_storage()
            storage.create_portfolio(
                sample_user_id,
                initial_value=Decimal('100000.00'),
                current_cash=Decimal('65210.00'),
                is_initialized=1,
                realized_gains=Decimal('0.00')
            )

            now = datetime.now(timezone.utc)
            holdings = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'technology', 'quantity': Decimal('50'), 'avg_cost': Decimal('178.00')},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'technology', 'quantity': Decimal('30'), 'avg_cost': Decimal('410.00')},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'technology', 'quantity': Decimal('20'), 'avg_cost': Decimal('165.00')},
            ]
            for h in holdings:
                storage.create_holding(sample_user_id, h['symbol'], **{k: v for k, v in h.items() if k != 'symbol'})

            trades = [
                {'trade_id': 'sample-001', 'type': 'buy', 'symbol': 'AAPL', 'stock_name': 'Apple Inc.', 'quantity': Decimal('50'), 'price': Decimal('178.00'), 'total': Decimal('8900.00'), 'strategy': 'balanced'},
                {'trade_id': 'sample-002', 'type': 'buy', 'symbol': 'MSFT', 'stock_name': 'Microsoft Corp.', 'quantity': Decimal('30'), 'price': Decimal('410.00'), 'total': Decimal('12300.00'), 'strategy': 'balanced'},
                {'trade_id': 'sample-003', 'type': 'buy', 'symbol': 'GOOGL', 'stock_name': 'Alphabet Inc.', 'quantity': Decimal('20'), 'price': Decimal('165.00'), 'total': Decimal('3300.00'), 'strategy': 'balanced'},
            ]
            for t in trades:
                storage.create_trade(user_id=sample_user_id, **t)
        else:
            from app import db
            from app.models import PortfolioState, Holdings, TradesHistory
            portfolio = PortfolioState(
                user_id=sample_user_id,
                initial_value=Decimal('100000.00'),
                current_cash=Decimal('65210.00'),
                is_initialized=1
            )
            db.session.add(portfolio)

            for symbol, name, qty, cost in [('AAPL', 'Apple Inc.', 50, 178), ('MSFT', 'Microsoft Corp.', 30, 410), ('GOOGL', 'Alphabet Inc.', 20, 165)]:
                db.session.add(Holdings(user_id=sample_user_id, symbol=symbol, name=name, sector='technology', quantity=qty, avg_cost=cost))

            db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Could not seed sample account: {e}')


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500


def setup_logging(app):
    """Configure application logging."""
    import logging
    from logging.handlers import RotatingFileHandler
    import os

    if not app.debug:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/investment_platform.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Investment Platform startup')
