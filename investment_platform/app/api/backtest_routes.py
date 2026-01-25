"""
Backtest API Routes

Endpoints for running strategy backtests against historical data.
Uses real market data from Yahoo Finance with caching to avoid rate limits.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta, timezone
import uuid
import logging

from app.database import is_csv_backend, get_csv_storage
from app.data.strategies import STRATEGIES, STRATEGY_IDS
from app.services.market_data_service import get_market_data_service

logger = logging.getLogger(__name__)

backtest_bp = Blueprint('backtest', __name__)

# Store backtest results in memory (for simplicity)
_backtest_results = {}


def fetch_historical_data(symbols, start_date, end_date):
    """
    Fetch historical data for multiple symbols with caching.

    Args:
        symbols: List of stock ticker symbols
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        Dict of {symbol: DataFrame} with OHLCV data
    """
    service = get_market_data_service()

    logger.info(f"Fetching historical data for {len(symbols)} symbols from {start_date} to {end_date}")

    # Fetch data for all symbols (service handles caching)
    data = service.fetch_multiple_symbols(symbols, start_date, end_date)

    # Log cache status
    for symbol in symbols:
        status = service.get_cache_status(symbol)
        if isinstance(status, dict):
            logger.info(f"{symbol}: {status.get('total_records', 0)} records cached, "
                       f"range: {status.get('earliest_date')} to {status.get('latest_date')}")

    return data


def run_backtest(strategy_id, start_date, end_date, initial_capital):
    """
    Run a backtest simulation for a given strategy using real historical data.

    This backtest:
    1. Fetches real historical OHLCV data from Yahoo Finance (with caching)
    2. Simulates buying/selling based on simple moving average crossover strategy
    3. Calculates daily portfolio values
    4. Returns performance metrics
    """
    import math

    # Get strategy config
    strategy = STRATEGIES.get(strategy_id)
    if not strategy:
        raise ValueError(f"Unknown strategy: {strategy_id}")

    # Get strategy symbols
    symbols = strategy.get('stocks', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'])
    max_position_pct = strategy.get('max_position_pct', 0.15)
    target_investment_ratio = strategy.get('target_investment_ratio', 0.7)

    # Fetch real historical data
    # Request extra days before start_date for moving average calculation
    ma_period = 20  # 20-day moving average
    fetch_start = start_date - timedelta(days=ma_period + 10)  # Add buffer for weekends

    historical_data = fetch_historical_data(symbols, fetch_start, end_date)

    # Check if we got any data
    valid_symbols = [s for s in symbols if s in historical_data and not historical_data[s].empty]

    if not valid_symbols:
        logger.error(f"No historical data available for any symbols in {strategy_id}")
        raise ValueError(f"No market data available for strategy '{strategy_id}'. Please ensure you have internet connection to fetch data from Yahoo Finance.")

    logger.info(f"Running backtest with real data for {len(valid_symbols)} symbols: {valid_symbols}")

    # Initialize portfolio
    cash = float(initial_capital)
    positions = {}  # {symbol: {'quantity': int, 'avg_cost': float}}

    # Generate equity curve and trades
    equity_curve = []
    trades = []

    # Get all trading days in range
    all_dates = set()
    for symbol in valid_symbols:
        df = historical_data[symbol]
        for d in df.index:
            if isinstance(d, date) and start_date <= d <= end_date:
                all_dates.add(d)

    trading_days = sorted(all_dates)

    if not trading_days:
        logger.error("No trading days found in date range")
        raise ValueError(f"No trading days found between {start_date} and {end_date}. Please check your date range.")

    # Calculate moving averages for each symbol
    moving_averages = {}
    for symbol in valid_symbols:
        df = historical_data[symbol]
        if 'adj_close' in df.columns:
            ma = df['adj_close'].rolling(window=ma_period).mean()
            moving_averages[symbol] = ma

    # Track metrics
    peak_value = initial_capital
    max_drawdown = 0

    # Run simulation day by day
    for current_date in trading_days:
        # Calculate current portfolio value
        holdings_value = 0
        for symbol, pos in positions.items():
            if symbol in historical_data:
                df = historical_data[symbol]
                if current_date in df.index:
                    price = float(df.loc[current_date, 'adj_close'])
                    holdings_value += pos['quantity'] * price

        portfolio_value = cash + holdings_value

        # Track drawdown
        if portfolio_value > peak_value:
            peak_value = portfolio_value
        drawdown = (peak_value - portfolio_value) / peak_value if peak_value > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        # Record equity curve point
        equity_curve.append({
            'date': current_date.isoformat(),
            'value': round(portfolio_value, 2)
        })

        # Trading logic: Simple moving average crossover
        for symbol in valid_symbols:
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if current_date not in df.index:
                continue

            price = float(df.loc[current_date, 'adj_close'])

            # Get moving average for this date
            if symbol in moving_averages and current_date in moving_averages[symbol].index:
                ma = moving_averages[symbol].loc[current_date]
                if ma is None or (hasattr(ma, '__len__') and len(ma) == 0):
                    continue
                ma = float(ma) if not (isinstance(ma, float) and math.isnan(ma)) else None
                if ma is None:
                    continue
            else:
                continue

            current_position = positions.get(symbol, {'quantity': 0, 'avg_cost': 0})

            # Buy signal: Price crosses above MA and we have room to buy
            if price > ma * 1.01:  # 1% above MA
                if current_position['quantity'] == 0:
                    # Calculate position size
                    max_investment = portfolio_value * max_position_pct
                    available_cash = cash * target_investment_ratio
                    invest_amount = min(max_investment, available_cash)

                    if invest_amount > 100 and cash >= invest_amount:  # Min $100 trade
                        quantity = int(invest_amount / price)
                        if quantity > 0:
                            cost = quantity * price
                            fee = cost * 0.001  # 0.1% fee
                            total_cost = cost + fee

                            if cash >= total_cost:
                                cash -= total_cost
                                positions[symbol] = {
                                    'quantity': quantity,
                                    'avg_cost': price
                                }

                                trades.append({
                                    'date': current_date.isoformat(),
                                    'type': 'buy',
                                    'symbol': symbol,
                                    'quantity': quantity,
                                    'price': round(price, 2),
                                    'value': round(portfolio_value, 2)
                                })

            # Sell signal: Price crosses below MA
            elif price < ma * 0.99 and current_position['quantity'] > 0:  # 1% below MA
                quantity = current_position['quantity']
                revenue = quantity * price
                fee = revenue * 0.001  # 0.1% fee
                net_revenue = revenue - fee

                cash += net_revenue
                del positions[symbol]

                trades.append({
                    'date': current_date.isoformat(),
                    'type': 'sell',
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': round(price, 2),
                    'value': round(cash + holdings_value, 2)
                })

    # Calculate final portfolio value
    final_holdings_value = 0
    for symbol, pos in positions.items():
        if symbol in historical_data:
            df = historical_data[symbol]
            if trading_days and trading_days[-1] in df.index:
                price = float(df.loc[trading_days[-1], 'adj_close'])
                final_holdings_value += pos['quantity'] * price

    final_value = cash + final_holdings_value

    # Calculate metrics
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    trading_days_count = len(equity_curve)
    annualized_return = total_return * (252 / trading_days_count) if trading_days_count > 0 else 0

    # Calculate volatility from daily returns
    if len(equity_curve) > 1:
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_val = equity_curve[i-1]['value']
            curr_val = equity_curve[i]['value']
            if prev_val > 0:
                daily_returns.append((curr_val - prev_val) / prev_val)

        if daily_returns:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            daily_volatility = math.sqrt(variance)
            annualized_volatility = daily_volatility * math.sqrt(252)
        else:
            annualized_volatility = 0
    else:
        annualized_volatility = 0

    # Sharpe ratio (assuming risk-free rate of 4%)
    risk_free_rate = 0.04
    sharpe_ratio = (annualized_return / 100 - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0

    # Win rate calculation
    wins = 0
    losses = 0
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']

    for sell in sell_trades:
        # Find matching buy
        matching_buys = [b for b in buy_trades if b['symbol'] == sell['symbol'] and b['date'] < sell['date']]
        if matching_buys:
            buy = matching_buys[-1]  # Most recent buy before this sell
            if sell['price'] > buy['price']:
                wins += 1
            else:
                losses += 1

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    return {
        'strategy': strategy_id,
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'trading_days': trading_days_count
        },
        'initial_capital': initial_capital,
        'final_value': round(final_value, 2),
        'data_source': 'yahoo_finance',
        'symbols_used': valid_symbols,
        'metrics': {
            'total_return': round(total_return, 2),
            'annualized_return': round(annualized_return, 2),
            'max_drawdown': round(-max_drawdown * 100, 2),
            'volatility': round(annualized_volatility * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1)
        },
        'equity_curve': equity_curve,
        'trades': trades
    }


@backtest_bp.route('/run', methods=['POST'])
def run_backtest_endpoint():
    """
    POST /api/backtest/run
    Run a backtest for a strategy using real historical data.

    Data is fetched from Yahoo Finance and cached to avoid rate limits.

    Request body:
    {
        "strategy_id": "balanced",
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "initial_capital": 100000
    }
    """
    data = request.get_json() or {}

    strategy_id = data.get('strategy_id', 'balanced')
    if strategy_id not in STRATEGY_IDS:
        return jsonify({
            'error': f'Invalid strategy: {strategy_id}',
            'valid_strategies': list(STRATEGY_IDS)
        }), 400

    # Parse dates
    try:
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')

        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        else:
            start_date = date.today() - timedelta(days=365)

        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
        else:
            end_date = date.today()

    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {e}'}), 400

    if start_date >= end_date:
        return jsonify({'error': 'start_date must be before end_date'}), 400

    initial_capital = float(data.get('initial_capital', 100000))
    if initial_capital < 1000:
        return jsonify({'error': 'initial_capital must be at least 1000'}), 400

    try:
        # Run the backtest
        result = run_backtest(strategy_id, start_date, end_date, initial_capital)

        # Generate unique ID and store result
        backtest_id = f"bt_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        result['backtest_id'] = backtest_id
        _backtest_results[backtest_id] = result

        return jsonify(result)

    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/results/<backtest_id>', methods=['GET'])
def get_backtest_result(backtest_id):
    """
    GET /api/backtest/results/<backtest_id>
    Get a previously run backtest result.
    """
    result = _backtest_results.get(backtest_id)
    if not result:
        return jsonify({'error': f'Backtest {backtest_id} not found'}), 404
    return jsonify(result)


@backtest_bp.route('/strategies', methods=['GET'])
def get_available_strategies():
    """
    GET /api/backtest/strategies
    Get list of strategies available for backtesting.
    """
    risk_labels = {1: 'very low', 2: 'low', 3: 'medium', 4: 'high', 5: 'very high'}
    strategies = []
    for sid in STRATEGY_IDS:
        strategy = STRATEGIES.get(sid, {})
        risk_num = strategy.get('risk_level', 3)
        strategies.append({
            'id': sid,
            'name': strategy.get('name', sid.title()),
            'risk_level': risk_labels.get(risk_num, 'medium'),
            'risk_value': risk_num,
            'description': strategy.get('description', ''),
            'stock_count': len(strategy.get('stocks', []))
        })

    return jsonify({
        'strategies': strategies,
        'count': len(strategies)
    })


@backtest_bp.route('/cache/status', methods=['GET'])
def get_cache_status():
    """
    GET /api/backtest/cache/status
    Get cache status for market data used in backtesting.
    """
    service = get_market_data_service()

    # Get all strategy symbols
    all_symbols = set()
    for strategy in STRATEGIES.values():
        all_symbols.update(strategy.get('stocks', []))

    cache_info = []
    for symbol in sorted(all_symbols):
        status = service.get_cache_status(symbol)
        if isinstance(status, dict):
            cache_info.append(status)

    return jsonify({
        'symbols': cache_info,
        'total_symbols': len(all_symbols),
        'cached_symbols': len([c for c in cache_info if c.get('total_records', 0) > 0])
    })
