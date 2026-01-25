"""
Strategy Callbacks

Handles strategy selection and customization.
"""
from dash import callback, Output, Input, State, no_update, ctx, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import requests

API_BASE = "http://localhost:5000/api"


def register_strategy_callbacks(app):
    """Register all strategy-related callbacks."""

    @app.callback(
        [
            Output({'type': 'strategy-active-badge', 'index': ALL}, 'style'),
            Output({'type': 'strategy-card', 'index': ALL}, 'style'),
            Output('selected-strategy-input', 'value'),
        ],
        [
            Input({'type': 'strategy-card', 'index': ALL}, 'n_clicks'),
            Input('portfolio-store', 'data'),
        ],
        State('selected-strategy-input', 'value'),
        prevent_initial_call=False
    )
    def handle_strategy_selection(card_clicks, portfolio_data, current_strategy):
        """Handle strategy card clicks and update visual selection."""
        triggered = ctx.triggered_id

        # Determine selected strategy
        if portfolio_data:
            selected = portfolio_data.get('strategy', 'balanced')
        else:
            selected = current_strategy or 'balanced'

        # If a card was clicked, update selection
        if triggered and isinstance(triggered, dict) and triggered.get('type') == 'strategy-card':
            clicked_strategy = triggered.get('index')
            if clicked_strategy:
                selected = clicked_strategy

                # Update strategy via API
                try:
                    requests.put(
                        f"{API_BASE}/portfolio/settings",
                        json={'current_strategy': selected},
                        timeout=5
                    )
                except Exception as e:
                    print(f"Error updating strategy: {e}")

        # Strategy order
        strategies = ['conservative', 'growth', 'value', 'balanced', 'aggressive']

        # Generate badge styles (show/hide based on selection)
        badge_styles = []
        card_styles = []

        for strategy_id in strategies:
            if strategy_id == selected:
                badge_styles.append({"display": "block"})
                card_styles.append({
                    "backgroundColor": "#25262b",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "borderColor": "#228be6",
                    "borderWidth": "2px"
                })
            else:
                badge_styles.append({"display": "none"})
                card_styles.append({
                    "backgroundColor": "#25262b",
                    "cursor": "pointer",
                    "transition": "all 0.2s ease",
                    "borderColor": "#373a40"
                })

        return badge_styles, card_styles, selected

    @app.callback(
        [
            Output('strategy-modal', 'opened'),
            Output('modal-strategy-id', 'value'),
            Output('modal-strategy-name', 'children'),
            Output('confidence-slider', 'value'),
            Output('frequency-selector', 'value'),
            Output('position-size-slider', 'value'),
            Output('stop-loss-slider', 'value'),
            Output('take-profit-slider', 'value'),
            Output('auto-rebalance-switch', 'checked'),
            Output('reinvest-dividends-switch', 'checked'),
        ],
        Input({'type': 'strategy-customize-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def open_strategy_modal(n_clicks):
        """Open strategy customization modal."""
        triggered = ctx.triggered_id

        if not triggered or not any(n_clicks):
            raise PreventUpdate

        strategy_id = triggered.get('index')
        if not strategy_id:
            raise PreventUpdate

        # Strategy names
        strategy_names = {
            'conservative': 'Conservative',
            'growth': 'Growth',
            'value': 'Value',
            'balanced': 'Balanced',
            'aggressive': 'Aggressive'
        }

        # Load current customization from API
        try:
            response = requests.get(
                f"{API_BASE}/strategies/customizations/{strategy_id}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return (
                    True,  # Open modal
                    strategy_id,
                    f"Customize {strategy_names.get(strategy_id, strategy_id.title())} Strategy",
                    data.get('confidence_level', 50),
                    data.get('trade_frequency', 'medium'),
                    data.get('max_position_size', 15),
                    data.get('stop_loss_percent', 10),
                    data.get('take_profit_percent', 20),
                    data.get('auto_rebalance', True),
                    data.get('reinvest_dividends', True),
                )
        except Exception as e:
            print(f"Error loading customization: {e}")

        # Return defaults
        return (
            True,
            strategy_id,
            f"Customize {strategy_names.get(strategy_id, strategy_id.title())} Strategy",
            50, 'medium', 15, 10, 20, True, True
        )

    @app.callback(
        Output('strategy-modal', 'opened', allow_duplicate=True),
        Input('modal-cancel-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_modal(n_clicks):
        """Close modal on cancel."""
        if n_clicks:
            return False
        raise PreventUpdate

    @app.callback(
        [
            Output('strategy-modal', 'opened', allow_duplicate=True),
            Output('notifications-container', 'children', allow_duplicate=True),
        ],
        Input('modal-save-btn', 'n_clicks'),
        [
            State('modal-strategy-id', 'value'),
            State('confidence-slider', 'value'),
            State('frequency-selector', 'value'),
            State('position-size-slider', 'value'),
            State('stop-loss-slider', 'value'),
            State('take-profit-slider', 'value'),
            State('auto-rebalance-switch', 'checked'),
            State('reinvest-dividends-switch', 'checked'),
        ],
        prevent_initial_call=True
    )
    def save_strategy_customization(
        n_clicks, strategy_id, confidence, frequency,
        position_size, stop_loss, take_profit, auto_rebalance, reinvest
    ):
        """Save strategy customization."""
        if not n_clicks or not strategy_id:
            raise PreventUpdate

        try:
            response = requests.put(
                f"{API_BASE}/strategies/customizations/{strategy_id}",
                json={
                    'confidence_level': confidence,
                    'trade_frequency': frequency,
                    'max_position_size': position_size,
                    'stop_loss_percent': stop_loss,
                    'take_profit_percent': take_profit,
                    'auto_rebalance': auto_rebalance,
                    'reinvest_dividends': reinvest,
                },
                timeout=5
            )

            if response.status_code == 200:
                notification = dmc.Notification(
                    title="Strategy Updated",
                    message=f"{strategy_id.title()} customization saved",
                    color="green",
                    icon=DashIconify(icon="mdi:check"),
                    action="show",
                    autoClose=3000,
                )
                return False, notification

        except Exception as e:
            notification = dmc.Notification(
                title="Save Failed",
                message=str(e),
                color="red",
                icon=DashIconify(icon="mdi:alert"),
                action="show",
                autoClose=5000,
            )
            return True, notification

        raise PreventUpdate

    # Slider value display callbacks
    @app.callback(
        Output('confidence-value-text', 'children'),
        Input('confidence-slider', 'value'),
        prevent_initial_call=True
    )
    def update_confidence_text(value):
        return f"{value}%"

    @app.callback(
        Output('position-size-value-text', 'children'),
        Input('position-size-slider', 'value'),
        prevent_initial_call=True
    )
    def update_position_size_text(value):
        return f"{value}%"

    @app.callback(
        Output('stop-loss-value-text', 'children'),
        Input('stop-loss-slider', 'value'),
        prevent_initial_call=True
    )
    def update_stop_loss_text(value):
        return f"{value}%"

    @app.callback(
        Output('take-profit-value-text', 'children'),
        Input('take-profit-slider', 'value'),
        prevent_initial_call=True
    )
    def update_take_profit_text(value):
        return f"{value}%"
