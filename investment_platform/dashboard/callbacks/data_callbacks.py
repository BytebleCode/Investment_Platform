"""
Data Callbacks

Handles data loading and refreshing for the dashboard.
"""
from dash import callback, Output, Input, State, no_update, ctx
from dash.exceptions import PreventUpdate
import requests
from datetime import datetime

API_BASE = "http://localhost:5000/api"


def register_data_callbacks(app):
    """Register all data-related callbacks."""

    @app.callback(
        [
            Output('portfolio-store', 'data'),
            Output('holdings-store', 'data'),
            Output('prices-store', 'data'),
            Output('last-update-text', 'children'),
        ],
        [
            Input('price-refresh-interval', 'n_intervals'),
            Input('refresh-data-btn', 'n_clicks'),
            Input('url', 'pathname'),
        ],
        prevent_initial_call=False
    )
    def refresh_all_data(n_intervals, n_clicks, pathname):
        """Refresh all dashboard data."""
        try:
            # Get trading summary (includes portfolio, holdings, prices)
            response = requests.get(f"{API_BASE}/trading/summary", timeout=10)
            if response.status_code == 200:
                data = response.json()

                portfolio_data = {
                    'initial_value': data.get('initial_value', 100000),
                    'current_cash': data.get('current_cash', 100000),
                    'invested_value': data.get('invested_value', 0),
                    'total_value': data.get('total_value', 100000),
                    'unrealized_gains': data.get('unrealized_gains', 0),
                    'realized_gains': data.get('realized_gains', 0),
                    'total_return_dollar': data.get('total_return_dollar', 0),
                    'total_return_percent': data.get('total_return_percent', 0),
                    'investment_ratio': data.get('investment_ratio', 0),
                    'estimated_tax': data.get('estimated_tax', 0),
                    'strategy': data.get('strategy', 'balanced'),
                }

                holdings_data = data.get('holdings', [])

                # Extract prices from holdings
                prices_data = {
                    h['symbol']: h.get('current_price', h.get('avg_cost', 0))
                    for h in holdings_data
                }

                timestamp = datetime.now().strftime("%H:%M:%S")
                last_update = f"Last updated: {timestamp}"

                return portfolio_data, holdings_data, prices_data, last_update

        except Exception as e:
            print(f"Error refreshing data: {e}")

        raise PreventUpdate

    @app.callback(
        [
            Output('stat-cash', 'children'),
            Output('stat-invested', 'children'),
            Output('stat-return', 'children'),
            Output('stat-return', 'style'),
            Output('stat-tax', 'children'),
            Output('investment-ratio-text', 'children'),
            Output('investment-ratio-bar', 'value'),
        ],
        Input('portfolio-store', 'data'),
        prevent_initial_call=True
    )
    def update_portfolio_summary(portfolio_data):
        """Update portfolio summary stats."""
        if not portfolio_data:
            raise PreventUpdate

        cash = portfolio_data.get('current_cash', 0)
        invested = portfolio_data.get('invested_value', 0)
        total_return = portfolio_data.get('total_return_dollar', 0)
        return_pct = portfolio_data.get('total_return_percent', 0)
        tax = portfolio_data.get('estimated_tax', 0)
        inv_ratio = portfolio_data.get('investment_ratio', 0)

        # Determine return color
        return_color = "#40c057" if total_return >= 0 else "#fa5252"
        return_style = {"color": return_color}

        # Format values
        cash_text = f"${cash:,.2f}"
        invested_text = f"${invested:,.2f}"
        return_text = f"${total_return:+,.2f} ({return_pct:+.2f}%)"
        tax_text = f"${tax:,.2f}"
        ratio_text = f"{inv_ratio * 100:.1f}%"
        ratio_value = inv_ratio * 100

        return cash_text, invested_text, return_text, return_style, tax_text, ratio_text, ratio_value

    @app.callback(
        [
            Output('holdings-table', 'data'),
            Output('holdings-count-badge', 'children'),
            Output('holdings-empty-state', 'style'),
        ],
        Input('holdings-store', 'data'),
        prevent_initial_call=True
    )
    def update_holdings_table(holdings_data):
        """Update holdings table data."""
        if not holdings_data:
            return [], "0 positions", {"display": "block"}

        # Format data for table
        table_data = []
        for h in holdings_data:
            table_data.append({
                'symbol': h.get('symbol', ''),
                'name': h.get('name', ''),
                'sector': h.get('sector', ''),
                'quantity': h.get('quantity', 0),
                'avg_cost': h.get('avg_cost', 0),
                'current_price': h.get('current_price', h.get('avg_cost', 0)),
                'market_value': h.get('market_value', 0),
                'unrealized_gain': h.get('unrealized_gain', 0),
                'unrealized_gain_pct': h.get('unrealized_gain_pct', 0),
            })

        count_text = f"{len(table_data)} position{'s' if len(table_data) != 1 else ''}"
        empty_style = {"display": "none"} if table_data else {"display": "block"}

        return table_data, count_text, empty_style

    @app.callback(
        Output('market-status-badge', 'children'),
        Output('market-status-badge', 'color'),
        Input('price-refresh-interval', 'n_intervals'),
        prevent_initial_call=False
    )
    def update_market_status(n_intervals):
        """Update market status indicator."""
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                market_status = data.get('market_status', 'closed')

                if market_status == 'open':
                    return "Market Open", "green"
                else:
                    return "Market Closed", "gray"
        except Exception:
            pass

        return "Market Closed", "gray"

    @app.callback(
        Output('current-strategy-text', 'children'),
        Input('portfolio-store', 'data'),
        prevent_initial_call=True
    )
    def update_current_strategy_text(portfolio_data):
        """Update current strategy display."""
        if not portfolio_data:
            raise PreventUpdate

        strategy = portfolio_data.get('strategy', 'balanced')
        return f"Current: {strategy.title()}"
