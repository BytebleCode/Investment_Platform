"""
Dash Application Setup

Creates and configures the Dash application integrated with Flask.
"""
from dash import Dash, html, dcc
import dash_mantine_components as dmc

from dashboard.layouts.main_layout import create_main_layout


def create_dash_app(flask_app):
    """
    Create Dash application integrated with Flask server.

    Args:
        flask_app: Flask application instance

    Returns:
        Configured Dash application
    """
    dash_app = Dash(
        __name__,
        server=flask_app,
        url_base_pathname='/dashboard/',
        suppress_callback_exceptions=True,
        external_stylesheets=[
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        ]
    )

    # Set page title
    dash_app.title = "Investment Platform"

    # Create layout
    dash_app.layout = dmc.MantineProvider(
        theme={
            "colorScheme": "dark",
            "fontFamily": "Inter, sans-serif",
            "primaryColor": "blue",
            "components": {
                "Card": {"defaultProps": {"shadow": "sm", "radius": "md"}},
                "Button": {"defaultProps": {"radius": "md"}},
            }
        },
        children=[
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='portfolio-store', storage_type='memory'),
            dcc.Store(id='holdings-store', storage_type='memory'),
            dcc.Store(id='prices-store', storage_type='memory'),
            dcc.Interval(
                id='price-refresh-interval',
                interval=30 * 1000,  # 30 seconds
                n_intervals=0
            ),
            dcc.Interval(
                id='auto-trade-interval',
                interval=60 * 1000,  # 60 seconds
                n_intervals=0,
                disabled=True  # Disabled by default
            ),
            create_main_layout()
        ]
    )

    # Register callbacks
    register_callbacks(dash_app)

    return dash_app


def register_callbacks(dash_app):
    """Register all Dash callbacks."""
    from dashboard.callbacks.data_callbacks import register_data_callbacks
    from dashboard.callbacks.trading_callbacks import register_trading_callbacks
    from dashboard.callbacks.chart_callbacks import register_chart_callbacks
    from dashboard.callbacks.strategy_callbacks import register_strategy_callbacks

    register_data_callbacks(dash_app)
    register_trading_callbacks(dash_app)
    register_chart_callbacks(dash_app)
    register_strategy_callbacks(dash_app)
