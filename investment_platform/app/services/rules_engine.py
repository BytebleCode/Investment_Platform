"""
Rules Engine Service

Evaluates and executes relational trading rules (hedge, pair, rebalance, correlation).
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from app.models.strategy_rules import StrategyRule
from app.data.symbol_universe import get_symbols_by_path

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Engine for evaluating and executing strategy rules.

    Rule Types:
        - hedge: When position A changes, adjust position B inversely
        - pair: Long/short spread trading between two components
        - rebalance: Threshold-based rebalancing rules
        - correlation: Reduce exposure when correlation spikes
    """

    def __init__(self, strategy_id: str):
        """
        Initialize rules engine for a strategy.

        Args:
            strategy_id: Strategy identifier
        """
        self.strategy_id = strategy_id

    def get_rules(self, include_inactive: bool = False) -> List[dict]:
        """
        Get all rules for this strategy.

        Args:
            include_inactive: Include deactivated rules

        Returns:
            List of rule dictionaries
        """
        rules = StrategyRule.get_rules(self.strategy_id, include_inactive)
        return [r.to_dict() if hasattr(r, 'to_dict') else r for r in rules]

    def get_rule(self, rule_id: int) -> Optional[dict]:
        """
        Get a specific rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule dictionary or None
        """
        rule = StrategyRule.get_rule(rule_id)
        if rule:
            return rule.to_dict() if hasattr(rule, 'to_dict') else rule
        return None

    def create_rule(self, rule_name: str, rule_type: str, config: dict,
                    priority: int = 0, is_active: bool = True) -> dict:
        """
        Create a new rule.

        Args:
            rule_name: Human-readable name
            rule_type: Type of rule (hedge, pair, rebalance, correlation)
            config: Rule configuration
            priority: Execution priority
            is_active: Whether rule is active

        Returns:
            Created rule dictionary
        """
        rule = StrategyRule.create(
            strategy_id=self.strategy_id,
            rule_name=rule_name,
            rule_type=rule_type,
            config=config,
            priority=priority,
            is_active=is_active
        )
        return rule.to_dict() if hasattr(rule, 'to_dict') else rule

    def create_from_template(self, rule_type: str, **overrides) -> dict:
        """
        Create a rule from a template.

        Args:
            rule_type: Type of rule to create
            **overrides: Config overrides

        Returns:
            Created rule dictionary
        """
        template = StrategyRule.get_template(rule_type)
        if not template:
            raise ValueError(f"Unknown rule type: {rule_type}")

        # Apply overrides
        config = template.copy()
        config.update(overrides)

        rule_name = f"{rule_type.title()} Rule"
        return self.create_rule(rule_name, rule_type, config)

    def update_rule(self, rule_id: int, **kwargs) -> Optional[dict]:
        """
        Update an existing rule.

        Args:
            rule_id: Rule ID
            **kwargs: Fields to update

        Returns:
            Updated rule dictionary or None
        """
        rule = StrategyRule.update(rule_id, **kwargs)
        if rule:
            return rule.to_dict() if hasattr(rule, 'to_dict') else rule
        return None

    def delete_rule(self, rule_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a rule.

        Args:
            rule_id: Rule ID
            hard_delete: If True, permanently delete

        Returns:
            True if deleted
        """
        return StrategyRule.delete(rule_id, hard_delete)

    def evaluate_rules(self, context: dict) -> List[dict]:
        """
        Evaluate all active rules against current context.

        Args:
            context: Current trading context with:
                - positions: dict of symbol -> position data
                - prices: dict of symbol -> current price
                - portfolio_value: current portfolio value
                - cash: available cash

        Returns:
            List of triggered rules with actions
        """
        rules = self.get_rules(include_inactive=False)
        triggered = []

        for rule in rules:
            try:
                result = self._evaluate_rule(rule, context)
                if result:
                    triggered.append({
                        'rule': rule,
                        'action': result
                    })
            except Exception as e:
                logger.error(f"Error evaluating rule {rule['id']}: {e}")

        return triggered

    def execute_rule(self, rule: dict, context: dict) -> Optional[dict]:
        """
        Execute a triggered rule and return trade signals.

        Args:
            rule: Rule dictionary
            context: Current trading context

        Returns:
            Trade signals dictionary or None
        """
        rule_type = rule['rule_type']
        config = rule['config']

        handler = getattr(self, f'_execute_{rule_type}', None)
        if handler:
            return handler(config, context)

        logger.warning(f"No handler for rule type: {rule_type}")
        return None

    def _evaluate_rule(self, rule: dict, context: dict) -> Optional[dict]:
        """
        Evaluate a single rule.

        Returns:
            Action dict if rule triggers, None otherwise
        """
        rule_type = rule['rule_type']
        config = rule['config']

        if rule_type == 'hedge':
            return self._evaluate_hedge(config, context)
        elif rule_type == 'pair':
            return self._evaluate_pair(config, context)
        elif rule_type == 'rebalance':
            return self._evaluate_rebalance(config, context)
        elif rule_type == 'correlation':
            return self._evaluate_correlation(config, context)

        return None

    def _evaluate_hedge(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate hedge rule.

        Triggers when primary position changes and hedge needs adjustment.
        """
        primary = config.get('primary')
        hedge = config.get('hedge')
        ratio = config.get('ratio', -0.3)

        positions = context.get('positions', {})
        prices = context.get('prices', {})

        primary_pos = positions.get(primary, {})
        hedge_pos = positions.get(hedge, {})

        primary_value = primary_pos.get('value', 0)
        hedge_value = hedge_pos.get('value', 0)

        target_hedge_value = primary_value * ratio
        hedge_diff = target_hedge_value - hedge_value

        # Only trigger if difference is significant (>5% of portfolio)
        portfolio_value = context.get('portfolio_value', 1)
        if abs(hedge_diff) / portfolio_value > 0.01:
            return {
                'type': 'hedge_adjustment',
                'symbol': hedge,
                'target_value': target_hedge_value,
                'current_value': hedge_value,
                'adjustment': hedge_diff
            }

        return None

    def _evaluate_pair(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate pair trade rule.

        Triggers when spread diverges from target.
        """
        long_path = config.get('long')
        short_path = config.get('short')
        spread_target = config.get('spread_target', 0.02)
        rebalance_threshold = config.get('rebalance_threshold', 0.05)

        positions = context.get('positions', {})
        prices = context.get('prices', {})

        # Get symbols for each side
        long_symbols = get_symbols_by_path(long_path) if '.' in long_path else [long_path]
        short_symbols = get_symbols_by_path(short_path) if '.' in short_path else [short_path]

        # Calculate current values
        long_value = sum(positions.get(s, {}).get('value', 0) for s in long_symbols)
        short_value = sum(positions.get(s, {}).get('value', 0) for s in short_symbols)

        # Calculate spread
        total = abs(long_value) + abs(short_value)
        if total == 0:
            return None

        current_spread = (long_value - abs(short_value)) / total
        spread_diff = abs(current_spread - spread_target)

        if spread_diff > rebalance_threshold:
            return {
                'type': 'pair_rebalance',
                'long': long_path,
                'short': short_path,
                'current_spread': current_spread,
                'target_spread': spread_target,
                'deviation': spread_diff
            }

        return None

    def _evaluate_rebalance(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate rebalance rule.

        Triggers when any component drifts beyond threshold.
        """
        components = config.get('components', [])
        threshold = config.get('threshold', 0.05)

        positions = context.get('positions', {})
        portfolio_value = context.get('portfolio_value', 1)

        # Calculate current weights
        current_weights = {}
        for component in components:
            if '.' in component:
                symbols = get_symbols_by_path(component)
            else:
                symbols = [component]

            total_value = sum(positions.get(s, {}).get('value', 0) for s in symbols)
            current_weights[component] = total_value / portfolio_value if portfolio_value > 0 else 0

        # Target is equal weight
        target_weight = 1.0 / len(components) if components else 0

        # Check for drift
        max_drift = 0
        drifted_components = []
        for component, weight in current_weights.items():
            drift = abs(weight - target_weight)
            if drift > max_drift:
                max_drift = drift
            if drift > threshold:
                drifted_components.append({
                    'component': component,
                    'current': weight,
                    'target': target_weight,
                    'drift': drift
                })

        if drifted_components:
            return {
                'type': 'threshold_rebalance',
                'components': drifted_components,
                'max_drift': max_drift,
                'threshold': threshold
            }

        return None

    def _evaluate_correlation(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate correlation rule.

        Triggers when correlation exceeds target.
        Note: Actual correlation calculation requires historical data.
        """
        components = config.get('components', [])
        target_correlation = config.get('target_correlation', 0.6)
        action = config.get('action', 'reduce_on_high_correlation')

        # This would need historical return data to calculate actual correlation
        # For now, we'll use a placeholder that checks context for correlation data
        correlations = context.get('correlations', {})

        # Check if any pair exceeds target
        high_corr_pairs = []
        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                pair_key = f"{comp1}:{comp2}"
                correlation = correlations.get(pair_key, 0)
                if correlation > target_correlation:
                    high_corr_pairs.append({
                        'pair': (comp1, comp2),
                        'correlation': correlation
                    })

        if high_corr_pairs:
            return {
                'type': 'correlation_adjustment',
                'action': action,
                'high_correlation_pairs': high_corr_pairs,
                'target_correlation': target_correlation
            }

        return None

    def _execute_hedge(self, config: dict, context: dict) -> dict:
        """Execute hedge rule - return trade signals."""
        primary = config.get('primary')
        hedge = config.get('hedge')
        ratio = config.get('ratio', -0.3)

        positions = context.get('positions', {})
        prices = context.get('prices', {})

        primary_value = positions.get(primary, {}).get('value', 0)
        hedge_value = positions.get(hedge, {}).get('value', 0)

        target_hedge_value = primary_value * ratio
        adjustment = target_hedge_value - hedge_value

        hedge_price = prices.get(hedge, 0)
        if hedge_price > 0:
            shares = int(adjustment / hedge_price)
            return {
                'trades': [{
                    'symbol': hedge,
                    'action': 'buy' if shares > 0 else 'sell',
                    'shares': abs(shares),
                    'reason': f'hedge_adjustment_for_{primary}'
                }]
            }

        return {'trades': []}

    def _execute_pair(self, config: dict, context: dict) -> dict:
        """Execute pair trade rule - return trade signals."""
        # Implementation would generate long/short orders
        return {'trades': [], 'note': 'pair_trade_execution'}

    def _execute_rebalance(self, config: dict, context: dict) -> dict:
        """Execute rebalance rule - return trade signals."""
        # Implementation would generate rebalance orders
        return {'trades': [], 'note': 'rebalance_execution'}

    def _execute_correlation(self, config: dict, context: dict) -> dict:
        """Execute correlation rule - return trade signals."""
        # Implementation would generate position reduction orders
        return {'trades': [], 'note': 'correlation_adjustment'}


def get_rule_templates() -> Dict[str, dict]:
    """
    Get all available rule templates.

    Returns:
        Dictionary of rule_type -> template config
    """
    return {
        'hedge': {
            'name': 'Hedge Position',
            'description': 'Automatically hedge a position with an inverse asset',
            'config': {
                'primary': 'NVDA',
                'hedge': 'GLD',
                'ratio': -0.3,
                'trigger': 'position_change'
            }
        },
        'pair': {
            'name': 'Pair Trade',
            'description': 'Long/short spread trading between two components',
            'config': {
                'long': 'technology.semiconductors',
                'short': 'utilities.electric',
                'spread_target': 0.02,
                'rebalance_threshold': 0.05
            }
        },
        'rebalance': {
            'name': 'Threshold Rebalance',
            'description': 'Rebalance when allocations drift beyond threshold',
            'config': {
                'components': ['financials', 'technology', 'healthcare'],
                'threshold': 0.05,
                'frequency': 'weekly'
            }
        },
        'correlation': {
            'name': 'Correlation Adjustment',
            'description': 'Reduce exposure when correlation spikes',
            'config': {
                'components': ['AAPL', 'MSFT', 'GOOGL'],
                'target_correlation': 0.6,
                'action': 'reduce_on_high_correlation',
                'lookback_days': 30
            }
        }
    }
