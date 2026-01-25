"""
Portfolio Summary Component

Displays key portfolio metrics in stat cards.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_stat_card(title, value_id, icon, color="blue"):
    """Create a single stat card."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#25262b"},
        children=[
            dmc.Group(
                justify="space-between",
                children=[
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Text(title, size="sm", c="dimmed"),
                            dmc.Text(
                                id=value_id,
                                size="xl",
                                fw=700,
                                children="$0.00"
                            ),
                            dmc.Text(
                                id=f"{value_id}-change",
                                size="sm",
                                c="dimmed",
                                children=""
                            ),
                        ]
                    ),
                    dmc.ThemeIcon(
                        DashIconify(icon=icon, width=24),
                        size="xl",
                        radius="md",
                        color=color,
                        variant="light"
                    ),
                ]
            )
        ]
    )


def create_portfolio_summary():
    """Create the portfolio summary component with 4 stat cards."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23", "height": "100%"},
        children=[
            dmc.Title("Portfolio Summary", order=4, mb="md", c="white"),

            dmc.Stack(
                gap="md",
                children=[
                    # Available Cash
                    create_stat_card(
                        "Available Cash",
                        "stat-cash",
                        "mdi:cash",
                        "green"
                    ),

                    # Invested Value
                    create_stat_card(
                        "Invested Value",
                        "stat-invested",
                        "mdi:chart-areaspline",
                        "blue"
                    ),

                    # Total Return
                    create_stat_card(
                        "Total Return",
                        "stat-return",
                        "mdi:trending-up",
                        "cyan"
                    ),

                    # Estimated Tax
                    create_stat_card(
                        "Estimated Tax (37%)",
                        "stat-tax",
                        "mdi:receipt-text",
                        "orange"
                    ),
                ]
            )
        ]
    )
