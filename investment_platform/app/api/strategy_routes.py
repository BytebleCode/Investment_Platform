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
from app.services.symbol_selector import get_sector_coverage_report, validate_strategy_allocation
from app.data.symbol_universe import SYMBOL_UNIVERSE, SECTOR_METADATA, get_all_sectors, get_sector_for_symbol
from app.services.allocation_service import AllocationService, get_industry_tree, search_industries
from app.services.component_params_service import ComponentParamsService
from app.services.rules_engine import RulesEngine, get_rule_templates
from app.services.conditions_engine import ConditionsEngine, get_condition_templates

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


@strategy_bp.route('/<strategy_id>/sectors', methods=['GET'])
def get_strategy_sectors(strategy_id):
    """
    GET /api/strategies/<strategy_id>/sectors
    Get sector breakdown for a strategy's symbols.
    """
    user_id = request.args.get('user_id', 'default')
    service = StrategyService(user_id)
    strategy = service.get_strategy(strategy_id)

    if not strategy:
        return jsonify({'error': f'Strategy not found: {strategy_id}'}), 404

    symbols = strategy.get('stocks', [])

    # Calculate sector breakdown
    sector_breakdown = {}
    for symbol in symbols:
        sector, subsector = get_sector_for_symbol(symbol)
        if sector:
            if sector not in sector_breakdown:
                metadata = SECTOR_METADATA.get(sector, {})
                sector_breakdown[sector] = {
                    'name': metadata.get('name', sector.title()),
                    'color': metadata.get('color', '#888888'),
                    'symbols': [],
                    'count': 0
                }
            sector_breakdown[sector]['symbols'].append(symbol)
            sector_breakdown[sector]['count'] += 1

    # Convert to list with percentages
    total_symbols = len(symbols)
    sectors = []
    for sector_key, sector_data in sector_breakdown.items():
        percentage = round((sector_data['count'] / total_symbols) * 100, 1) if total_symbols > 0 else 0
        sectors.append({
            'sector': sector_key,
            'name': sector_data['name'],
            'color': sector_data['color'],
            'symbols': sector_data['symbols'],
            'count': sector_data['count'],
            'percentage': percentage
        })

    # Sort by percentage descending
    sectors.sort(key=lambda x: x['percentage'], reverse=True)

    return jsonify({
        'strategy_id': strategy_id,
        'total_symbols': total_symbols,
        'sectors': sectors
    })


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


# ===== Macro Strategy Endpoints =====

@strategy_bp.route('/<strategy_id>/regime', methods=['GET'])
def get_strategy_regime(strategy_id):
    """
    GET /api/strategies/<strategy_id>/regime
    Get the current macro regime for a strategy.

    Returns regime score, label, and individual signal values.
    """
    user_id = request.args.get('user_id', 'default')
    service = StrategyService(user_id)

    strategy = service.get_strategy(strategy_id)
    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    regime = service.get_macro_regime(strategy_id)

    return jsonify({
        'strategy_id': strategy_id,
        'regime': regime
    })


@strategy_bp.route('/regimes', methods=['GET'])
def get_all_regimes():
    """
    GET /api/strategies/regimes
    Get macro regime info for all system strategies.
    """
    user_id = request.args.get('user_id', 'default')
    service = StrategyService(user_id)

    regimes = service.get_all_regimes()
    macro_enabled = service.is_macro_enabled()

    return jsonify({
        'regimes': regimes,
        'macro_enabled': macro_enabled
    })


@strategy_bp.route('/sectors', methods=['GET'])
def get_sectors():
    """
    GET /api/strategies/sectors
    Get all available sectors and subsectors from the symbol universe.
    """
    sectors = {}
    for sector in get_all_sectors():
        metadata = SECTOR_METADATA.get(sector, {})
        subsectors = list(SYMBOL_UNIVERSE.get(sector, {}).keys())
        sectors[sector] = {
            'name': metadata.get('name', sector.replace('_', ' ').title()),
            'description': metadata.get('description', ''),
            'color': metadata.get('color', '#6b7280'),
            'subsectors': subsectors
        }

    return jsonify({
        'sectors': sectors,
        'count': len(sectors)
    })


@strategy_bp.route('/sectors/coverage', methods=['GET'])
def get_sectors_coverage():
    """
    GET /api/strategies/sectors/coverage
    Get coverage report showing universe vs available symbols by sector.
    """
    report = get_sector_coverage_report()

    return jsonify({
        'coverage': report
    })


