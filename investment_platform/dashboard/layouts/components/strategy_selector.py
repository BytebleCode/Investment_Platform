"""
Strategy Selector Component

Displays the 5 macro investment strategies as selectable cards.
"""
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


# Macro Strategy configurations
STRATEGIES = {
    'monetary_policy': {
        'name': 'Monetary Policy',
        'description': 'Rate-sensitive: banks, utilities, treasury',
        'risk': 3,
        'return_range': '5-18%',
        'icon': 'mdi:bank',
        'color': 'blue'
    },
    'inflation_hedge': {
        'name': 'Inflation Hedge',
        'description': 'Commodities, energy, materials',
        'risk': 4,
        'return_range': '8-25%',
        'icon': 'mdi:fire',
        'color': 'orange'
    },
    'growth_expansion': {
        'name': 'Growth Expansion',
        'description': 'Tech, industrials, high-beta',
        'risk': 5,
        'return_range': '12-35%',
        'icon': 'mdi:rocket-launch',
        'color': 'green'
    },
    'defensive_quality': {
        'name': 'Defensive Quality',
        'description': 'Utilities, staples, healthcare',
        'risk': 1,
        'return_range': '2-8%',
        'icon': 'mdi:shield-check',
        'color': 'violet'
    },
    'liquidity_cycle': {
        'name': 'Liquidity Cycle',
        'description': 'Credit conditions, financials',
        'risk': 4,
        'return_range': '6-22%',
        'icon': 'mdi:chart-line',
        'color': 'red'
    }
}

# Strategy order for display
STRATEGY_ORDER = [
    'monetary_policy',
    'inflation_hedge',
    'growth_expansion',
    'defensive_quality',
    'liquidity_cycle'
]


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
                                        c="white",
                                        size="sm"
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
                        size="xs",
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

                    # Customize button
                    dmc.Group(
                        justify="flex-end",
                        mt="xs",
                        children=[
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
    """Create the strategy selector component with all 5 macro strategy cards."""
    return dmc.Paper(
        p="md",
        radius="md",
        style={"backgroundColor": "#1e1f23"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="md",
                children=[
                    dmc.Title("Macro Strategy", order=4, c="white"),
                    dmc.Text(
                        id="current-strategy-text",
                        size="sm",
                        c="dimmed",
                        children="Current: Monetary Policy"
                    ),
                ]
            ),

            # Strategy cards grid
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "lg": 5},
                spacing="md",
                children=[
                    create_strategy_card(strategy_id, STRATEGIES[strategy_id])
                    for strategy_id in STRATEGY_ORDER
                ]
            ),

            # Hidden input to store selected strategy
            dmc.TextInput(
                id="selected-strategy-input",
                value="monetary_policy",
                style={"display": "none"}
            ),
        ]
    )
