"""
Price Generation Engine (Fallback/Simulation Mode)

Implements Geometric Brownian Motion (GBM) price simulation as a fallback
for when Yahoo Finance is unavailable. Provides realistic price movements
for backtesting and simulation purposes.

NOTE: This is a FALLBACK. Primary price data should come from MarketDataService.
"""
import numpy as np
from datetime import date, timedelta
from math import sin, pi
from typing import List, Dict, Optional

from app.data import get_stock_beta, get_strategy_volatility, get_strategy_drift, STOCK_UNIVERSE


# Strategy-specific simulation parameters
STRATEGY_PARAMS = {
    'conservative': {'volatility': 0.005, 'drift': 0.00015},
    'growth':       {'volatility': 0.015, 'drift': 0.0005},
    'value':        {'volatility': 0.008, 'drift': 0.0003},
    'balanced':     {'volatility': 0.01,  'drift': 0.00035},
    'aggressive':   {'volatility': 0.025, 'drift': 0.0004}
}


def set_simulation_seed(seed: int):
    """
    Set random seed for reproducible simulations.

    Args:
        seed: Integer seed value
    """
    np.random.seed(seed)


def generate_price(
    current_price: float,
    beta: float = 1.0,
    volatility: float = 0.02,
    drift: float = 0.0003
) -> float:
    """
    Generate next price using Geometric Brownian Motion.

    GBM Formula: S(t+1) = S(t) * exp((drift - 0.5*vol^2)*dt + vol*sqrt(dt)*Z)
    Simplified for daily: S(t+1) = S(t) * (1 + daily_return)

    Args:
        current_price: Current stock price
        beta: Stock's beta (volatility relative to market, default 1.0)
        volatility: Base volatility parameter (default 0.02 = 2%)
        drift: Daily drift/expected return (default 0.0003 ≈ 7.5% annually)

    Returns:
        New simulated price (always positive)
    """
    # Adjust volatility by stock's beta
    daily_volatility = volatility * beta

    # Generate random factor from standard normal distribution
    random_factor = np.random.normal(0, 1)

    # Calculate daily return
    daily_return = drift + (random_factor * daily_volatility)

    # Calculate new price (ensure positive)
    new_price = current_price * (1 + daily_return)

    # Ensure price doesn't go negative or below a minimum
    min_price = current_price * 0.5  # Don't allow more than 50% daily drop
    return max(new_price, min_price, 0.01)


def generate_price_with_seasonality(
    current_price: float,
    beta: float,
    day_of_year: int,
    volatility: float = 0.02,
    drift: float = 0.0003
) -> float:
    """
    Generate price with seasonal adjustment.

    Adds slight cyclical behavior to simulate market patterns like:
    - January effect
    - Summer doldrums
    - Year-end rally

    Args:
        current_price: Current stock price
        beta: Stock's beta
        day_of_year: Day of year (1-365)
        volatility: Base volatility
        drift: Base drift

    Returns:
        New simulated price with seasonality
    """
    # Calculate seasonal adjustment using sine wave
    monthly_phase = 2 * pi * (day_of_year / 365)
    seasonality = sin(monthly_phase) * 0.003  # ±0.3% seasonal swing

    # Adjust drift for seasonality
    adjusted_drift = drift + seasonality

    return generate_price(current_price, beta, volatility, adjusted_drift)


def generate_price_series(
    start_price: float,
    num_days: int,
    beta: float = 1.0,
    volatility: float = 0.02,
    drift: float = 0.0003,
    seed: Optional[int] = None,
    include_seasonality: bool = False,
    start_day_of_year: int = 1
) -> List[float]:
    """
    Generate a series of prices over multiple days.

    Args:
        start_price: Starting price
        num_days: Number of days to simulate
        beta: Stock's beta
        volatility: Base volatility
        drift: Base drift
        seed: Random seed for reproducibility
        include_seasonality: Whether to include seasonal effects
        start_day_of_year: Starting day of year for seasonality

    Returns:
        List of prices
    """
    if seed is not None:
        np.random.seed(seed)

    prices = [start_price]

    for i in range(num_days - 1):
        if include_seasonality:
            day_of_year = (start_day_of_year + i) % 365 + 1
            new_price = generate_price_with_seasonality(
                prices[-1], beta, day_of_year, volatility, drift
            )
        else:
            new_price = generate_price(prices[-1], beta, volatility, drift)

        prices.append(new_price)

    return prices


def generate_reproducible_prices(
    symbol: str,
    start_price: float,
    num_days: int,
    seed: int
) -> List[float]:
    """
    Generate deterministic price series for backtesting.

    Uses symbol-specific beta and a fixed seed for reproducibility.

    Args:
        symbol: Stock ticker symbol
        start_price: Starting price
        num_days: Number of days
        seed: Random seed

    Returns:
        List of prices
    """
    beta = get_stock_beta(symbol)
    return generate_price_series(
        start_price=start_price,
        num_days=num_days,
        beta=beta,
        seed=seed
    )


