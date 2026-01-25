"""
Portfolio API Routes

Endpoints for managing portfolio state including settings, cash, and reset.
"""
from flask import Blueprint, jsonify, request
from app.database import is_csv_backend, get_csv_storage, get_scoped_session
from app.models import PortfolioState, Holdings, TradesHistory

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/settings', methods=['GET'])
def get_settings():
    """
    GET /api/portfolio/settings
    Returns current portfolio configuration.
    """
    portfolio = PortfolioState.get_or_create()
    if isinstance(portfolio, dict):
        return jsonify(portfolio)
    return jsonify(portfolio.to_dict())


@portfolio_bp.route('/initialize', methods=['POST'])
def initialize_portfolio():
    """
    POST /api/portfolio/initialize
    Initialize or reinitialize the portfolio with default settings.
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id', 'default')
        initial_value = float(data.get('initial_value', 100000.00))

        if is_csv_backend():
            storage = get_csv_storage()
            portfolio = storage.get_portfolio(user_id)
            if portfolio:
                storage.update_portfolio(
                    user_id,
                    initial_value=initial_value,
                    current_cash=initial_value,
                    is_initialized=1,
                    realized_gains=0
                )
            else:
                storage.create_portfolio(
                    user_id,
                    initial_value=initial_value,
                    current_cash=initial_value,
                    is_initialized=1
                )
            portfolio = storage.get_portfolio(user_id)
            # Convert Decimal to float for JSON serialization
            if portfolio:
                for key in ['initial_value', 'current_cash', 'realized_gains']:
                    if key in portfolio and portfolio[key] is not None:
                        portfolio[key] = float(portfolio[key])
            return jsonify({
                'message': 'Portfolio initialized',
                'portfolio': portfolio
            })
        else:
            from app import db
            portfolio = PortfolioState.get_or_create(user_id)
            portfolio.initial_value = initial_value
            portfolio.current_cash = initial_value
            portfolio.is_initialized = 1
            portfolio.realized_gains = 0
            db.session.commit()
            return jsonify({
                'message': 'Portfolio initialized',
                'portfolio': portfolio.to_dict()
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/settings', methods=['PUT'])
def update_settings():
    """
    PUT /api/portfolio/settings
    Updates portfolio settings.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    portfolio = PortfolioState.get_or_create()

    # Update allowed fields
    allowed_fields = ['initial_value', 'current_strategy', 'is_initialized']
    for field in allowed_fields:
        if field in data:
            setattr(portfolio, field, data[field])

    try:
        db.session.commit()
        return jsonify(portfolio.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/cash', methods=['PUT'])
def update_cash():
    """
    PUT /api/portfolio/cash
    Updates cash balance.
    """
    data = request.get_json()
    if not data or 'current_cash' not in data:
        return jsonify({'error': 'current_cash is required'}), 400

    portfolio = PortfolioState.get_or_create()
    portfolio.current_cash = data['current_cash']

    try:
        db.session.commit()
        return jsonify({'current_cash': float(portfolio.current_cash)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/reset', methods=['POST'])
def reset_portfolio():
    """
    POST /api/portfolio/reset
    Resets portfolio to initial state, clearing all holdings and trades.
    """
    data = request.get_json() or {}
    user_id = data.get('user_id', request.args.get('user_id', 'default'))

    try:
        # Delete holdings and trades
        Holdings.delete_user_holdings(user_id)
        TradesHistory.delete_user_trades(user_id)

        if is_csv_backend():
            storage = get_csv_storage()
            portfolio = storage.get_portfolio(user_id)
            if portfolio:
                storage.update_portfolio(
                    user_id,
                    current_cash=portfolio.get('initial_value', 100000),
                    realized_gains=0,
                    is_initialized=0
                )
            portfolio = storage.get_portfolio(user_id)
            return jsonify({'message': 'Portfolio reset successfully', 'portfolio': portfolio})
        else:
            from app import db
            portfolio = PortfolioState.get_or_create(user_id)
            portfolio.reset()
            db.session.commit()
            return jsonify({'message': 'Portfolio reset successfully', 'portfolio': portfolio.to_dict()})
    except Exception as e:
        if not is_csv_backend():
            from app import db
            db.session.rollback()
        return jsonify({'error': str(e)}), 500
