"""
Strategy Selector Component

Displays the 5 investment strategies as selectable cards.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


# Strategy configurations
STRATEGIES = {
    'conservative': {
        'name': 'Conservative',
        'description': 'Low-risk, stable returns',
        'risk': 1,
        'return_range': '2-6%',
        'icon': 'mdi:shield-check',
        'color': 'green'
    },
    'growth': {
        'name': 'Growth',
        'description': 'High-growth technology focus',
        'risk': 4,
        'return_range': '10-25%',
        'icon': 'mdi:rocket-launch',
        'color': 'blue'
    },
    'value': {
        'name': 'Value',
        'description': 'Undervalued dividend stocks',
        'risk': 2,
        'return_range': '6-12%',
        'icon': 'mdi:diamond-stone',
        'color': 'violet'
    },
    'balanced': {
        'name': 'Balanced',
        'description': 'Mix of growth and stability',
        'risk': 3,
        'return_range': '5-12%',
        'icon': 'mdi:scale-balance',
        'color': 'orange'
    },
    'aggressive': {
        'name': 'Aggressive',
        'description': 'High-risk speculation',
        'risk': 5,
        'return_range': '-20-50%',
        'icon': 'mdi:fire',
        'color': 'red'
    }
}


def create_risk_indicator(risk_level):
    """Create a visual risk indicator (filled/empty circles)."""
    indicators = []
    for i in range(5):
        if i < risk_level:
            indicators.append(
                dmc.ThemeIcon(
                    DashIconify(icon="mdi:circle", width=8),
                    size="xs",
                    radius="xl",
                    color="red" if risk_level >= 4 else "orange" if risk_level >= 3 else "green",
                    variant="filled"
                )
            )
        else:
            indicators.append(
                dmc.ThemeIcon(
                    DashIconify(icon="mdi:circle-outline", width=8),
                    size="xs",
                    radius="xl",
                    color="gray",
                    variant="subtle"
                )
            )
    return dmc.Group(gap=2, children=indicators)


def create_strategy_card(strategy_id, strategy_info):
    """Create a single strategy card."""
    return dmc.Card(
        id={"type": "strategy-card", "index": strategy_id},
        p="md",
        radius="md",
        withBorder=True,
        style={
            "backgroundColor": "#25262b",
            "cursor": "pointer",
            "transition": "all 0.2s ease",
            "borderColor": "#373a40"
        },
        children=[
            dmc.Stack(
                gap="sm",
                children=[
                    # Icon and name
                    dmc.Group(
                        justify="space-between",
                        children=[
                            dmc.Group(
                                gap="sm",
                                children=[
                                    dmc.ThemeIcon(
                                        DashIconify(icon=strategy_info['icon'], width=20),
                                        size="lg",
                                        radius="md",
                                        color=strategy_info['color'],
                                        variant="light"
                                    ),
                                    dmc.Text(
                                        strategy_info['name'],
                                        fw=600,
                                        c="white"
                                    ),
                                ]
                            ),
                            # Active badge (shown via callback)
                            dmc.Badge(
                                id={"type": "strategy-active-badge", "index": strategy_id},
                                children="Active",
                                color="green",
                                variant="filled",
                                style={"display": "none"}
                            ),
                        ]
                    ),

                    # Description
                    dmc.Text(
                        strategy_info['description'],
                        size="sm",
                        c="dimmed"
                    ),

                    # Risk and return
                    dmc.Group(
                        justify="space-between",
                        children=[
                            dmc.Stack(
                                gap=2,
                                children=[
                                    dmc.Text("Risk", size="xs", c="dimmed"),
                                    create_risk_indicator(strategy_info['risk']),
                                ]
                            ),
                            dmc.Stack(
                                gap=2,
                                align="flex-end",
                                children=[
                                    dmc.Text("Return", size="xs", c="dimmed"),
                                    dmc.Text(
                                        strategy_info['return_range'],
                                        size="sm",
                                        fw=500,
                                        c="white"
                                    ),
                                ]
                            ),
                        ]
                    ),

                    # Confidence level and customize button
                    dmc.Group(
                        justify="space-between",
                        mt="xs",
                        children=[
                            dmc.Stack(
                                gap=2,
                                children=[
                                    dmc.Text("Confidence", size="xs", c="dimmed"),
                                    dmc.Text(
                                        id={"type": "strategy-confidence", "index": strategy_id},
                                        size="sm",
                                        c="white",
                                        children="50%"
                                    ),
                                ]
                            ),
                            dmc.Button(
                                "Customize",
                                id={"type": "strategy-customize-btn", "index": strategy_id},
                                size="xs",
                                variant="subtle",
                                color="gray",
                                leftSection=DashIconify(icon="mdi:cog", width=14)
                            ),
                        ]
                    ),
                ]
            )
        ]
    )


def create_strategy_selector():
    """Create the strategy selector component with all 5 strategy cards."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Investment Strategy", order=4, c="white"),
                    dmc.Text(
                        id="current-strategy-text",
                        size="sm",
                        c="dimmed",
                        children="Current: Balanced"
                    ),
                ]
            ),

            # Strategy cards grid
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "lg": 5},
                spacing="md",
                children=[
                    create_strategy_card(strategy_id, strategy_info)
                    for strategy_id, strategy_info in STRATEGIES.items()
                ]
            ),

            # Hidden input to store selected strategy
            dmc.TextInput(
                id="selected-strategy-input",
                value="balanced",
                style={"display": "none"}
            ),
        ]
    )