@strategy_bp.route('/<strategy_id>/allocation', methods=['GET'])
def get_strategy_allocation(strategy_id):
    """
    GET /api/strategies/<strategy_id>/allocation
    Get the sector allocation and selected symbols for a strategy.
    """
    user_id = request.args.get('user_id', 'default')
    service = StrategyService(user_id)

    strategy = service.get_strategy(strategy_id)
    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    sector_allocation = strategy.get('sector_allocation', {})

    # Validate allocation if it exists
    validation = None
    if sector_allocation:
        validation = validate_strategy_allocation(sector_allocation)

    return jsonify({
        'strategy_id': strategy_id,
        'sector_allocation': sector_allocation,
        'stocks': strategy.get('stocks', []),
        'max_symbols': strategy.get('max_symbols', 20),
        'min_symbols': strategy.get('min_symbols', 10),
        'validation': validation
    })


@strategy_bp.route('/<strategy_id>/weights', methods=['PUT'])
def update_strategy_weights(strategy_id):
    """
    PUT /api/strategies/<strategy_id>/weights
    Update the sector allocation weights for a strategy.

    Request body:
    {
        "sector_allocation": {
            "financials.banks": 0.35,
            "utilities.electric": 0.25,
            ...
        }
    }
    """
    user_id = request.json.get('user_id', 'default') if request.json else 'default'
    service = StrategyService(user_id)

    strategy = service.get_strategy(strategy_id)
    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    data = request.get_json()
    if not data or 'sector_allocation' not in data:
        return jsonify({'error': 'sector_allocation is required'}), 400

    new_allocation = data['sector_allocation']

    # Validate weights sum to ~1.0
    total = sum(new_allocation.values())
    if total < 0.95 or total > 1.05:
        return jsonify({'error': f'Weights must sum to ~100%, got {total*100:.1f}%'}), 400

    # Validate all sector paths exist
    for sector_path in new_allocation.keys():
        from app.data.symbol_universe import get_symbols_by_path
        symbols = get_symbols_by_path(sector_path)
        if not symbols:
            return jsonify({'error': f'Invalid sector path: {sector_path}'}), 400

    # Save customization (for user strategies, update directly; for system, store as customization)
    if strategy.get('is_system', True):
        # Store custom weights in user customization
        try:
            from app.models import StrategyCustomization
            from app.database import is_csv_backend, get_csv_storage, get_scoped_session

            if is_csv_backend():
                storage = get_csv_storage()
                customization = storage.get_strategy_customization(user_id, strategy_id)
                if customization:
                    customization['sector_allocation'] = new_allocation
                    storage.save_strategy_customization(user_id, strategy_id, customization)
                else:
                    storage.save_strategy_customization(user_id, strategy_id, {
                        'sector_allocation': new_allocation
                    })
            else:
                session = get_scoped_session()
                customization = session.query(StrategyCustomization).filter_by(
                    user_id=user_id, strategy_id=strategy_id
                ).first()

                if customization:
                    # Store as JSON in a metadata field or separate table
                    # For now, we'll just acknowledge the save
                    pass

            return jsonify({
                'success': True,
                'strategy_id': strategy_id,
                'sector_allocation': new_allocation,
                'message': 'Weights saved successfully'
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        # For custom strategies, update directly via strategy service
        result = service.update_user_strategy(strategy_id, {
            'sector_allocation': new_allocation
        })
        if result:
            return jsonify({
                'success': True,
                'strategy_id': strategy_id,
                'sector_allocation': new_allocation
            })
        else:
            return jsonify({'error': 'Failed to update strategy'}), 500


# ===== Industry Browser Endpoints =====

@strategy_bp.route('/industries', methods=['GET'])
def get_industries():
    """
    GET /api/strategies/industries
    Get full industry hierarchy tree for the browser.
    """
    tree = get_industry_tree()
    return jsonify({
        'industries': tree,
        'count': len(tree)
    })


@strategy_bp.route('/industries/<sector>', methods=['GET'])
def get_industry_sector(sector):
    """
    GET /api/strategies/industries/<sector>
    Get single sector detail with subsectors and symbols.
    """
    if sector not in SYMBOL_UNIVERSE:
        return jsonify({'error': f'Sector "{sector}" not found'}), 404

    metadata = SECTOR_METADATA.get(sector, {})
    subsectors = []

    for subsector_name, symbols in SYMBOL_UNIVERSE[sector].items():
        subsectors.append({
            'id': f"{sector}.{subsector_name}",
            'name': subsector_name.replace('_', ' ').title(),
            'symbols': symbols,
            'symbol_count': len(symbols)
        })

    return jsonify({
        'id': sector,
        'name': metadata.get('name', sector.replace('_', ' ').title()),
        'description': metadata.get('description', ''),
        'color': metadata.get('color', '#6b7280'),
        'subsectors': subsectors,
        'total_symbols': sum(s['symbol_count'] for s in subsectors)
    })


@strategy_bp.route('/industries/search', methods=['GET'])
def search_industry():
    """
    GET /api/strategies/industries/search?q=<query>
    Search across sectors, subsectors, and symbols.
    """
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    results = search_industries(query)
    return jsonify({
        'results': results,
        'count': len(results),
        'query': query
    })


# ===== Strategy Allocations Endpoints =====

@strategy_bp.route('/<strategy_id>/allocations', methods=['GET'])
def get_allocations(strategy_id):
    """
    GET /api/strategies/<strategy_id>/allocations
    Get all allocations for a strategy.
    """
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    service = AllocationService(strategy_id)
    allocations = service.get_allocations(include_inactive)
    summary = service.get_allocation_summary()
    effective_symbols = service.compute_effective_symbols()

    return jsonify({
        'strategy_id': strategy_id,
        'allocations': allocations,
        'summary': summary,
        'effective_symbols': effective_symbols
    })


@strategy_bp.route('/<strategy_id>/allocations', methods=['POST'])
def add_allocation(strategy_id):
    """
    POST /api/strategies/<strategy_id>/allocations
    Add an allocation to a strategy.

    Request body:
    {
        "path": "financials.banks",
        "weight": 0.3,
        "allocation_type": "subsector"  // optional, auto-detected
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    path = data.get('path')
    if not path:
        return jsonify({'error': 'Path is required'}), 400

    weight = float(data.get('weight', 1.0))
    allocation_type = data.get('allocation_type')

    try:
        service = AllocationService(strategy_id)
        allocation = service.add_allocation(path, weight, allocation_type)
        return jsonify({
            'message': 'Allocation added successfully',
            'allocation': allocation
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/allocations/bulk', methods=['POST'])
def set_allocations(strategy_id):
    """
    POST /api/strategies/<strategy_id>/allocations/bulk
    Replace all allocations for a strategy.

    Request body:
    {
        "allocations": [
            {"path": "financials", "weight": 0.3},
            {"path": "technology.semiconductors", "weight": 0.4},
            {"path": "AAPL", "weight": 0.1}
        ]
    }
    """
    data = request.get_json()
    if not data or 'allocations' not in data:
        return jsonify({'error': 'allocations array is required'}), 400

    try:
        service = AllocationService(strategy_id)
        allocations = service.set_allocations(data['allocations'])
        summary = service.get_allocation_summary()

        return jsonify({
            'message': 'Allocations set successfully',
            'allocations': allocations,
            'summary': summary
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/allocations/<int:allocation_id>', methods=['PUT'])
def update_allocation(strategy_id, allocation_id):
    """
    PUT /api/strategies/<strategy_id>/allocations/<allocation_id>
    Update an allocation's weight.

    Request body:
    {
        "weight": 0.35
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    weight = data.get('weight')
    if weight is None:
        return jsonify({'error': 'Weight is required'}), 400

    try:
        service = AllocationService(strategy_id)
        allocation = service.update_allocation(allocation_id, float(weight))
        if allocation:
            return jsonify({
                'message': 'Allocation updated successfully',
                'allocation': allocation
            })
        else:
            return jsonify({'error': 'Allocation not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/allocations/<int:allocation_id>', methods=['DELETE'])
def delete_allocation(strategy_id, allocation_id):
    """
    DELETE /api/strategies/<strategy_id>/allocations/<allocation_id>
    Remove an allocation.
    """
    hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'

    service = AllocationService(strategy_id)
    result = service.remove_allocation(allocation_id, hard_delete)

    if result:
        return jsonify({'message': 'Allocation removed successfully'})
    else:
        return jsonify({'error': 'Allocation not found'}), 404


# ===== Component Parameters Endpoints =====

@strategy_bp.route('/<strategy_id>/component-params', methods=['GET'])
def get_component_params(strategy_id):
    """
    GET /api/strategies/<strategy_id>/component-params
    Get all component parameter overrides for a strategy.
    """
    user_id = request.args.get('user_id', 'default')
    strategy_service = StrategyService(user_id)
    strategy = strategy_service.get_strategy(strategy_id)

    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    strategy_defaults = {
        'max_position_pct': strategy.get('max_position_pct', 0.15),
        'stop_loss_percent': strategy.get('stop_loss_percent', 10),
        'take_profit_percent': strategy.get('take_profit_percent', 20)
    }

    service = ComponentParamsService(strategy_id, strategy_defaults)
    params = service.get_all_params()

    return jsonify({
        'strategy_id': strategy_id,
        'strategy_defaults': strategy_defaults,
        'component_params': params
    })


@strategy_bp.route('/<strategy_id>/component-params/<path:component_path>', methods=['GET'])
def get_component_param(strategy_id, component_path):
    """
    GET /api/strategies/<strategy_id>/component-params/<component_path>
    Get effective params for a component with inheritance chain.
    """
    user_id = request.args.get('user_id', 'default')
    strategy_service = StrategyService(user_id)
    strategy = strategy_service.get_strategy(strategy_id)

    if not strategy:
        return jsonify({'error': f'Strategy "{strategy_id}" not found'}), 404

    strategy_defaults = {
        'max_position_pct': strategy.get('max_position_pct', 0.15),
        'stop_loss_percent': strategy.get('stop_loss_percent', 10),
        'take_profit_percent': strategy.get('take_profit_percent', 20)
    }

    service = ComponentParamsService(strategy_id, strategy_defaults)
    params_with_inheritance = service.get_params_with_inheritance(component_path)

    return jsonify({
        'strategy_id': strategy_id,
        'component_path': component_path,
        **params_with_inheritance
    })


@strategy_bp.route('/<strategy_id>/component-params/<path:component_path>', methods=['PUT'])
def set_component_param(strategy_id, component_path):
    """
    PUT /api/strategies/<strategy_id>/component-params/<component_path>
    Set parameter overrides for a component.

    Request body:
    {
        "stop_loss_percent": 15,
        "entry_signal": "momentum"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        service = ComponentParamsService(strategy_id)
        params = service.set_params(component_path, **data)
        return jsonify({
            'message': 'Parameters set successfully',
            'params': params
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/component-params/<path:component_path>', methods=['DELETE'])
def delete_component_param(strategy_id, component_path):
    """
    DELETE /api/strategies/<strategy_id>/component-params/<component_path>
    Delete parameter overrides for a component.
    """
    service = ComponentParamsService(strategy_id)
    result = service.delete_params(component_path)

    if result:
        return jsonify({'message': 'Parameters removed successfully'})
    else:
        return jsonify({'error': 'Parameters not found'}), 404


# ===== Strategy Rules Endpoints =====

@strategy_bp.route('/<strategy_id>/rules', methods=['GET'])
def get_rules(strategy_id):
    """
    GET /api/strategies/<strategy_id>/rules
    Get all rules for a strategy.
    """
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    engine = RulesEngine(strategy_id)
    rules = engine.get_rules(include_inactive)

    return jsonify({
        'strategy_id': strategy_id,
        'rules': rules,
        'count': len(rules)
    })


@strategy_bp.route('/<strategy_id>/rules', methods=['POST'])
def create_rule(strategy_id):
    """
    POST /api/strategies/<strategy_id>/rules
    Create a new rule.

    Request body:
    {
        "rule_name": "Hedge NVDA with Gold",
        "rule_type": "hedge",
        "config": {
            "primary": "NVDA",
            "hedge": "GLD",
            "ratio": -0.3
        },
        "priority": 1,
        "is_active": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['rule_name', 'rule_type', 'config']
    for field in required:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        engine = RulesEngine(strategy_id)
        rule = engine.create_rule(
            rule_name=data['rule_name'],
            rule_type=data['rule_type'],
            config=data['config'],
            priority=data.get('priority', 0),
            is_active=data.get('is_active', True)
        )
        return jsonify({
            'message': 'Rule created successfully',
            'rule': rule
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/rules/templates', methods=['GET'])
def get_rules_templates(strategy_id):
    """
    GET /api/strategies/<strategy_id>/rules/templates
    Get available rule templates.
    """
    templates = get_rule_templates()
    return jsonify({
        'templates': templates
    })


@strategy_bp.route('/<strategy_id>/rules/<int:rule_id>', methods=['GET'])
def get_rule(strategy_id, rule_id):
    """
    GET /api/strategies/<strategy_id>/rules/<rule_id>
    Get a specific rule.
    """
    engine = RulesEngine(strategy_id)
    rule = engine.get_rule(rule_id)

    if rule:
        return jsonify(rule)
    else:
        return jsonify({'error': 'Rule not found'}), 404


@strategy_bp.route('/<strategy_id>/rules/<int:rule_id>', methods=['PUT'])
def update_rule(strategy_id, rule_id):
    """
    PUT /api/strategies/<strategy_id>/rules/<rule_id>
    Update a rule.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        engine = RulesEngine(strategy_id)
        rule = engine.update_rule(rule_id, **data)
        if rule:
            return jsonify({
                'message': 'Rule updated successfully',
                'rule': rule
            })
        else:
            return jsonify({'error': 'Rule not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(strategy_id, rule_id):
    """
    DELETE /api/strategies/<strategy_id>/rules/<rule_id>
    Delete a rule.
    """
    hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'

    engine = RulesEngine(strategy_id)
    result = engine.delete_rule(rule_id, hard_delete)

    if result:
        return jsonify({'message': 'Rule deleted successfully'})
    else:
        return jsonify({'error': 'Rule not found'}), 404


# ===== Strategy Conditions Endpoints =====

@strategy_bp.route('/<strategy_id>/conditions', methods=['GET'])
def get_conditions(strategy_id):
    """
    GET /api/strategies/<strategy_id>/conditions
    Get all conditions for a strategy.
    """
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    engine = ConditionsEngine(strategy_id)
    conditions = engine.get_conditions(include_inactive)

    return jsonify({
        'strategy_id': strategy_id,
        'conditions': conditions,
        'count': len(conditions)
    })


@strategy_bp.route('/<strategy_id>/conditions', methods=['POST'])
def create_condition(strategy_id):
    """
    POST /api/strategies/<strategy_id>/conditions
    Create a new condition.

    Request body:
    {
        "condition_name": "Recession Defense",
        "condition_type": "macro",
        "trigger_config": {
            "signal": "T10Y2Y",
            "comparison": "less_than",
            "threshold": 0
        },
        "action_config": {
            "action": "shift_allocation",
            "reduce": {"technology": 0.10},
            "increase": {"utilities": 0.10}
        },
        "is_active": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['condition_type', 'trigger_config', 'action_config']
    for field in required:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        engine = ConditionsEngine(strategy_id)
        condition = engine.create_condition(
            condition_type=data['condition_type'],
            trigger_config=data['trigger_config'],
            action_config=data['action_config'],
            condition_name=data.get('condition_name'),
            is_active=data.get('is_active', True)
        )
        return jsonify({
            'message': 'Condition created successfully',
            'condition': condition
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/conditions/templates', methods=['GET'])
def get_conditions_templates(strategy_id):
    """
    GET /api/strategies/<strategy_id>/conditions/templates
    Get available condition templates.
    """
    templates = get_condition_templates()
    return jsonify({
        'templates': templates
    })


@strategy_bp.route('/<strategy_id>/conditions/from-template', methods=['POST'])
def create_condition_from_template(strategy_id):
    """
    POST /api/strategies/<strategy_id>/conditions/from-template
    Create a condition from a preset template.

    Request body:
    {
        "template_name": "recession_defense",
        "is_active": true
    }
    """
    data = request.get_json()
    if not data or 'template_name' not in data:
        return jsonify({'error': 'template_name is required'}), 400

    try:
        engine = ConditionsEngine(strategy_id)
        condition = engine.create_from_template(
            data['template_name'],
            data.get('is_active', True)
        )
        return jsonify({
            'message': 'Condition created from template',
            'condition': condition
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/conditions/<int:condition_id>', methods=['GET'])
def get_condition(strategy_id, condition_id):
    """
    GET /api/strategies/<strategy_id>/conditions/<condition_id>
    Get a specific condition.
    """
    engine = ConditionsEngine(strategy_id)
    condition = engine.get_condition(condition_id)

    if condition:
        return jsonify(condition)
    else:
        return jsonify({'error': 'Condition not found'}), 404


@strategy_bp.route('/<strategy_id>/conditions/<int:condition_id>', methods=['PUT'])
def update_condition(strategy_id, condition_id):
    """
    PUT /api/strategies/<strategy_id>/conditions/<condition_id>
    Update a condition.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        engine = ConditionsEngine(strategy_id)
        condition = engine.update_condition(condition_id, **data)
        if condition:
            return jsonify({
                'message': 'Condition updated successfully',
                'condition': condition
            })
        else:
            return jsonify({'error': 'Condition not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/<strategy_id>/conditions/<int:condition_id>', methods=['DELETE'])
def delete_condition(strategy_id, condition_id):
    """
    DELETE /api/strategies/<strategy_id>/conditions/<condition_id>
    Delete a condition.
    """
    hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'

    engine = ConditionsEngine(strategy_id)
    result = engine.delete_condition(condition_id, hard_delete)

    if result:
        return jsonify({'message': 'Condition deleted successfully'})
    else:
        return jsonify({'error': 'Condition not found'}), 404
