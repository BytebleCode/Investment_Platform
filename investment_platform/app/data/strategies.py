"""
Investment Strategy Definitions

Contains the 5 investment strategies with their parameters, risk levels,
target stocks, and trading behavior configurations.
"""

# Investment Strategies
# Note: Using only symbols available in local CSV data (alphabetically up to RVTY)
STRATEGIES = {
    'conservative': {
        'id': 'conservative',
        'name': 'Conservative',
        'description': 'Low-risk strategy focused on stable, dividend-paying blue chips',
        'risk_level': 1,
        'expected_return': (2, 6),  # Annual return range in percent
        'stocks': ['JNJ', 'PG', 'KO', 'PEP', 'DUK', 'NEE', 'MRK', 'CL', 'KMB', 'PEG'],
        'volatility': 0.005,
        'daily_drift': 0.00015,
        'trade_frequency_seconds': 120,
        'target_investment_ratio': 0.6,
        'max_position_pct': 0.15,
        'color': '#22c55e'  # Green
    },
    'growth': {
        'id': 'growth',
        'name': 'Growth',
        'description': 'High-growth focus on technology and innovation leaders',
        'risk_level': 4,
        'expected_return': (10, 25),
        'stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'AMD', 'CRM', 'NFLX', 'NOW', 'ADBE'],
        'volatility': 0.015,
        'daily_drift': 0.0005,
        'trade_frequency_seconds': 60,
        'target_investment_ratio': 0.8,
        'max_position_pct': 0.20,
        'color': '#3b82f6'  # Blue
    },
    'value': {
        'id': 'value',
        'name': 'Value',
        'description': 'Focus on undervalued stocks with strong fundamentals',
        'risk_level': 2,
        'expected_return': (6, 12),
        'stocks': ['BLK', 'JPM', 'BAC', 'GS', 'MA', 'PFE', 'CVS', 'IBM', 'MET', 'PRU'],
        'volatility': 0.008,
        'daily_drift': 0.0003,
        'trade_frequency_seconds': 90,
        'target_investment_ratio': 0.7,
        'max_position_pct': 0.18,
        'color': '#a855f7'  # Purple
    },
    'balanced': {
        'id': 'balanced',
        'name': 'Balanced',
        'description': 'Diversified mix of growth and stability across sectors',
        'risk_level': 3,
        'expected_return': (5, 12),
        'stocks': ['AAPL', 'MSFT', 'JNJ', 'PG', 'JPM', 'KO', 'CAT', 'HON', 'LMT', 'MMM'],
        'volatility': 0.01,
        'daily_drift': 0.00035,
        'trade_frequency_seconds': 75,
        'target_investment_ratio': 0.7,
        'max_position_pct': 0.15,
        'color': '#f59e0b'  # Amber
    },
    'aggressive': {
        'id': 'aggressive',
        'name': 'Aggressive',
        'description': 'High-risk, high-reward speculation on volatile stocks',
        'risk_level': 5,
        'expected_return': (-20, 50),
        'stocks': ['COIN', 'PLTR', 'NVDA', 'AMD', 'BA', 'CRWD', 'PANW', 'ABNB'],
        'volatility': 0.025,
        'daily_drift': 0.0004,
        'trade_frequency_seconds': 45,
        'target_investment_ratio': 0.9,
        'max_position_pct': 0.25,
        'color': '#ef4444'  # Red
    }
}

# Strategy IDs for iteration
STRATEGY_IDS = ['conservative', 'growth', 'value', 'balanced', 'aggressive']

# Default customization values
DEFAULT_CUSTOMIZATION = {
    'confidence_level': 50,
    'trade_frequency': 'medium',
    'max_position_size': 15,
    'stop_loss_percent': 10,
    'take_profit_percent': 20,
    'auto_rebalance': True,
    'reinvest_dividends': True
}

# Trade frequency mappings (multiplier for base trade_frequency_seconds)
TRADE_FREQUENCY_MULTIPLIERS = {
    'low': 2.0,     # Trade half as often
    'medium': 1.0,  # Use base frequency
    'high': 0.5     # Trade twice as often
}


def get_strategy(strategy_id: str) -> dict:
    """
    Get strategy configuration by ID.

    Args:
        strategy_id: Strategy identifier (conservative, growth, etc.)

    Returns:
        Strategy dict or None if not found
    """
    return STRATEGIES.get(strategy_id.lower())


def get_all_strategies() -> list:
    """
    Get all strategies as a list.

    Returns:
        List of strategy dicts
    """
    return list(STRATEGIES.values())


def get_strategy_stocks(strategy_id: str) -> list:
    """
    Get list of stock symbols for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        List of stock symbols or empty list
    """
    strategy = get_strategy(strategy_id)
    return strategy['stocks'] if strategy else []


def get_strategy_risk_level(strategy_id: str) -> int:
    """
    Get risk level (1-5) for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Risk level or 3 (balanced) if not found
    """
    strategy = get_strategy(strategy_id)
    return strategy['risk_level'] if strategy else 3


def get_strategy_volatility(strategy_id: str) -> float:
    """
    Get volatility parameter for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Volatility value or 0.01 (balanced) if not found
    """
    strategy = get_strategy(strategy_id)
    return strategy['volatility'] if strategy else 0.01


def get_strategy_drift(strategy_id: str) -> float:
    """
    Get daily drift parameter for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Daily drift value
    """
    strategy = get_strategy(strategy_id)
    return strategy['daily_drift'] if strategy else 0.00035


def get_target_investment_ratio(strategy_id: str) -> float:
    """
    Get target investment ratio for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Target ratio (0-1)
    """
    strategy = get_strategy(strategy_id)
    return strategy['target_investment_ratio'] if strategy else 0.7


def get_trade_frequency_seconds(strategy_id: str, frequency: str = 'medium') -> int:
    """
    Get trade frequency in seconds, adjusted by user preference.

    Args:
        strategy_id: Strategy identifier
        frequency: User preference (low/medium/high)

    Returns:
        Seconds between trades
    """
    strategy = get_strategy(strategy_id)
    base_seconds = strategy['trade_frequency_seconds'] if strategy else 75
    multiplier = TRADE_FREQUENCY_MULTIPLIERS.get(frequency, 1.0)
    return int(base_seconds * multiplier)


def is_valid_strategy(strategy_id: str) -> bool:
    """Check if strategy ID is valid."""
    return strategy_id.lower() in STRATEGIES


def get_strategy_summary(strategy_id: str) -> dict:
    """
    Get a summary of strategy for display.

    Returns:
        Dict with id, name, description, risk_level, expected_return, color
    """
    strategy = get_strategy(strategy_id)
    if not strategy:
        return None

    return {
        'id': strategy['id'],
        'name': strategy['name'],
        'description': strategy['description'],
        'risk_level': strategy['risk_level'],
        'expected_return_min': strategy['expected_return'][0],
        'expected_return_max': strategy['expected_return'][1],
        'color': strategy['color'],
        'num_stocks': len(strategy['stocks'])
    }
