"""
Trade History Component

Displays recent trades with filtering options.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_trade_card(trade):
    """Create a single trade card (used by callback)."""
    is_buy = trade.get('type', '').lower() == 'buy'

    return dmc.Card(
        p="sm",
        radius="md",
        withBorder=True,
        style={"backgroundColor": "#25262b", "borderColor": "#373a40"},
        children=[
            dmc.Group(
                justify="space-between",
                children=[
                    dmc.Group(
                        gap="sm",
                        children=[
                            dmc.Badge(
                                trade.get('type', 'BUY').upper(),
                                color="green" if is_buy else "red",
                                variant="filled",
                                size="sm"
                            ),
                            dmc.Stack(
                                gap=0,
                                children=[
                                    dmc.Text(
                                        trade.get('symbol', ''),
                                        fw=600,
                                        c="white"
                                    ),
                                    dmc.Text(
                                        trade.get('stock_name', ''),
                                        size="xs",
                                        c="dimmed"
                                    ),
                                ]
                            ),
                        ]
                    ),
                    dmc.Stack(
                        gap=0,
                        align="flex-end",
                        children=[
                            dmc.Text(
                                f"${trade.get('total', 0):,.2f}",
                                fw=600,
                                c="white"
                            ),
                            dmc.Text(
                                f"{trade.get('quantity', 0)} @ ${trade.get('price', 0):.2f}",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),
                ]
            ),
            dmc.Group(
                justify="space-between",
                mt="xs",
                children=[
                    dmc.Text(
                        trade.get('timestamp', '')[:16].replace('T', ' ') if trade.get('timestamp') else '',
                        size="xs",
                        c="dimmed"
                    ),
                    dmc.Group(
                        gap="xs",
                        children=[
                            dmc.Badge(
                                trade.get('strategy', 'balanced').title(),
                                color="gray",
                                variant="light",
                                size="xs"
                            ),
                            dmc.Text(
                                f"Fee: ${trade.get('fees', 0):.2f}",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


def create_trade_history():
    """Create the trade history component."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Trade History", order=4, c="white"),

                    dmc.Group(
                        gap="sm",
                        children=[
                            # Filter tabs
                            dmc.SegmentedControl(
                                id="trade-filter",
                                value="all",
                                data=[
                                    {"value": "all", "label": "All"},
                                    {"value": "buy", "label": "Buy"},
                                    {"value": "sell", "label": "Sell"},
                                ],
                                size="xs",
                                color="blue"
                            ),
                            dmc.Badge(
                                id="trade-count-badge",
                                children="0 trades",
                                color="gray",
                                variant="light"
                            ),
                        ]
                    ),
                ]
            ),

            # Trade cards container
            dmc.ScrollArea(
                h=300,
                children=[
                    dmc.Stack(
                        id="trade-history-container",
                        gap="sm",
                        children=[
                            # Trade cards will be inserted here by callback
                        ]
                    ),

                    # Empty state
                    html.Div(
                        id="trades-empty-state",
                        children=[
                            dmc.Stack(
                                align="center",
                                py="xl",
                                children=[
                                    DashIconify(
                                        icon="mdi:history",
                                        width=48,
                                        color="#909296"
                                    ),
                                    dmc.Text(
                                        "No trades yet",
                                        c="dimmed",
                                        size="lg"
                                    ),
                                    dmc.Text(
                                        "Your trade history will appear here",
                                        c="dimmed",
                                        size="sm"
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
        ]
    )
