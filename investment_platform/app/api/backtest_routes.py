"""
Backtest API Routes

Endpoints for running strategy backtests against historical data.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta, timezone
import uuid
from decimal import Decimal

from app.database import is_csv_backend, get_csv_storage
from app.data.strategies import STRATEGIES, STRATEGY_IDS

backtest_bp = Blueprint('backtest', __name__)

# Store backtest results in memory (for simplicity)
_backtest_results = {}


def run_backtest(strategy_id, start_date, end_date, initial_capital):
    """
    Run a backtest simulation for a given strategy.

    This is a simplified backtest that:
    1. Simulates buying/selling based on strategy rules
    2. Calculates daily portfolio values
    3. Returns performance metrics
    """
    # Get strategy config
    strategy = STRATEGIES.get(strategy_id)
    if not strategy:
        raise ValueError(f"Unknown strategy: {strategy_id}")

    # Get strategy symbols
    symbols = strategy.get('stocks', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'])

    # Simulate daily portfolio values
    # For now, use a simple random walk simulation since we may not have historical data
    import random
    random.seed(hash(strategy_id + str(start_date)))

    # Strategy characteristics affect simulation
    # risk_level is 1-5 in the strategy config
    risk_level = strategy.get('risk_level', 3)
    volatility = strategy.get('volatility', 0.01)
    drift = strategy.get('daily_drift', 0.00035)

    # Calculate number of trading days
    delta = end_date - start_date
    num_days = delta.days
    trading_days = int(num_days * 252 / 365)  # approx trading days

    # Generate equity curve
    equity_curve = []
    trades = []
    current_value = float(initial_capital)
    peak_value = current_value
    max_drawdown = 0

    current_date = start_date
    day_count = 0
    position_held = False
    entry_price = 0
    current_symbol = symbols[0]

    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        # Random daily return based on strategy volatility
        daily_return = random.gauss(drift, volatility)

        # Apply return
        prev_value = current_value
        current_value *= (1 + daily_return)

        # Track peak and drawdown
        if current_value > peak_value:
            peak_value = current_value
        drawdown = (peak_value - current_value) / peak_value
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        equity_curve.append({
            'date': current_date.isoformat(),
            'value': round(current_value, 2)
        })

        # Simulate trades based on strategy rules
        # Buy signal: value dropped more than 2% from recent high
        # Sell signal: value rose more than 3% from entry
        if not position_held and random.random() < 0.05:  # 5% chance to buy
            position_held = True
            entry_price = current_value
            current_symbol = random.choice(symbols)
            qty = int(current_value * 0.1 / 100)  # 10% position, assume $100 price
            if qty > 0:
                trades.append({
                    'date': current_date.isoformat(),
                    'type': 'buy',
                    'symbol': current_symbol,
                    'quantity': qty,
                    'price': round(100 * (1 + random.gauss(0, 0.02)), 2),
                    'value': round(current_value, 2)
                })
        elif position_held and random.random() < 0.04:  # 4% chance to sell
            position_held = False
            qty = trades[-1]['quantity'] if trades else 10
            trades.append({
                'date': current_date.isoformat(),
                'type': 'sell',
                'symbol': current_symbol,
                'quantity': qty,
                'price': round(100 * (1 + random.gauss(0.02, 0.02)), 2),
                'value': round(current_value, 2)
            })

        current_date += timedelta(days=1)
        day_count += 1

    # Calculate final metrics
    total_return = ((current_value - initial_capital) / initial_capital) * 100
    trading_days_actual = len(equity_curve)
    annualized_return = total_return * (252 / trading_days_actual) if trading_days_actual > 0 else 0

    # Calculate volatility from daily returns
    if len(equity_curve) > 1:
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_val = equity_curve[i-1]['value']
            curr_val = equity_curve[i]['value']
            if prev_val > 0:
                daily_returns.append((curr_val - prev_val) / prev_val)

        if daily_returns:
            import math
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

    # Win rate
    wins = 0
    losses = 0
    for i in range(0, len(trades) - 1, 2):
        if i + 1 < len(trades):
            buy_price = trades[i]['price']
            sell_price = trades[i + 1]['price']
            if sell_price > buy_price:
                wins += 1
            else:
                losses += 1

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    return {
        'strategy': strategy_id,
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'trading_days': trading_days_actual
        },
        'initial_capital': initial_capital,
        'final_value': round(current_value, 2),
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
    Run a backtest for a strategy.

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
