"""
Dashboard Callbacks Package

Contains Dash callback definitions for interactivity.
"""
from dashboard.callbacks.data_callbacks import register_data_callbacks
from dashboard.callbacks.trading_callbacks import register_trading_callbacks
from dashboard.callbacks.chart_callbacks import register_chart_callbacks
from dashboard.callbacks.strategy_callbacks import register_strategy_callbacks

__all__ = [
    'register_data_callbacks',
    'register_trading_callbacks',
    'register_chart_callbacks',
    'register_strategy_callbacks',
]
