"""
Strategy Customization Modal

Modal dialog for customizing strategy parameters.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_strategy_modal():
    """Create the strategy customization modal."""
    return dmc.Modal(
        id="strategy-modal",
        title="Customize Strategy",
        size="lg",
        centered=True,
        overlayProps={"blur": 3},
        children=[
            dmc.Stack(
                gap="md",
                children=[
                    # Strategy name (will be set dynamically)
                    dmc.Title(
                        id="modal-strategy-name",
                        order=4,
                        c="white",
                        children="Strategy Name"
                    ),

                    dmc.Divider(),

                    # Confidence Level
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                children=[
                                    dmc.Text("Confidence Level", fw=500),
                                    dmc.Text(
                                        id="confidence-value-text",
                                        c="blue",
                                        fw=600,
                                        children="50%"
                                    ),
                                ]
                            ),
                            dmc.Slider(
                                id="confidence-slider",
                                value=50,
                                min=10,
                                max=100,
                                step=5,
                                marks=[
                                    {"value": 10, "label": "10%"},
                                    {"value": 50, "label": "50%"},
                                    {"value": 100, "label": "100%"},
                                ],
                                color="blue"
                            ),
                            dmc.Text(
                                "Higher confidence means larger position sizes",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),

                    # Trade Frequency
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Text("Trade Frequency", fw=500),
                            dmc.SegmentedControl(
                                id="frequency-selector",
                                value="medium",
                                data=[
                                    {"value": "low", "label": "Low"},
                                    {"value": "medium", "label": "Medium"},
                                    {"value": "high", "label": "High"},
                                ],
                                fullWidth=True,
                                color="blue"
                            ),
                            dmc.Text(
                                "How often the auto-trader executes trades",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),

                    # Max Position Size
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                children=[
                                    dmc.Text("Max Position Size", fw=500),
                                    dmc.Text(
                                        id="position-size-value-text",
                                        c="blue",
                                        fw=600,
                                        children="15%"
                                    ),
                                ]
                            ),
                            dmc.Slider(
                                id="position-size-slider",
                                value=15,
                                min=5,
                                max=50,
                                step=5,
                                marks=[
                                    {"value": 5, "label": "5%"},
                                    {"value": 25, "label": "25%"},
                                    {"value": 50, "label": "50%"},
                                ],
                                color="blue"
                            ),
                            dmc.Text(
                                "Maximum allocation to a single stock",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),

                    # Stop Loss
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                children=[
                                    dmc.Text("Stop Loss", fw=500),
                                    dmc.Text(
                                        id="stop-loss-value-text",
                                        c="red",
                                        fw=600,
                                        children="10%"
                                    ),
                                ]
                            ),
                            dmc.Slider(
                                id="stop-loss-slider",
                                value=10,
                                min=5,
                                max=30,
                                step=1,
                                marks=[
                                    {"value": 5, "label": "5%"},
                                    {"value": 15, "label": "15%"},
                                    {"value": 30, "label": "30%"},
                                ],
                                color="red"
                            ),
                            dmc.Text(
                                "Sell if position drops by this percentage",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),

                    # Take Profit
                    dmc.Stack(
                        gap="xs",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                children=[
                                    dmc.Text("Take Profit", fw=500),
                                    dmc.Text(
                                        id="take-profit-value-text",
                                        c="green",
                                        fw=600,
                                        children="20%"
                                    ),
                                ]
                            ),
                            dmc.Slider(
                                id="take-profit-slider",
                                value=20,
                                min=10,
                                max=100,
                                step=5,
                                marks=[
                                    {"value": 10, "label": "10%"},
                                    {"value": 50, "label": "50%"},
                                    {"value": 100, "label": "100%"},
                                ],
                                color="green"
                            ),
                            dmc.Text(
                                "Sell if position gains this percentage",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    ),

                    dmc.Divider(),

                    # Toggle switches
                    dmc.Group(
                        grow=True,
                        children=[
                            dmc.Switch(
                                id="auto-rebalance-switch",
                                label="Auto Rebalance",
                                checked=True,
                                description="Automatically rebalance portfolio",
                                color="blue"
                            ),
                            dmc.Switch(
                                id="reinvest-dividends-switch",
                                label="Reinvest Dividends",
                                checked=True,
                                description="Automatically reinvest dividends",
                                color="blue"
                            ),
                        ]
                    ),

                    dmc.Divider(),

                    # Action buttons
                    dmc.Group(
                        justify="flex-end",
                        children=[
                            dmc.Button(
                                "Cancel",
                                id="modal-cancel-btn",
                                variant="subtle",
                                color="gray"
                            ),
                            dmc.Button(
                                "Save Changes",
                                id="modal-save-btn",
                                variant="filled",
                                color="blue",
                                leftSection=DashIconify(icon="mdi:content-save")
                            ),
                        ]
                    ),
                ]
            ),

            # Hidden input to store which strategy is being edited
            dmc.TextInput(
                id="modal-strategy-id",
                value="",
                style={"display": "none"}
            ),
        ]
    )
