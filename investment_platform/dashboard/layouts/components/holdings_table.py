"""
Holdings Table Component

Interactive table displaying current stock positions.
"""
from dash import html, dash_table
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_holdings_table():
    """Create the holdings table component."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Holdings", order=4, c="white"),
                    dmc.Badge(
                        id="holdings-count-badge",
                        children="0 positions",
                        color="blue",
                        variant="light"
                    ),
                ]
            ),

            # Data table
            dash_table.DataTable(
                id="holdings-table",
                columns=[
                    {"name": "Symbol", "id": "symbol", "type": "text"},
                    {"name": "Name", "id": "name", "type": "text"},
                    {"name": "Sector", "id": "sector", "type": "text"},
                    {"name": "Quantity", "id": "quantity", "type": "numeric", "format": {"specifier": ",.0f"}},
                    {"name": "Avg Cost", "id": "avg_cost", "type": "numeric", "format": {"specifier": "$,.2f"}},
                    {"name": "Current", "id": "current_price", "type": "numeric", "format": {"specifier": "$,.2f"}},
                    {"name": "Value", "id": "market_value", "type": "numeric", "format": {"specifier": "$,.2f"}},
                    {"name": "Gain/Loss", "id": "unrealized_gain", "type": "numeric", "format": {"specifier": "$,.2f"}},
                    {"name": "Gain %", "id": "unrealized_gain_pct", "type": "numeric", "format": {"specifier": "+.2f%"}},
                ],
                data=[],
                sort_action="native",
                sort_mode="single",
                page_size=10,
                style_table={
                    "overflowX": "auto",
                    "backgroundColor": "#25262b"
                },
                style_header={
                    "backgroundColor": "#2c2e33",
                    "color": "#909296",
                    "fontWeight": "600",
                    "textAlign": "left",
                    "padding": "12px",
                    "borderBottom": "1px solid #373a40"
                },
                style_cell={
                    "backgroundColor": "#25262b",
                    "color": "white",
                    "textAlign": "left",
                    "padding": "12px",
                    "borderBottom": "1px solid #373a40",
                    "fontFamily": "Inter, sans-serif"
                },
                style_data_conditional=[
                    # Green for positive gains
                    {
                        "if": {
                            "filter_query": "{unrealized_gain} > 0",
                            "column_id": ["unrealized_gain", "unrealized_gain_pct"]
                        },
                        "color": "#40c057"
                    },
                    # Red for negative gains
                    {
                        "if": {
                            "filter_query": "{unrealized_gain} < 0",
                            "column_id": ["unrealized_gain", "unrealized_gain_pct"]
                        },
                        "color": "#fa5252"
                    },
                    # Highlight row on hover
                    {
                        "if": {"state": "active"},
                        "backgroundColor": "#2c2e33"
                    }
                ],
                style_as_list_view=True,
            ),

            # Empty state
            html.Div(
                id="holdings-empty-state",
                style={"display": "none"},
                children=[
                    dmc.Stack(
                        align="center",
                        py="xl",
                        children=[
                            DashIconify(
                                icon="mdi:folder-open-outline",
                                width=48,
                                color="#909296"
                            ),
                            dmc.Text(
                                "No holdings yet",
                                c="dimmed",
                                size="lg"
                            ),
                            dmc.Text(
                                "Execute a trade to get started",
                                c="dimmed",
                                size="sm"
                            ),
                        ]
                    )
                ]
            )
        ]
    )
