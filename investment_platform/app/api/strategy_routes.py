"""
Strategy API Routes

Endpoints for managing investment strategies, including:
- System strategies (read-only templates)
- User-created custom strategies (full CRUD)
- Strategy customizations (limited tweaks for system strategies)
"""
from flask import Blueprint, jsonify, request
from app.database import is_csv_backend, get_scoped_session
from app.models import StrategyCustomization
from app.data.strategies import STRATEGIES, STRATEGY_IDS, DEFAULT_CUSTOMIZATION
from app.services.strategy_service import StrategyService
from app.services.available_symbols import search_symbols, get_all_symbols

strategy_bp = Blueprint('strategies', __name__)


@strategy_bp.route('', methods=['GET'])
def get_strategies():
    """
    GET /api/strategies
    Returns all available investment strategies (system + user).
    """
    user_id = request.args.get('user_id', 'default')
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    service = StrategyService(user_id)
    strategies = service.get_all_strategies(include_inactive)

    return jsonify({
        'strategies': strategies,
        'count': len(strategies)
    })


@strategy_bp.route('', methods=['POST'])
def create_strategy():
    """
    POST /api/strategies
    Create a new custom user strategy.

    Request body:
    {
        "name": "My Strategy",
        "description": "A custom strategy",
        "color": "#3b82f6",
        "risk_level": 3,
        "expected_return_min": 5,
        "expected_return_max": 15,
        "volatility": 0.01,
        "daily_drift": 0.00035,
        "trade_frequency_seconds": 75,
        "target_investment_ratio": 0.7,
        "max_position_pct": 0.15,
        "stop_loss_percent": 10,
        "take_profit_percent": 20,
        "auto_rebalance": true,
        "stocks": ["AAPL", "MSFT", "GOOGL"]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id', 'default')
    service = StrategyService(user_id)

    try:
        strategy = service.create_strategy(data)
        return jsonify({
            'message': 'Strategy created successfully',
            'strategy': strategy
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """
    GET /api/strategies/<strategy_id>
    Get a specific strategy with its stocks.
    """
    user_id = request.args.get('user_id', 'default')
    service = StrategyService(user_id)

    strategy = service.get_strategy(strategy_id)
    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    return jsonify(strategy)


@strategy_bp.route('/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """
    PUT /api/strategies/<strategy_id>
    Update a user strategy.

    Note: System strategies cannot be modified. Clone them instead.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id', 'default')
    service = StrategyService(user_id)

    try:
        strategy = service.update_strategy(strategy_id, data)
        return jsonify({
            'message': 'Strategy updated successfully',
            'strategy': strategy
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """
    DELETE /api/strategies/<strategy_id>
    Archive a user strategy.

    Query params:
        - hard_delete: If "true", permanently delete instead of archiving
    """
    user_id = request.args.get('user_id', 'default')
    hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'

    service = StrategyService(user_id)

    try:
        service.delete_strategy(strategy_id, hard_delete)
        return jsonify({
            'message': f'Strategy "{strategy_id}" {"deleted" if hard_delete else "archived"} successfully'
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/clone', methods=['POST'])
def clone_strategy(strategy_id):
    """
    POST /api/strategies/<strategy_id>/clone
    Clone a strategy (system or user) to a new user strategy.

    Request body:
    {
        "name": "My Cloned Strategy"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    new_name = data.get('name')
    if not new_name:
        return jsonify({'error': 'New strategy name is required'}), 400

    user_id = data.get('user_id', 'default')
    service = StrategyService(user_id)

    try:
        strategy = service.clone_strategy(strategy_id, new_name)
        return jsonify({
            'message': 'Strategy cloned successfully',
            'strategy': strategy
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/symbols', methods=['GET'])
def search_available_symbols():
    """
    GET /api/strategies/symbols
    Search for available stock symbols.

    Query params:
        - q: Search query (matches start of symbol)
        - limit: Maximum results (default 20)
    """
    query = request.args.get('q', '')
    limit = min(int(request.args.get('limit', 20)), 50)

    if not query:
        # Return a sample of symbols if no query
        symbols = get_all_symbols()[:limit]
    else:
        symbols = search_symbols(query, limit)

    return jsonify({
        'symbols': symbols,
        'count': len(symbols)
    })


# ===== Legacy Customizations Endpoints =====
# These are kept for backward compatibility with the existing UI

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
        # Return default customization
        strategy = STRATEGIES.get(strategy_id, {})
        return jsonify({
            'user_id': user_id,
            'strategy_id': strategy_id,
            'confidence_level': DEFAULT_CUSTOMIZATION.get('confidence_level', 50),
            'trade_frequency': DEFAULT_CUSTOMIZATION.get('trade_frequency', 'medium'),
            'max_position_size': DEFAULT_CUSTOMIZATION.get('max_position_size', 15),
            'stop_loss_percent': DEFAULT_CUSTOMIZATION.get('stop_loss_percent', 10),
            'take_profit_percent': DEFAULT_CUSTOMIZATION.get('take_profit_percent', 20),
            'auto_rebalance': DEFAULT_CUSTOMIZATION.get('auto_rebalance', True),
            'reinvest_dividends': DEFAULT_CUSTOMIZATION.get('reinvest_dividends', True),
        })

    if isinstance(customization, dict):
        return jsonify(customization)
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

        # Commit if using SQL backend
        if not is_csv_backend():
            session = get_scoped_session()
            if session:
                session.commit()

        if isinstance(customization, dict):
            return jsonify(customization)
        return jsonify(customization.to_dict())
    except ValueError as e:
        if not is_csv_backend():
            session = get_scoped_session()
            if session:
                session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        if not is_csv_backend():
            session = get_scoped_session()
            if session:
                session.rollback()
        return jsonify({'error': str(e)}), 500
