"""
Strategy API Routes

Endpoints for managing investment strategy customizations.
"""
from flask import Blueprint, jsonify, request
from app.database import is_csv_backend
from app.models import StrategyCustomization
from app.data.strategies import STRATEGIES, STRATEGY_IDS

strategy_bp = Blueprint('strategies', __name__)


@strategy_bp.route('', methods=['GET'])
def get_strategies():
    """
    GET /api/strategies
    Returns all available investment strategies.
    """
    strategies_list = []
    for strategy_id in STRATEGY_IDS:
        strategy = STRATEGIES.get(strategy_id, {})
        strategies_list.append({
            'id': strategy_id,
            'name': strategy.get('name', strategy_id.title()),
            'description': strategy.get('description', ''),
            'risk_level': strategy.get('risk_level', 3),
            'expected_return': strategy.get('expected_return', (0, 0)),
            'stocks': strategy.get('stocks', []),
            'color': strategy.get('color', '#3b82f6')
        })

    return jsonify({
        'strategies': strategies_list,
        'count': len(strategies_list)
    })


@strategy_bp.route('/customizations', methods=['GET'])
def get_customizations():
    """
    GET /api/strategies/customizations
    Returns all strategy customizations for the user.
    Returns all strategies with default values merged with user customizations.
    """
    user_id = request.args.get('user_id', 'default')
    customizations = StrategyCustomization.get_user_customizations(user_id)

    # CSV backend returns dicts, DB backend returns objects
    if customizations and isinstance(customizations[0], dict):
        user_customs = {c['strategy_id']: c for c in customizations}
    elif customizations:
        user_customs = {c.strategy_id: c.to_dict() for c in customizations}
    else:
        user_customs = {}

    # Build list with all strategies, merging user customizations
    from app.data.strategies import DEFAULT_CUSTOMIZATION
    customizations_list = []

    for strategy_id in STRATEGY_IDS:
        strategy = STRATEGIES.get(strategy_id, {})

        if strategy_id in user_customs:
            # Use user's customization
            customizations_list.append(user_customs[strategy_id])
        else:
            # Use default customization
            customizations_list.append({
                'user_id': user_id,
                'strategy_id': strategy_id,
                'confidence_level': DEFAULT_CUSTOMIZATION.get('confidence_level', 50),
                'trade_frequency': DEFAULT_CUSTOMIZATION.get('trade_frequency', 'medium'),
                'max_position_size': DEFAULT_CUSTOMIZATION.get('max_position_size', 15),
                'stop_loss_percent': DEFAULT_CUSTOMIZATION.get('stop_loss_percent', 10),
                'take_profit_percent': DEFAULT_CUSTOMIZATION.get('take_profit_percent', 20),
                'auto_rebalance': DEFAULT_CUSTOMIZATION.get('auto_rebalance', True),
                'reinvest_dividends': DEFAULT_CUSTOMIZATION.get('reinvest_dividends', True),
                'name': strategy.get('name', strategy_id.title()),
                'description': strategy.get('description', ''),
                'risk_level': strategy.get('risk_level', 3),
                'color': strategy.get('color', '#3b82f6')
            })

    return jsonify({
        'customizations': customizations_list
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
