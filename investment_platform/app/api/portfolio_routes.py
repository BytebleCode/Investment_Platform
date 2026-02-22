"""
Portfolio API Routes

Endpoints for managing portfolio state including settings, cash, and reset.
"""
from flask import Blueprint, jsonify, request, g
from datetime import datetime, timedelta, timezone
from app.database import is_csv_backend, get_csv_storage, get_scoped_session
from app.models import PortfolioState, Holdings, TradesHistory, StrategyCustomization
from app.data.strategies import STRATEGY_IDS, DEFAULT_CUSTOMIZATION
from app.api.auth_routes import login_required

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/settings', methods=['GET'])
@login_required
def get_settings():
    """
    GET /api/portfolio/settings
    Returns current portfolio configuration.
    """
    portfolio = PortfolioState.get_or_create(g.current_user_id)
    if isinstance(portfolio, dict):
        return jsonify(portfolio)
    return jsonify(portfolio.to_dict())


@portfolio_bp.route('/initialize', methods=['POST'])
@login_required
def initialize_portfolio():
    """
    POST /api/portfolio/initialize
    Initialize or reinitialize the portfolio with default settings.
    Also creates default strategy customizations.
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = g.current_user_id
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

            # Create default strategy customizations
            for strategy_id in STRATEGY_IDS:
                existing = storage.get_strategy_customization(user_id, strategy_id)
                if not existing:
                    storage.upsert_strategy_customization(
                        user_id,
                        strategy_id,
                        **DEFAULT_CUSTOMIZATION
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

            # Create default strategy customizations
            for strategy_id in STRATEGY_IDS:
                StrategyCustomization.upsert(user_id, strategy_id, **DEFAULT_CUSTOMIZATION)

            db.session.commit()
            return jsonify({
                'message': 'Portfolio initialized',
                'portfolio': portfolio.to_dict()
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/settings', methods=['PUT'])
@login_required
def update_settings():
    """
    PUT /api/portfolio/settings
    Updates portfolio settings.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = g.current_user_id

    try:
        if is_csv_backend():
            storage = get_csv_storage()
            # Build update dict from allowed fields
            update_data = {}
            allowed_fields = ['initial_value', 'current_strategy', 'is_initialized']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]

            if update_data:
                storage.update_portfolio(user_id, **update_data)

            portfolio = storage.get_portfolio(user_id)
            return jsonify(portfolio)
        else:
            portfolio = PortfolioState.get_or_create(user_id)

            # Update allowed fields
            allowed_fields = ['initial_value', 'current_strategy', 'is_initialized']
            for field in allowed_fields:
                if field in data:
                    setattr(portfolio, field, data[field])

            session = get_scoped_session()
            if session:
                session.commit()
            return jsonify(portfolio.to_dict())
    except Exception as e:
        if not is_csv_backend():
            session = get_scoped_session()
            if session:
                session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/cash', methods=['PUT'])
@login_required
def update_cash():
    """
    PUT /api/portfolio/cash
    Updates cash balance.
    """
    data = request.get_json()
    if not data or 'current_cash' not in data:
        return jsonify({'error': 'current_cash is required'}), 400

    user_id = g.current_user_id

    try:
        if is_csv_backend():
            storage = get_csv_storage()
            storage.update_portfolio(user_id, current_cash=data['current_cash'])
            portfolio = storage.get_portfolio(user_id)
            return jsonify({'current_cash': float(portfolio.get('current_cash', 0))})
        else:
            portfolio = PortfolioState.get_or_create(user_id)
            portfolio.current_cash = data['current_cash']

            session = get_scoped_session()
            if session:
                session.commit()
            return jsonify({'current_cash': float(portfolio.current_cash)})
    except Exception as e:
        if not is_csv_backend():
            session = get_scoped_session()
            if session:
                session.rollback()
        return jsonify({'error': str(e)}), 500


@portfolio_bp.route('/reset', methods=['POST'])
@login_required
def reset_portfolio():
    """
    POST /api/portfolio/reset
    Resets portfolio to initial state, clearing all holdings and trades.
    """
    user_id = g.current_user_id

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


