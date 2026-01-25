"""
Business Logic Services Package

Contains core business logic including trading engine, price generation,
portfolio calculations, and market data service.
"""
from app.services.price_generator import (
    generate_price,
    generate_price_with_seasonality,
    generate_price_series,
    generate_reproducible_prices,
    generate_portfolio_history,
    generate_ohlcv,
    update_all_prices,
    set_simulation_seed,
    calculate_daily_returns,
    calculate_volatility,
    simulate_market_movement,
    STRATEGY_PARAMS
)

from app.services.portfolio_service import (
    calculate_portfolio_value,
    calculate_invested_value,
    calculate_unrealized_gain,
    calculate_total_unrealized_gains,
    calculate_realized_gain,
    calculate_estimated_tax,
    calculate_new_avg_cost,
    calculate_investment_ratio,
    calculate_total_return,
    calculate_position_value,
    calculate_position_weight,
    calculate_sector_allocation,
    get_portfolio_summary,
    to_decimal,
    quantize_currency,
    quantize_price,
    TAX_RATE
)

from app.services.trading_engine import (
    TradingEngine,
    auto_trade,
    execute_trade,
    determine_trade_type,
    select_stock_for_trade,
    calculate_buy_quantity,
    calculate_sell_quantity,
    calculate_execution_price,
    calculate_trade_fees,
    validate_buy_trade,
    validate_sell_trade,
    generate_trade_id
)

from app.services.market_data_service import (
    MarketDataService,
    get_market_data_service,
    RateLimiter
)

__all__ = [
    # Price Generator
    'generate_price',
    'generate_price_with_seasonality',
    'generate_price_series',
    'generate_reproducible_prices',
    'generate_portfolio_history',
    'generate_ohlcv',
    'update_all_prices',
    'set_simulation_seed',
    'calculate_daily_returns',
    'calculate_volatility',
    'simulate_market_movement',
    'STRATEGY_PARAMS',
    # Portfolio Service
    'calculate_portfolio_value',
    'calculate_invested_value',
    'calculate_unrealized_gain',
    'calculate_total_unrealized_gains',
    'calculate_realized_gain',
    'calculate_estimated_tax',
    'calculate_new_avg_cost',
    'calculate_investment_ratio',
    'calculate_total_return',
    'calculate_position_value',
    'calculate_position_weight',
    'calculate_sector_allocation',
    'get_portfolio_summary',
    'to_decimal',
    'quantize_currency',
    'quantize_price',
    'TAX_RATE',
    # Trading Engine
    'TradingEngine',
    'auto_trade',
    'execute_trade',
    'determine_trade_type',
    'select_stock_for_trade',
    'calculate_buy_quantity',
    'calculate_sell_quantity',
    'calculate_execution_price',
    'calculate_trade_fees',
    'validate_buy_trade',
    'validate_sell_trade',
    'generate_trade_id',
    # Market Data Service
    'MarketDataService',
    'get_market_data_service',
    'RateLimiter'
]