def update_all_prices(
    holdings: List[Dict],
    strategy: str = 'balanced'
) -> Dict[str, float]:
    """
    Update prices for all holdings based on strategy parameters.

    Args:
        holdings: List of holdings with 'symbol' and 'current_price'
        strategy: Strategy ID for volatility/drift parameters

    Returns:
        Dict of {symbol: new_price}
    """
    params = STRATEGY_PARAMS.get(strategy, STRATEGY_PARAMS['balanced'])

    updated_prices = {}

    for holding in holdings:
        symbol = holding['symbol']
        current_price = holding.get('current_price', holding.get('price', 100))
        beta = get_stock_beta(symbol)

        new_price = generate_price(
            current_price,
            beta,
            params['volatility'],
            params['drift']
        )
        updated_prices[symbol] = new_price

    return updated_prices


def generate_portfolio_history(
    initial_value: float,
    strategy: str,
    num_days: int,
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Generate historical portfolio values for charting.

    Simulates portfolio value over time based on strategy parameters.

    Args:
        initial_value: Starting portfolio value
        strategy: Strategy ID
        num_days: Number of days to simulate
        seed: Random seed for reproducibility

    Returns:
        List of {'date': date, 'value': float}
    """
    if seed is not None:
        np.random.seed(seed)

    params = STRATEGY_PARAMS.get(strategy, STRATEGY_PARAMS['balanced'])

    history = []
    value = initial_value
    start_date = date.today() - timedelta(days=num_days)

    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        history.append({
            'date': current_date,
            'value': round(value, 2)
        })

        # Only update value on weekdays (skip weekends)
        if current_date.weekday() < 5:
            random_factor = np.random.normal(0, 1)
            daily_return = params['drift'] + (random_factor * params['volatility'])
            value = value * (1 + daily_return)
            value = max(value, initial_value * 0.1)  # Floor at 10% of initial

    return history


def generate_ohlcv(
    open_price: float,
    beta: float = 1.0,
    volatility: float = 0.02,
    avg_volume: int = 10000000
) -> Dict:
    """
    Generate simulated OHLCV data for a single day.

    Args:
        open_price: Opening price
        beta: Stock's beta
        volatility: Volatility parameter
        avg_volume: Average daily volume

    Returns:
        Dict with open, high, low, close, volume
    """
    daily_vol = volatility * beta

    # Generate intraday movements
    intraday_moves = np.random.normal(0, daily_vol, 4)

    # Open is given
    open_p = open_price

    # High and low based on intraday volatility
    high_p = open_p * (1 + abs(intraday_moves[0]) + abs(intraday_moves[1]) * 0.5)
    low_p = open_p * (1 - abs(intraday_moves[2]) - abs(intraday_moves[3]) * 0.5)

    # Close somewhere between high and low
    close_range = high_p - low_p
    close_p = low_p + close_range * np.random.random()

    # Volume with some randomness
    volume = int(avg_volume * (0.5 + np.random.random()))

    return {
        'open': round(open_p, 2),
        'high': round(high_p, 2),
        'low': round(low_p, 2),
        'close': round(close_p, 2),
        'volume': volume
    }


def calculate_daily_returns(prices: List[float]) -> List[float]:
    """
    Calculate daily returns from a price series.

    Args:
        prices: List of prices

    Returns:
        List of daily returns (length = len(prices) - 1)
    """
    returns = []
    for i in range(1, len(prices)):
        daily_return = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(daily_return)
    return returns


def calculate_volatility(prices: List[float]) -> float:
    """
    Calculate annualized volatility from a price series.

    Args:
        prices: List of prices

    Returns:
        Annualized volatility
    """
    returns = calculate_daily_returns(prices)
    if not returns:
        return 0.0

    daily_vol = np.std(returns)
    annualized_vol = daily_vol * np.sqrt(252)  # 252 trading days

    return annualized_vol


def simulate_market_movement(
    symbols: List[str],
    current_prices: Dict[str, float],
    market_trend: float = 0.0,
    correlation: float = 0.5
) -> Dict[str, float]:
    """
    Simulate correlated market movement for multiple stocks.

    Args:
        symbols: List of stock symbols
        current_prices: Dict of current prices
        market_trend: Overall market direction (-1 to 1)
        correlation: How correlated stocks are to each other (0 to 1)

    Returns:
        Dict of new prices
    """
    # Generate market-wide factor
    market_factor = np.random.normal(market_trend * 0.001, 0.01)

    new_prices = {}

    for symbol in symbols:
        current = current_prices.get(symbol, 100)
        beta = get_stock_beta(symbol)

        # Combine market factor with individual randomness
        individual_factor = np.random.normal(0, 0.02 * beta)
        combined_return = (correlation * market_factor * beta) + ((1 - correlation) * individual_factor)

        new_price = current * (1 + combined_return)
        new_prices[symbol] = max(new_price, 0.01)

    return new_prices
