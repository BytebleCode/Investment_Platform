"""
Allocation Pie Chart Component

Shows portfolio allocation by stock or sector.
"""
from dash import html, dcc
import dash_mantine_components as dmc


def create_allocation_pie():
    """Create the allocation pie chart component."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23", "height": "100%"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Allocation", order=4, c="white"),

                    # Toggle between stock and sector view
                    dmc.SegmentedControl(
                        id="allocation-view-toggle",
                        value="stock",
                        data=[
                            {"value": "stock", "label": "By Stock"},
                            {"value": "sector", "label": "By Sector"},
                        ],
                        size="xs",
                        color="blue"
                    ),
                ]
            ),

            # Pie chart
            dcc.Graph(
                id="allocation-chart",
                config={
                    "displayModeBar": False,
                    "responsive": True
                },
                style={"height": "280px"}
            ),

            # Investment ratio indicator
            dmc.Stack(
                gap="xs",
                mt="md",
                children=[
                    dmc.Group(
                        justify="space-between",
                        children=[
                            dmc.Text("Investment Ratio", size="sm", c="dimmed"),
                            dmc.Text(
                                id="investment-ratio-text",
                                size="sm",
                                fw=600,
                                c="white",
                                children="0%"
                            ),
                        ]
                    ),
                    dmc.Progress(
                        id="investment-ratio-bar",
                        value=0,
                        color="blue",
                        size="lg",
                        radius="md"
                    ),
                    dmc.Group(
                        justify="space-between",
                        children=[
                            dmc.Text("Cash", size="xs", c="dimmed"),
                            dmc.Text("Invested", size="xs", c="dimmed"),
                        ]
                    ),
                ]
            )
        ]
    )
