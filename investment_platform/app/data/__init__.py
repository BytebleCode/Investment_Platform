"""
Data Definitions Package

Contains static data definitions for stocks and strategies.
"""
from app.data.stock_universe import (
    STOCK_UNIVERSE,
    SECTORS,
    get_all_symbols,
    get_stock_info,
    get_stocks_by_sector,
    get_sector_symbols,
    get_stock_beta,
    get_stock_name,
    get_stock_sector,
    is_valid_symbol
)

from app.data.strategies import (
    STRATEGIES,
    STRATEGY_IDS,
    DEFAULT_CUSTOMIZATION,
    get_strategy,
    get_all_strategies,
    get_strategy_stocks,
    get_strategy_risk_level,
    get_strategy_volatility,
    get_strategy_drift,
    get_target_investment_ratio,
    get_trade_frequency_seconds,
    is_valid_strategy,
    get_strategy_summary
)

__all__ = [
    # Stock Universe
    'STOCK_UNIVERSE',
    'SECTORS',
    'get_all_symbols',
    'get_stock_info',
    'get_stocks_by_sector',
    'get_sector_symbols',
    'get_stock_beta',
    'get_stock_name',
    'get_stock_sector',
    'is_valid_symbol',
    # Strategies
    'STRATEGIES',
    'STRATEGY_IDS',
    'DEFAULT_CUSTOMIZATION',
    'get_strategy',
    'get_all_strategies',
    'get_strategy_stocks',
    'get_strategy_risk_level',
    'get_strategy_volatility',
    'get_strategy_drift',
    'get_target_investment_ratio',
    'get_trade_frequency_seconds',
    'is_valid_strategy',
    'get_strategy_summary'
]
