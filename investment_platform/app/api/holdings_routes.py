"""
Holdings API Routes

Endpoints for managing stock holdings.
"""
from flask import Blueprint, jsonify, request
from app.database import is_csv_backend
from app.models import Holdings
from app.data.symbol_universe import get_sector_for_symbol, SECTOR_METADATA

holdings_bp = Blueprint('holdings', __name__)


@holdings_bp.route('', methods=['GET'])
def get_holdings():
    """
    GET /api/holdings
    Returns all holdings for the user.
    """
    user_id = request.args.get('user_id', 'default')
    holdings = Holdings.get_user_holdings(user_id)

    # CSV backend returns dicts, DB backend returns objects
    if holdings and isinstance(holdings[0], dict):
        holdings_list = holdings
    else:
        holdings_list = [h.to_dict() for h in holdings]

    return jsonify({
        'holdings': holdings_list,
        'total_count': len(holdings_list)
    })


@holdings_bp.route('', methods=['PUT'])
def update_holdings():
    """
    PUT /api/holdings
    Bulk update/replace all holdings for a user.
    """
    data = request.get_json()
    if not data or 'holdings' not in data:
        return jsonify({'error': 'holdings array is required'}), 400

    user_id = data.get('user_id', 'default')

    try:
        # Delete existing holdings
        Holdings.delete_user_holdings(user_id)

        # Insert new holdings
        for holding_data in data['holdings']:
            holding = Holdings(
                user_id=user_id,
                symbol=holding_data['symbol'],
                name=holding_data.get('name'),
                sector=holding_data.get('sector'),
                quantity=holding_data['quantity'],
                avg_cost=holding_data['avg_cost']
            )
            db.session.add(holding)

        db.session.commit()

        holdings = Holdings.get_user_holdings(user_id)
        return jsonify({
            'holdings': [h.to_dict() for h in holdings],
            'total_count': len(holdings)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@holdings_bp.route('/<symbol>', methods=['GET'])
def get_holding(symbol):
    """
    GET /api/holdings/<symbol>
    Get a specific holding by symbol.
    """
    user_id = request.args.get('user_id', 'default')
    holding = Holdings.get_holding(user_id, symbol.upper())

    if not holding:
        return jsonify({'error': f'No holding found for {symbol}'}), 404

    return jsonify(holding.to_dict())


@holdings_bp.route('/sectors', methods=['GET'])
def get_holdings_by_sector():
    """
    GET /api/holdings/sectors
    Returns holdings aggregated by sector for pie chart display.
    """
    user_id = request.args.get('user_id', 'default')
    holdings = Holdings.get_user_holdings(user_id)

    # CSV backend returns dicts, DB backend returns objects
    if holdings and isinstance(holdings[0], dict):
        holdings_list = holdings
    else:
        holdings_list = [h.to_dict() for h in holdings] if holdings else []

    # Aggregate by sector
    sector_values = {}
    total_value = 0

    for h in holdings_list:
        symbol = h.get('symbol', '')
        quantity = float(h.get('quantity', 0))
        avg_cost = float(h.get('avg_cost', 0))
        value = quantity * avg_cost
        total_value += value

        # Get sector from symbol universe
        sector, subsector = get_sector_for_symbol(symbol)
        if not sector:
            sector = 'other'
            subsector = 'unknown'

        if sector not in sector_values:
            metadata = SECTOR_METADATA.get(sector, {})
            sector_values[sector] = {
                'name': metadata.get('name', sector.replace('_', ' ').title()),
                'color': metadata.get('color', '#6b7280'),
                'value': 0,
                'holdings': []
            }

        sector_values[sector]['value'] += value
        sector_values[sector]['holdings'].append({
            'symbol': symbol,
            'value': value,
            'subsector': subsector
        })

    # Calculate percentages
    sectors = []
    for sector_id, data in sector_values.items():
        pct = (data['value'] / total_value * 100) if total_value > 0 else 0
        sectors.append({
            'sector': sector_id,
            'name': data['name'],
            'color': data['color'],
            'value': round(data['value'], 2),
            'percentage': round(pct, 1),
            'holdings': data['holdings']
        })

    # Sort by value descending
    sectors.sort(key=lambda x: x['value'], reverse=True)

    return jsonify({
        'sectors': sectors,
        'total_value': round(total_value, 2),
        'total_holdings': len(holdings_list)
    })
