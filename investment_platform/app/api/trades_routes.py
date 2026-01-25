"""
Trades API Routes

Endpoints for recording and retrieving trade history.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from app import db
from app.models import TradesHistory

trades_bp = Blueprint('trades', __name__)


@trades_bp.route('', methods=['GET'])
def get_trades():
    """
    GET /api/trades
    Returns trade history for the user.

    Query params:
        - user_id: User identifier (default: 'default')
        - type: Filter by trade type ('buy' or 'sell')
        - limit: Maximum number of trades to return (default: 100)
    """
    user_id = request.args.get('user_id', 'default')
    trade_type = request.args.get('type')
    limit = request.args.get('limit', 100, type=int)

    if trade_type:
        trades = TradesHistory.get_trades_by_type(user_id, trade_type, limit)
    else:
        trades = TradesHistory.get_user_trades(user_id, limit)

    return jsonify({
        'trades': [t.to_dict() for t in trades],
        'total_count': TradesHistory.get_trade_count(user_id)
    })


@trades_bp.route('', methods=['POST'])
def create_trade():
    """
    POST /api/trades
    Record a new trade.

    Required fields:
        - trade_id: Unique trade identifier
        - type: 'buy' or 'sell'
        - symbol: Stock ticker
        - quantity: Number of shares
        - price: Price per share
        - total: Total transaction value
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    required_fields = ['trade_id', 'type', 'symbol', 'quantity', 'price', 'total']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    # Validate trade type
    if data['type'] not in ['buy', 'sell']:
        return jsonify({'error': 'type must be "buy" or "sell"'}), 400

    try:
        trade = TradesHistory(
            user_id=data.get('user_id', 'default'),
            trade_id=data['trade_id'],
            timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now(timezone.utc),
            type=data['type'],
            symbol=data['symbol'].upper(),
            stock_name=data.get('stock_name'),
            sector=data.get('sector'),
            quantity=data['quantity'],
            price=data['price'],
            total=data['total'],
            fees=data.get('fees', 0),
            strategy=data.get('strategy')
        )

        db.session.add(trade)
        db.session.commit()

        return jsonify(trade.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@trades_bp.route('/<trade_id>', methods=['GET'])
def get_trade(trade_id):
    """
    GET /api/trades/<trade_id>
    Get a specific trade by ID.
    """
    trade = TradesHistory.query.filter_by(trade_id=trade_id).first()

    if not trade:
        return jsonify({'error': f'Trade {trade_id} not found'}), 404

    return jsonify(trade.to_dict())
