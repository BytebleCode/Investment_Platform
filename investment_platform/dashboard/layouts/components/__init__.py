"""
Dashboard Components Package

Contains individual UI components for the dashboard.
"""
from dashboard.layouts.components.header import create_header
from dashboard.layouts.components.portfolio_summary import create_portfolio_summary
from dashboard.layouts.components.portfolio_chart import create_portfolio_chart
from dashboard.layouts.components.holdings_table import create_holdings_table
from dashboard.layouts.components.allocation_pie import create_allocation_pie
from dashboard.layouts.components.strategy_selector import create_strategy_selector
from dashboard.layouts.components.strategy_modal import create_strategy_modal
from dashboard.layouts.components.trade_history import create_trade_history

__all__ = [
    'create_header',
    'create_portfolio_summary',
    'create_portfolio_chart',
    'create_holdings_table',
    'create_allocation_pie',
    'create_strategy_selector',
    'create_strategy_modal',
    'create_trade_history',
]
