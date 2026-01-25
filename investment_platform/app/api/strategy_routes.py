"""
Strategy API Routes

Endpoints for managing investment strategy customizations.
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models import StrategyCustomization

strategy_bp = Blueprint('strategies', __name__)


@strategy_bp.route('/customizations', methods=['GET'])
def get_customizations():
    """
    GET /api/strategies/customizations
    Returns all strategy customizations for the user.
    """
    user_id = request.args.get('user_id', 'default')
    customizations = StrategyCustomization.get_user_customizations(user_id)

    return jsonify({
        'customizations': [c.to_dict() for c in customizations]
    })


@strategy_bp.route('/customizations/<strategy_id>', methods=['GET'])
def get_customization(strategy_id):
    """
    GET /api/strategies/customizations/<strategy_id>
    Get customization for a specific strategy.
    """
    user_id = request.args.get('user_id', 'default')
    customization = StrategyCustomization.get_customization(user_id, strategy_id)

    if not customization:
        return jsonify({'error': f'No customization found for {strategy_id}'}), 404

    return jsonify(customization.to_dict())


@strategy_bp.route('/customizations/<strategy_id>', methods=['PUT'])
def update_customization(strategy_id):
    """
    PUT /api/strategies/customizations/<strategy_id>
    Create or update strategy customization.

    Validated parameters:
        - confidence_level: 10-100
        - trade_frequency: low/medium/high
        - max_position_size: 5-50
        - stop_loss_percent: 5-30
        - take_profit_percent: 10-100
        - auto_rebalance: boolean
        - reinvest_dividends: boolean
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id', 'default')

    # Extract customization parameters
    params = {}
    allowed_fields = [
        'confidence_level', 'trade_frequency', 'max_position_size',
        'stop_loss_percent', 'take_profit_percent', 'auto_rebalance',
        'reinvest_dividends'
    ]

    for field in allowed_fields:
        if field in data:
            # Convert boolean fields
            if field in ['auto_rebalance', 'reinvest_dividends']:
                params[field] = 1 if data[field] else 0
            else:
                params[field] = data[field]

    try:
        customization = StrategyCustomization.upsert(user_id, strategy_id, **params)
        db.session.commit()
        return jsonify(customization.to_dict())
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
