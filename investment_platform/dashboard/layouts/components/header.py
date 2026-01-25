"""
Header Component

Navigation bar and application title.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_header():
    """Create the header/navbar component."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#25262b"},
        children=[
            dmc.Group(
                justify="space-between",
                children=[
                    # Logo and title
                    dmc.Group(
                        children=[
                            DashIconify(
                                icon="mdi:chart-line",
                                width=32,
                                color="#228be6"
                            ),
                            dmc.Title(
                                "Investment Platform",
                                order=2,
                                style={"color": "white", "margin": 0}
                            ),
                        ]
                    ),

                    # Controls
                    dmc.Group(
                        children=[
                            # Auto-trade toggle
                            dmc.Switch(
                                id="auto-trade-switch",
                                label="Auto Trading",
                                checked=False,
                                color="green",
                                size="md"
                            ),

                            # Manual trade button
                            dmc.Button(
                                "Execute Trade",
                                id="manual-trade-btn",
                                leftSection=DashIconify(icon="mdi:swap-horizontal"),
                                variant="filled",
                                color="blue"
                            ),

                            # Refresh button
                            dmc.ActionIcon(
                                DashIconify(icon="mdi:refresh", width=20),
                                id="refresh-data-btn",
                                variant="subtle",
                                color="gray",
                                size="lg"
                            ),

                            # Reset portfolio button
                            dmc.Button(
                                "Reset",
                                id="reset-portfolio-btn",
                                leftSection=DashIconify(icon="mdi:restore"),
                                variant="outline",
                                color="red"
                            ),
                        ]
                    ),
                ]
            ),

            # Market status indicator
            dmc.Group(
                mt="xs",
                children=[
                    dmc.Badge(
                        id="market-status-badge",
                        children="Market Closed",
                        color="gray",
                        variant="dot"
                    ),
                    dmc.Text(
                        id="last-update-text",
                        size="xs",
                        c="dimmed",
                        children="Last updated: --"
                    ),
                ]
            )
        ]
    )
