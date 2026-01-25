"""
Portfolio API Routes

Endpoints for managing portfolio state including settings, cash, and reset.
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models import PortfolioState, Holdings, TradesHistory

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/settings', methods=['GET'])
def get_settings():
    """
    GET /api/portfolio/settings
    Returns current portfolio configuration.
    """
    portfolio = PortfolioState.get_or_create()
    return jsonify(portfolio.to_dict())


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
    user_id = request.args.get('user_id', 'default')

    try:
        # Delete holdings and trades
        Holdings.delete_user_holdings(user_id)
        TradesHistory.delete_user_trades(user_id)

        # Reset portfolio state
        portfolio = PortfolioState.get_or_create(user_id)
        portfolio.reset()

        db.session.commit()
        return jsonify({'message': 'Portfolio reset successfully', 'portfolio': portfolio.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
