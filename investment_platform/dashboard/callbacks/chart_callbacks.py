"""
Chart Callbacks

Handles portfolio chart and allocation pie chart updates.
"""
from dash import callback, Output, Input, State, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests

API_BASE = "http://localhost:5000/api"

# Dark theme colors
COLORS = {
    'background': '#1e1f23',
    'paper': '#25262b',
    'text': '#c1c2c5',
    'grid': '#373a40',
    'line': '#228be6',
    'positive': '#40c057',
    'negative': '#fa5252',
}

# Sector colors for pie chart
SECTOR_COLORS = {
    'Technology': '#228be6',
    'Healthcare': '#40c057',
    'Finance': '#fab005',
    'Consumer': '#7950f2',
    'Energy': '#fd7e14',
    'Industrial': '#868e96',
    'Utilities': '#20c997',
    'Speculative': '#e64980',
    'Cash': '#495057',
}


def register_chart_callbacks(app):
    """Register all chart-related callbacks."""

    @app.callback(
        [
            Output('portfolio-chart', 'figure'),
            Output('chart-total-value', 'children'),
            Output('chart-period-change', 'children'),
            Output('chart-period-change', 'style'),
            Output('chart-period-return', 'children'),
            Output('chart-period-return', 'style'),
        ],
        [
            Input('chart-time-range', 'value'),
            Input('portfolio-store', 'data'),
        ],
        prevent_initial_call=False
    )
    def update_portfolio_chart(time_range, portfolio_data):
        """Update portfolio performance chart."""
        # Calculate days based on time range
        days_map = {
            '1W': 7,
            '1M': 30,
            '3M': 90,
            '6M': 180,
            '1Y': 365,
        }
        num_days = days_map.get(time_range, 30)

        # Generate simulated historical data
        # In production, this would come from actual portfolio history
        import numpy as np
        np.random.seed(42)  # For consistent demo data

        initial_value = 100000
        if portfolio_data:
            current_value = portfolio_data.get('total_value', initial_value)
        else:
            current_value = initial_value

        # Generate dates
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(num_days, -1, -1)]

        # Generate values (random walk ending at current value)
        volatility = 0.01
        values = [initial_value]
        for i in range(1, len(dates) - 1):
            change = np.random.normal(0.0003, volatility)
            values.append(values[-1] * (1 + change))
        values.append(current_value)  # End at current value

        # Create figure
        fig = go.Figure()

        # Add area chart
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode='lines',
            name='Portfolio Value',
            line=dict(color=COLORS['line'], width=2),
            fill='tozeroy',
            fillcolor='rgba(34, 139, 230, 0.1)',
            hovertemplate='%{x|%b %d}<br>$%{y:,.2f}<extra></extra>'
        ))

        # Update layout
        fig.update_layout(
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(
                showgrid=False,
                showline=False,
                tickformat='%b %d',
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=COLORS['grid'],
                showline=False,
                tickformat='$,.0f',
                tickfont=dict(size=10),
            ),
            hovermode='x unified',
            showlegend=False,
        )

        # Calculate stats
        start_value = values[0]
        end_value = values[-1]
        period_change = end_value - start_value
        period_return = ((end_value - start_value) / start_value) * 100 if start_value > 0 else 0

        # Format outputs
        total_text = f"${end_value:,.2f}"

        if period_change >= 0:
            change_text = f"+${period_change:,.2f}"
            change_style = {"color": COLORS['positive']}
            return_text = f"+{period_return:.2f}%"
            return_style = {"color": COLORS['positive']}
        else:
            change_text = f"-${abs(period_change):,.2f}"
            change_style = {"color": COLORS['negative']}
            return_text = f"{period_return:.2f}%"
            return_style = {"color": COLORS['negative']}

        return fig, total_text, change_text, change_style, return_text, return_style

    @app.callback(
        Output('allocation-chart', 'figure'),
        [
            Input('allocation-view-toggle', 'value'),
            Input('holdings-store', 'data'),
            Input('portfolio-store', 'data'),
        ],
        prevent_initial_call=False
    )
    def update_allocation_chart(view_type, holdings_data, portfolio_data):
        """Update allocation pie chart."""
        # Prepare data
        if not holdings_data and not portfolio_data:
            # Empty state
            fig = go.Figure(go.Pie(
                labels=['Cash'],
                values=[100000],
                hole=0.6,
                marker=dict(colors=[SECTOR_COLORS['Cash']]),
                textinfo='none',
                hovertemplate='%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>'
            ))
        else:
            cash = portfolio_data.get('current_cash', 0) if portfolio_data else 0
            holdings = holdings_data or []

            if view_type == 'sector':
                # Group by sector
                sector_values = {'Cash': cash}
                for h in holdings:
                    sector = h.get('sector', 'Unknown')
                    value = h.get('market_value', 0)
                    sector_values[sector] = sector_values.get(sector, 0) + value

                labels = list(sector_values.keys())
                values = list(sector_values.values())
                colors = [SECTOR_COLORS.get(s, '#868e96') for s in labels]

            else:
                # By stock
                labels = ['Cash'] + [h.get('symbol', '') for h in holdings]
                values = [cash] + [h.get('market_value', 0) for h in holdings]
                colors = [SECTOR_COLORS['Cash']] + [
                    SECTOR_COLORS.get(h.get('sector', 'Unknown'), '#868e96')
                    for h in holdings
                ]

            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors),
                textinfo='none',
                hovertemplate='%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>'
            ))

        # Update layout
        fig.update_layout(
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background'],
            font=dict(color=COLORS['text']),
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.2,
                xanchor='center',
                x=0.5,
                font=dict(size=10)
            ),
        )

        # Add center annotation
        total_value = 0
        if portfolio_data:
            total_value = portfolio_data.get('total_value', 0)

        fig.add_annotation(
            text=f"${total_value:,.0f}",
            x=0.5,
            y=0.5,
            font=dict(size=16, color='white'),
            showarrow=False
        )

        return fig
