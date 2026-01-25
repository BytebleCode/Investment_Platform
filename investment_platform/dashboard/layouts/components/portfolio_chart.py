"""
Portfolio Chart Component

Interactive line chart showing portfolio value over time.
"""
from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_portfolio_chart():
    """Create the portfolio performance chart component."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23", "height": "100%"},
        children=[
            # Header with title and time range buttons
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Portfolio Performance", order=4, c="white"),

                    # Time range selector
                    dmc.SegmentedControl(
                        id="chart-time-range",
                        value="1M",
                        data=[
                            {"value": "1W", "label": "1W"},
                            {"value": "1M", "label": "1M"},
                            {"value": "3M", "label": "3M"},
                            {"value": "6M", "label": "6M"},
                            {"value": "1Y", "label": "1Y"},
                        ],
                        size="sm",
                        color="blue"
                    ),
                ]
            ),

            # Chart
            dcc.Graph(
                id="portfolio-chart",
                config={
                    "displayModeBar": False,
                    "responsive": True
                },
                style={"height": "300px"}
            ),

            # Summary stats below chart
            dmc.Group(
                justify="space-around",
                mt="md",
                children=[
                    dmc.Stack(
                        gap=0,
                        align="center",
                        children=[
                            dmc.Text("Total Value", size="xs", c="dimmed"),
                            dmc.Text(
                                id="chart-total-value",
                                size="lg",
                                fw=600,
                                c="white",
                                children="$100,000.00"
                            ),
                        ]
                    ),
                    dmc.Stack(
                        gap=0,
                        align="center",
                        children=[
                            dmc.Text("Period Change", size="xs", c="dimmed"),
                            dmc.Text(
                                id="chart-period-change",
                                size="lg",
                                fw=600,
                                children="+$0.00"
                            ),
                        ]
                    ),
                    dmc.Stack(
                        gap=0,
                        align="center",
                        children=[
                            dmc.Text("Period Return", size="xs", c="dimmed"),
                            dmc.Text(
                                id="chart-period-return",
                                size="lg",
                                fw=600,
                                children="+0.00%"
                            ),
                        ]
                    ),
                ]
            )
        ]
    )