@portfolio_bp.route('/performance', methods=['GET'])
@login_required
def get_performance():
    """
    GET /api/portfolio/performance
    Returns time-series data for portfolio performance charting.

    Query params:
        - period: 1d, 1w, 1m, 3m, 1y, all (default: 1m)
    """
    user_id = g.current_user_id
    period = request.args.get('period', '1m')

    # Calculate date range based on period
    now = datetime.now(timezone.utc)
    period_days = {
        '1d': 1,
        '1w': 7,
        '1m': 30,
        '3m': 90,
        '1y': 365,
        'all': 3650  # approx 10 years
    }
    days = period_days.get(period, 30)
    start_date = now - timedelta(days=days)

    try:
        # Get portfolio info
        if is_csv_backend():
            storage = get_csv_storage()
            portfolio = storage.get_portfolio(user_id)
            trades = storage.get_trades(user_id, limit=500)
            holdings = storage.get_holdings(user_id)
        else:
            portfolio = PortfolioState.get_or_create(user_id)
            if hasattr(portfolio, 'to_dict'):
                portfolio = portfolio.to_dict()
            trades = TradesHistory.get_user_trades(user_id, limit=500)
            if trades and hasattr(trades[0], 'to_dict'):
                trades = [t.to_dict() for t in trades]
            holdings_obj = Holdings.get_user_holdings(user_id)
            if holdings_obj and hasattr(holdings_obj[0], 'to_dict'):
                holdings = [h.to_dict() for h in holdings_obj]
            else:
                holdings = holdings_obj or []

        # Get initial values
        initial_value = float(portfolio.get('initial_value', 100000) if isinstance(portfolio, dict) else 100000)
        current_cash = float(portfolio.get('current_cash', initial_value) if isinstance(portfolio, dict) else initial_value)

        # Calculate holdings value
        holdings_value = 0
        if holdings:
            for h in holdings:
                qty = float(h.get('quantity', 0) if isinstance(h, dict) else 0)
                cost = float(h.get('avg_cost', 0) if isinstance(h, dict) else 0)
                holdings_value += qty * cost

        current_total = current_cash + holdings_value

        # Build equity curve from trades
        # Start with initial value, then apply each trade
        equity_curve = []
        trade_markers = []

        # Filter trades within date range and sort chronologically
        filtered_trades = []
        for t in trades:
            ts = t.get('timestamp') if isinstance(t, dict) else t.timestamp
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    continue
            if ts and ts >= start_date:
                filtered_trades.append(t)

        filtered_trades.sort(key=lambda x: x.get('timestamp') if isinstance(x, dict) else x.timestamp)

        # Build timeline
        running_cash = initial_value
        running_holdings_value = 0

        # Add starting point
        equity_curve.append({
            'date': start_date.isoformat(),
            'value': initial_value,
            'cash': initial_value,
            'holdings': 0
        })

        # Process each trade
        for t in filtered_trades:
            ts = t.get('timestamp') if isinstance(t, dict) else t.timestamp
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))

            trade_type = t.get('type') if isinstance(t, dict) else t.type
            total = float(t.get('total', 0) if isinstance(t, dict) else t.total or 0)
            symbol = t.get('symbol') if isinstance(t, dict) else t.symbol
            qty = float(t.get('quantity', 0) if isinstance(t, dict) else t.quantity or 0)
            price = float(t.get('price', 0) if isinstance(t, dict) else t.price or 0)

            if trade_type == 'buy':
                running_cash -= total
                running_holdings_value += total
            else:  # sell
                running_cash += total
                running_holdings_value -= total
                if running_holdings_value < 0:
                    running_holdings_value = 0

            portfolio_value = running_cash + running_holdings_value

            equity_curve.append({
                'date': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                'value': portfolio_value,
                'cash': running_cash,
                'holdings': running_holdings_value
            })

            trade_markers.append({
                'date': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                'type': trade_type,
                'symbol': symbol,
                'quantity': qty,
                'price': price,
                'value': portfolio_value
            })

        # Add current point if different from last
        equity_curve.append({
            'date': now.isoformat(),
            'value': current_total,
            'cash': current_cash,
            'holdings': holdings_value
        })

        # Calculate performance metrics
        if len(equity_curve) > 1:
            start_val = equity_curve[0]['value']
            end_val = equity_curve[-1]['value']
            total_return = ((end_val - start_val) / start_val) * 100 if start_val > 0 else 0

            # Calculate max drawdown
            peak = start_val
            max_drawdown = 0
            for point in equity_curve:
                val = point['value']
                if val > peak:
                    peak = val
                drawdown = ((peak - val) / peak) * 100 if peak > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            total_return = 0
            max_drawdown = 0

        return jsonify({
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': now.isoformat(),
            'initial_value': initial_value,
            'current_value': current_total,
            'metrics': {
                'total_return': round(total_return, 2),
                'max_drawdown': round(-max_drawdown, 2),
                'total_trades': len(trade_markers)
            },
            'equity_curve': equity_curve,
            'trades': trade_markers
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
