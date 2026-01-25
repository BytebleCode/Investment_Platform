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
    get_strategy_summary,
    get_strategy_sector_allocation,
    get_strategy_signals
)

from app.data.symbol_universe import (
    SYMBOL_UNIVERSE,
    SECTOR_METADATA,
    get_all_sectors,
    get_subsectors,
    get_sector_symbols as get_universe_sector_symbols,
    get_symbols_by_path,
    get_sector_for_symbol,
    get_sector_metadata
)

__all__ = [
    # Stock Universe (legacy)
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
    'get_strategy_summary',
    'get_strategy_sector_allocation',
    'get_strategy_signals',
    # Symbol Universe (macro system)
    'SYMBOL_UNIVERSE',
    'SECTOR_METADATA',
    'get_all_sectors',
    'get_subsectors',
    'get_universe_sector_symbols',
    'get_symbols_by_path',
    'get_sector_for_symbol',
    'get_sector_metadata'
]
