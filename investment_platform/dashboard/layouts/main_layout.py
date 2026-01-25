"""
Main Layout Component

Defines the overall structure and layout of the dashboard.
"""
from dash import html, dcc
import dash_mantine_components as dmc

from dashboard.layouts.components.header import create_header
from dashboard.layouts.components.portfolio_summary import create_portfolio_summary
from dashboard.layouts.components.portfolio_chart import create_portfolio_chart
from dashboard.layouts.components.holdings_table import create_holdings_table
from dashboard.layouts.components.allocation_pie import create_allocation_pie
from dashboard.layouts.components.strategy_selector import create_strategy_selector
from dashboard.layouts.components.strategy_modal import create_strategy_modal
from dashboard.layouts.components.trade_history import create_trade_history


def create_main_layout():
    """
    Create the main dashboard layout.

    Layout structure:
    ┌─────────────────────────────────────────┐
    │            HEADER / NAVBAR              │
    ├───────────────────────┬─────────────────┤
    │   PORTFOLIO CHART     │ PORTFOLIO       │
    │   (Line Chart)        │ SUMMARY         │
    ├───────────────────────┼─────────────────┤
    │   STRATEGY SELECTOR   │ ALLOCATION      │
    │   (5 Cards)           │ PIE CHART       │
    ├───────────────────────┴─────────────────┤
    │   HOLDINGS TABLE                        │
    ├─────────────────────────────────────────┤
    │   TRADE HISTORY                         │
    └─────────────────────────────────────────┘
    """
    return dmc.Container(
        fluid=True,
        px="md",
        py="sm",
        style={"backgroundColor": "#1a1b1e", "minHeight": "100vh"},
        children=[
            # Header
            create_header(),

            dmc.Space(h="md"),

            # Main content grid
            dmc.Grid(
                gutter="md",
                children=[
                    # Left column - Portfolio Chart
                    dmc.GridCol(
                        span={"base": 12, "md": 8},
                        children=[create_portfolio_chart()]
                    ),

                    # Right column - Portfolio Summary
                    dmc.GridCol(
                        span={"base": 12, "md": 4},
                        children=[create_portfolio_summary()]
                    ),
                ]
            ),

            dmc.Space(h="md"),

            # Strategy and Allocation row
            dmc.Grid(
                gutter="md",
                children=[
                    # Strategy Selector
                    dmc.GridCol(
                        span={"base": 12, "md": 8},
                        children=[create_strategy_selector()]
                    ),

                    # Allocation Pie Chart
                    dmc.GridCol(
                        span={"base": 12, "md": 4},
                        children=[create_allocation_pie()]
                    ),
                ]
            ),

            dmc.Space(h="md"),

            # Holdings Table
            create_holdings_table(),

            dmc.Space(h="md"),

            # Trade History
            create_trade_history(),

            # Strategy Customization Modal
            create_strategy_modal(),

            # Notifications
            html.Div(id='notifications-container'),
        ]
    )
