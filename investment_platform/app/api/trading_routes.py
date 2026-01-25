"""
Trading API Routes

Endpoints for executing trades and managing the trading engine.
"""
from flask import Blueprint, jsonify, request

from app import db
from app.models import PortfolioState, Holdings
from app.services.trading_engine import (
    TradingEngine, auto_trade, execute_trade,
    calculate_execution_price, generate_trade_id
)
from app.services.portfolio_service import get_portfolio_summary
from app.services.market_data_service import get_market_data_service
from app.data import get_all_symbols, get_strategy_stocks, is_valid_symbol

trading_bp = Blueprint('trading', __name__)


@trading_bp.route('/execute', methods=['POST'])
def execute_manual_trade():
    """
    POST /api/trading/execute
    Execute a manual trade.

    Request body:
        {
            "type": "buy" or "sell",
            "symbol": "AAPL",
            "quantity": 10,
            "price": 175.50  // Optional, uses market price if not provided
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    required = ['type', 'symbol', 'quantity']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    trade_type = data['type'].lower()
    symbol = data['symbol'].upper()
    quantity = int(data['quantity'])
    user_id = data.get('user_id', 'default')

    if trade_type not in ['buy', 'sell']:
        return jsonify({'error': 'type must be "buy" or "sell"'}), 400

    if not is_valid_symbol(symbol):
        return jsonify({'error': f'Invalid symbol: {symbol}'}), 400

    if quantity <= 0:
        return jsonify({'error': 'quantity must be positive'}), 400

    # Get price (from request or market)
    if 'price' in data:
        price = float(data['price'])
    else:
        service = get_market_data_service()
        price_data = service.get_current_price(symbol)
        market_price = price_data['price']
        price = calculate_execution_price(market_price, trade_type)

    # Get strategy from portfolio
    portfolio = PortfolioState.get_or_create(user_id)
    strategy = portfolio.current_strategy

    # Execute trade
    result = execute_trade(
        user_id=user_id,
        trade_type=trade_type,
        symbol=symbol,
        quantity=quantity,
        price=price,
        strategy=strategy
    )

    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@trading_bp.route('/auto', methods=['POST'])
def execute_auto_trade():
    """
    POST /api/trading/auto
    Execute an automatic trade based on current strategy.

    The trading engine will determine:
    - Whether to buy or sell
    - Which stock to trade
    - How many shares
    """
    data = request.get_json() or {}
    user_id = data.get('user_id', 'default')

    # Get current prices for all strategy stocks
    portfolio = PortfolioState.get_or_create(user_id)
    strategy_stocks = get_strategy_stocks(portfolio.current_strategy)

    service = get_market_data_service()
    current_prices = {}

    for symbol in strategy_stocks:
        try:
            price_data = service.get_current_price(symbol)
            current_prices[symbol] = price_data['price']
        except Exception as e:
            continue  # Skip symbols we can't get prices for

    if not current_prices:
        return jsonify({
            'error': 'Could not get prices for any stocks',
            'message': 'Auto trade aborted'
        }), 500

    # Execute auto trade
    result = auto_trade(user_id, current_prices)

    if result is None:
        return jsonify({
            'message': 'No trade executed',
            'reason': 'No valid trade opportunity found'
        })

    if result.get('success'):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@trading_bp.route('/recommendation', methods=['GET'])
def get_recommendation():
    """
    GET /api/trading/recommendation
    Get trade recommendation without executing.

    Shows what the auto-trader would do if triggered.
    """
    user_id = request.args.get('user_id', 'default')

    # Get current prices
    portfolio = PortfolioState.get_or_create(user_id)
    strategy_stocks = get_strategy_stocks(portfolio.current_strategy)

    service = get_market_data_service()
    current_prices = {}

    for symbol in strategy_stocks:
        try:
            price_data = service.get_current_price(symbol)
            current_prices[symbol] = price_data['price']
        except Exception:
            continue

    if not current_prices:
        return jsonify({
            'recommendation': 'hold',
            'reason': 'Could not get market prices'
        })

    engine = TradingEngine(user_id)
    recommendation = engine.get_trade_recommendation(current_prices)

    return jsonify(recommendation)


@trading_bp.route('/summary', methods=['GET'])
def get_trading_summary():
    """
    GET /api/trading/summary
    Get comprehensive portfolio and trading summary.
    """
    user_id = request.args.get('user_id', 'default')

    # Get portfolio state
    portfolio = PortfolioState.get_or_create(user_id)
    portfolio_dict = portfolio.to_dict()

    # Get holdings
    holdings = Holdings.get_user_holdings(user_id)
    holdings_list = [h.to_dict() for h in holdings]

    # Get current prices for holdings
    service = get_market_data_service()
    current_prices = {}

    symbols = [h['symbol'] for h in holdings_list]
    for symbol in symbols:
        try:
            price_data = service.get_current_price(symbol)
            current_prices[symbol] = price_data['price']
        except Exception:
            # Use avg_cost as fallback
            holding = next(h for h in holdings_list if h['symbol'] == symbol)
            current_prices[symbol] = holding['avg_cost']

    # Get portfolio summary with calculations
    summary = get_portfolio_summary(portfolio_dict, holdings_list, current_prices)

    # Add holdings with current prices
    for holding in holdings_list:
        symbol = holding['symbol']
        holding['current_price'] = current_prices.get(symbol, holding['avg_cost'])
        holding['market_value'] = holding['quantity'] * holding['current_price']
        holding['unrealized_gain'] = (holding['current_price'] - holding['avg_cost']) * holding['quantity']
        holding['unrealized_gain_pct'] = ((holding['current_price'] - holding['avg_cost']) / holding['avg_cost'] * 100) if holding['avg_cost'] > 0 else 0

    summary['holdings'] = holdings_list
    summary['strategy'] = portfolio.current_strategy

    return jsonify(summary)
