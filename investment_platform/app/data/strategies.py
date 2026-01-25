"""
Macro Trading Strategy Definitions

Contains 5 macro-driven investment strategies that:
1. Define sector allocations (not hardcoded tickers)
2. Dynamically select symbols from available universe
3. Integrate FRED API macro signals for regime detection
4. Support future expansion when more symbols become available

Each strategy targets a specific macro regime/theme.
"""


# ============================================================================
# MACRO PRESET STRATEGIES
# ============================================================================

STRATEGIES = {
    # ========================================================================
    # STRATEGY 1: MONETARY POLICY (Rate Regime)
    # ========================================================================
    'monetary_policy': {
        'id': 'monetary_policy',
        'name': 'Monetary Policy',
        'description': 'Trades rate-sensitive assets based on Fed policy. Banks benefit from rate hikes, utilities from cuts. Treasury futures for duration exposure.',
        'risk_level': 3,
        'expected_return': (5, 18),
        'color': '#3b82f6',  # Blue
        'volatility': 0.012,
        'daily_drift': 0.0003,
        'trade_frequency_seconds': 90,
        'target_investment_ratio': 0.7,
        'max_position_pct': 0.12,

        # DYNAMIC SYMBOL SELECTION
        'sector_allocation': {
            'financials.banks': 0.35,
            'financials.asset_managers': 0.10,
            'financials.exchanges': 0.10,
            'utilities.electric': 0.25,
            'futures.treasury': 0.10,
            'real_estate.data_centers': 0.10
        },
        'max_symbols': 20,
        'min_symbols': 12,

        # MACRO SIGNALS (FRED API)
        'signals': {
            'fed_funds_rate': {'series': 'FEDFUNDS', 'weight': 0.30},
            'yield_curve_2y10y': {'series': 'T10Y2Y', 'weight': 0.35},
            'real_rates': {'series': 'DFII10', 'weight': 0.20},
            'financial_conditions': {'series': 'NFCI', 'weight': 0.15}
        },

        # Fallback static stocks (used if sector_allocation fails)
        'stocks': ['JPM', 'BAC', 'GS', 'MS', 'BLK', 'CME', 'NEE', 'DUK', 'AEP', 'SO']
    },

    # ========================================================================
    # STRATEGY 2: INFLATION HEDGE (Price Pressure Regime)
    # ========================================================================
    'inflation_hedge': {
        'id': 'inflation_hedge',
        'name': 'Inflation Hedge',
        'description': 'Commodity producers and real assets for inflationary periods. Energy, materials, gold, and agricultural exposure. Best when CPI rising.',
        'risk_level': 4,
        'expected_return': (8, 25),
        'color': '#f59e0b',  # Amber
        'volatility': 0.018,
        'daily_drift': 0.0004,
        'trade_frequency_seconds': 75,
        'target_investment_ratio': 0.75,
        'max_position_pct': 0.10,

        'sector_allocation': {
            'energy.integrated': 0.18,
            'energy.exploration': 0.15,
            'energy.refining': 0.10,
            'materials.mining': 0.15,
            'materials.chemicals': 0.12,
            'materials.agriculture': 0.05,
            'futures.energy': 0.10,
            'futures.metals': 0.10,
            'futures.agriculture': 0.05
        },
        'max_symbols': 22,
        'min_symbols': 15,

        'signals': {
            'cpi_yoy': {'series': 'CPIAUCSL', 'weight': 0.35, 'transform': 'yoy'},
            'core_pce': {'series': 'PCEPILFE', 'weight': 0.25, 'transform': 'yoy'},
            'breakeven_10y': {'series': 'T10YIE', 'weight': 0.25},
            'commodity_index': {'series': 'PPIACO', 'weight': 0.15, 'transform': 'yoy'}
        },

        'stocks': ['XOM', 'CVX', 'COP', 'EOG', 'FCX', 'NEM', 'APD', 'LIN', 'MPC', 'PSX']
    },

    # ========================================================================
    # STRATEGY 3: GROWTH EXPANSION (Risk-On Regime)
    # ========================================================================
    'growth_expansion': {
        'id': 'growth_expansion',
        'name': 'Growth Expansion',
        'description': 'High-beta growth and cyclicals for economic expansion. Tech, industrials, discretionary. Best when PMI rising and credit tight.',
        'risk_level': 5,
        'expected_return': (12, 35),
        'color': '#22c55e',  # Green
        'volatility': 0.022,
        'daily_drift': 0.0005,
        'trade_frequency_seconds': 60,
        'target_investment_ratio': 0.85,
        'max_position_pct': 0.08,

        'sector_allocation': {
            'technology.semiconductors': 0.25,
            'technology.software': 0.15,
            'technology.internet': 0.10,
            'industrials.machinery': 0.10,
            'industrials.transport': 0.10,
            'consumer_discretionary.retail': 0.10,
            'consumer_discretionary.restaurants': 0.05,
            'financials.payments': 0.10,
            'currency.pairs': 0.03,
            'crypto.major': 0.02
        },
        'max_symbols': 25,
        'min_symbols': 18,

        'signals': {
            'ism_pmi': {'series': 'ISM/MAN_PMI', 'weight': 0.30},
            'industrial_production': {'series': 'INDPRO', 'weight': 0.20, 'transform': 'yoy'},
            'retail_sales': {'series': 'RSAFS', 'weight': 0.20, 'transform': 'yoy'},
            'leading_index': {'series': 'USSLIND', 'weight': 0.30}
        },

        'stocks': ['NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'CAT', 'DE', 'UNP', 'HD', 'V']
    },

    # ========================================================================
    # STRATEGY 4: DEFENSIVE QUALITY (Risk-Off Regime)
    # ========================================================================
    'defensive_quality': {
        'id': 'defensive_quality',
        'name': 'Defensive Quality',
        'description': 'Low-volatility defensives for late cycle and recession. Utilities, healthcare, staples. Gold as safe haven. Capital preservation focus.',
        'risk_level': 1,
        'expected_return': (2, 8),
        'color': '#8b5cf6',  # Purple
        'volatility': 0.006,
        'daily_drift': 0.0002,
        'trade_frequency_seconds': 120,
        'target_investment_ratio': 0.6,
        'max_position_pct': 0.15,

        'sector_allocation': {
            'utilities.electric': 0.28,
            'consumer_staples.food': 0.18,
            'consumer_staples.household': 0.10,
            'healthcare.pharma': 0.22,
            'healthcare.services': 0.12,
            'futures.metals': 0.10  # Gold
        },
        'max_symbols': 22,
        'min_symbols': 15,

        'signals': {
            'ism_pmi': {'series': 'ISM/MAN_PMI', 'weight': 0.25, 'invert': True},
            'yield_curve': {'series': 'T10Y2Y', 'weight': 0.25, 'invert': True},
            'credit_spreads': {'series': 'BAMLH0A0HYM2', 'weight': 0.30},
            'unemployment_claims': {'series': 'ICSA', 'weight': 0.20}
        },

        'stocks': ['NEE', 'DUK', 'SO', 'JNJ', 'PFE', 'MRK', 'PG', 'KO', 'CL', 'KMB']
    },

    # ========================================================================
    # STRATEGY 5: LIQUIDITY CYCLE (Credit Conditions Regime)
    # ========================================================================
    'liquidity_cycle': {
        'id': 'liquidity_cycle',
        'name': 'Liquidity Cycle',
        'description': 'Trades liquidity-sensitive assets based on credit conditions. Risk-on when liquidity loose, defensive when tightening. Tracks NFCI and HY spreads.',
        'risk_level': 4,
        'expected_return': (6, 22),
        'color': '#ef4444',  # Red
        'volatility': 0.016,
        'daily_drift': 0.00035,
        'trade_frequency_seconds': 70,
        'target_investment_ratio': 0.7,
        'max_position_pct': 0.10,

        'sector_allocation': {
            'technology.semiconductors': 0.18,
            'financials.banks': 0.15,
            'financials.asset_managers': 0.12,
            'real_estate.data_centers': 0.12,
            'industrials.aerospace': 0.12,
            'consumer_discretionary.retail': 0.11,
            'futures.metals': 0.10,
            'currency.pairs': 0.05,
            'crypto.major': 0.05
        },
        'max_symbols': 24,
        'min_symbols': 16,

        'signals': {
            'credit_spreads_hy': {'series': 'BAMLH0A0HYM2', 'weight': 0.35},
            'financial_conditions': {'series': 'NFCI', 'weight': 0.25},
            'm2_growth': {'series': 'M2SL', 'weight': 0.20, 'transform': 'yoy'},
            'bank_lending': {'series': 'DRTSCILM', 'weight': 0.20}
        },

        'stocks': ['NVDA', 'AMD', 'JPM', 'BLK', 'BX', 'EQIX', 'BA', 'LMT', 'HD', 'COIN']
    }
}

# Strategy IDs for iteration (in display order)
STRATEGY_IDS = ['monetary_policy', 'inflation_hedge', 'growth_expansion', 'defensive_quality', 'liquidity_cycle']

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


# ============================================================================
# STRATEGY ACCESS FUNCTIONS
# ============================================================================

def get_strategy(strategy_id: str) -> dict:
    """
    Get strategy configuration by ID.

    Args:
        strategy_id: Strategy identifier

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
    Uses dynamic symbol selection if sector_allocation is defined.

    Args:
        strategy_id: Strategy identifier

    Returns:
        List of stock symbols or empty list
    """
    strategy = get_strategy(strategy_id)
    if not strategy:
        return []

    # Use dynamic selection if sector_allocation exists
    if strategy.get('sector_allocation'):
        # Lazy import to avoid circular dependency
        from app.services.symbol_selector import get_symbols_for_strategy
        return get_symbols_for_strategy(strategy)

    # Fall back to static stocks
    return strategy.get('stocks', [])


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

    # Get dynamic stocks count
    stocks = get_strategy_stocks(strategy_id)

    return {
        'id': strategy['id'],
        'name': strategy['name'],
        'description': strategy['description'],
        'risk_level': strategy['risk_level'],
        'expected_return_min': strategy['expected_return'][0],
        'expected_return_max': strategy['expected_return'][1],
        'color': strategy['color'],
        'num_stocks': len(stocks),
        'sector_allocation': strategy.get('sector_allocation', {}),
        'has_macro_signals': bool(strategy.get('signals'))
    }


def get_strategy_sector_allocation(strategy_id: str) -> dict:
    """
    Get the sector allocation for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Dict mapping sector paths to weights
    """
    strategy = get_strategy(strategy_id)
    if not strategy:
        return {}
    return strategy.get('sector_allocation', {})


def get_strategy_signals(strategy_id: str) -> dict:
    """
    Get the macro signal configuration for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Dict of signal configurations
    """
    strategy = get_strategy(strategy_id)
    if not strategy:
        return {}
    return strategy.get('signals', {})
