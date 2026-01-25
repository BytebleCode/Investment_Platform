"""
Trading Callbacks

Handles trade execution and auto-trading functionality.
"""
from dash import callback, Output, Input, State, no_update, ctx, html, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import requests

API_BASE = "http://localhost:5000/api"


def register_trading_callbacks(app):
    """Register all trading-related callbacks."""

    @app.callback(
        Output('auto-trade-interval', 'disabled'),
        Input('auto-trade-switch', 'checked'),
        prevent_initial_call=True
    )
    def toggle_auto_trading(checked):
        """Enable/disable auto trading interval."""
        return not checked

    @app.callback(
        Output('notifications-container', 'children', allow_duplicate=True),
        Input('auto-trade-interval', 'n_intervals'),
        State('auto-trade-switch', 'checked'),
        prevent_initial_call=True
    )
    def execute_auto_trade(n_intervals, auto_enabled):
        """Execute automatic trade when interval fires."""
        if not auto_enabled:
            raise PreventUpdate

        try:
            response = requests.post(f"{API_BASE}/trading/auto", json={}, timeout=15)
            if response.status_code in [200, 201]:
                data = response.json()

                if data.get('success'):
                    trade = data.get('trade', {})
                    trade_type = trade.get('type', 'trade').upper()
                    symbol = trade.get('symbol', '')
                    quantity = trade.get('quantity', 0)
                    price = trade.get('price', 0)

                    return dmc.Notification(
                        title=f"Auto Trade Executed",
                        message=f"{trade_type} {quantity} {symbol} @ ${price:.2f}",
                        color="green" if trade_type == "BUY" else "red",
                        icon=DashIconify(icon="mdi:check"),
                        action="show",
                        autoClose=5000,
                    )
                else:
                    # No trade executed
                    return no_update

        except Exception as e:
            return dmc.Notification(
                title="Auto Trade Failed",
                message=str(e),
                color="red",
                icon=DashIconify(icon="mdi:alert"),
                action="show",
                autoClose=5000,
            )

        raise PreventUpdate

    @app.callback(
        Output('notifications-container', 'children', allow_duplicate=True),
        Input('manual-trade-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def execute_manual_trade(n_clicks):
        """Execute a manual trade (uses auto-trade logic)."""
        if not n_clicks:
            raise PreventUpdate

        try:
            response = requests.post(f"{API_BASE}/trading/auto", json={}, timeout=15)
            if response.status_code in [200, 201]:
                data = response.json()

                if data.get('success'):
                    trade = data.get('trade', {})
                    trade_type = trade.get('type', 'trade').upper()
                    symbol = trade.get('symbol', '')
                    quantity = trade.get('quantity', 0)
                    price = trade.get('price', 0)

                    return dmc.Notification(
                        title=f"Trade Executed",
                        message=f"{trade_type} {quantity} {symbol} @ ${price:.2f}",
                        color="green" if trade_type == "BUY" else "red",
                        icon=DashIconify(icon="mdi:check"),
                        action="show",
                        autoClose=5000,
                    )
                else:
                    return dmc.Notification(
                        title="No Trade Available",
                        message=data.get('reason', 'No valid trade opportunity'),
                        color="yellow",
                        icon=DashIconify(icon="mdi:information"),
                        action="show",
                        autoClose=3000,
                    )

        except Exception as e:
            return dmc.Notification(
                title="Trade Failed",
                message=str(e),
                color="red",
                icon=DashIconify(icon="mdi:alert"),
                action="show",
                autoClose=5000,
            )

        raise PreventUpdate

    @app.callback(
        Output('notifications-container', 'children', allow_duplicate=True),
        Output('portfolio-store', 'data', allow_duplicate=True),
        Input('reset-portfolio-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_portfolio(n_clicks):
        """Reset portfolio to initial state."""
        if not n_clicks:
            raise PreventUpdate

        try:
            response = requests.post(f"{API_BASE}/portfolio/reset", timeout=10)
            if response.status_code == 200:
                notification = dmc.Notification(
                    title="Portfolio Reset",
                    message="Your portfolio has been reset to initial state",
                    color="blue",
                    icon=DashIconify(icon="mdi:restore"),
                    action="show",
                    autoClose=3000,
                )

                # Return empty portfolio data to trigger refresh
                return notification, None

        except Exception as e:
            return dmc.Notification(
                title="Reset Failed",
                message=str(e),
                color="red",
                icon=DashIconify(icon="mdi:alert"),
                action="show",
                autoClose=5000,
            ), no_update

        raise PreventUpdate

    @app.callback(
        [
            Output('trade-history-container', 'children'),
            Output('trade-count-badge', 'children'),
            Output('trades-empty-state', 'style'),
        ],
        [
            Input('price-refresh-interval', 'n_intervals'),
            Input('trade-filter', 'value'),
        ],
        prevent_initial_call=False
    )
    def update_trade_history(n_intervals, filter_value):
        """Update trade history display."""
        try:
            params = {}
            if filter_value and filter_value != 'all':
                params['type'] = filter_value

            response = requests.get(f"{API_BASE}/trades", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                trades = data.get('trades', [])
                total_count = data.get('total_count', 0)

                if not trades:
                    return [], f"0 trades", {"display": "block"}

                # Create trade cards
                from dashboard.layouts.components.trade_history import create_trade_card
                trade_cards = [create_trade_card(trade) for trade in trades[:50]]

                count_text = f"{total_count} trade{'s' if total_count != 1 else ''}"

                return trade_cards, count_text, {"display": "none"}

        except Exception as e:
            print(f"Error loading trades: {e}")

        return [], "0 trades", {"display": "block"}
