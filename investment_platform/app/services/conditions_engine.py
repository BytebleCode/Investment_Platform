"""
Conditions Engine Service

Evaluates and executes conditional triggers (price, macro, portfolio, time-based).
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from app.models.strategy_conditions import StrategyCondition
from app.services.macro_signals import get_macro_service

logger = logging.getLogger(__name__)


class ConditionsEngine:
    """
    Engine for evaluating and executing conditional triggers.

    Condition Types:
        - price: Price-based triggers (percent change, threshold)
        - macro: Macro indicator triggers (FRED signals)
        - portfolio: Portfolio metric triggers (drawdown, allocation drift)
        - time: Time-based triggers (scheduled rebalancing)

    Action Types:
        - reduce_position: Sell portion of specific holding
        - shift_allocation: Move weight between sectors
        - reduce_exposure: Increase cash position
        - rebalance: Return to target weights
    """

    def __init__(self, strategy_id: str):
        """
        Initialize conditions engine for a strategy.

        Args:
            strategy_id: Strategy identifier
        """
        self.strategy_id = strategy_id
        self.macro_service = get_macro_service()

    def get_conditions(self, include_inactive: bool = False) -> List[dict]:
        """
        Get all conditions for this strategy.

        Args:
            include_inactive: Include deactivated conditions

        Returns:
            List of condition dictionaries
        """
        conditions = StrategyCondition.get_conditions(self.strategy_id, include_inactive)
        return [c.to_dict() if hasattr(c, 'to_dict') else c for c in conditions]

    def get_condition(self, condition_id: int) -> Optional[dict]:
        """
        Get a specific condition by ID.

        Args:
            condition_id: Condition ID

        Returns:
            Condition dictionary or None
        """
        condition = StrategyCondition.get_condition(condition_id)
        if condition:
            return condition.to_dict() if hasattr(condition, 'to_dict') else condition
        return None

    def create_condition(self, condition_type: str, trigger_config: dict,
                        action_config: dict, condition_name: Optional[str] = None,
                        is_active: bool = True) -> dict:
        """
        Create a new condition.

        Args:
            condition_type: Type of condition (price, macro, portfolio, time)
            trigger_config: When to trigger
            action_config: What to do
            condition_name: Human-readable name
            is_active: Whether condition is active

        Returns:
            Created condition dictionary
        """
        condition = StrategyCondition.create(
            strategy_id=self.strategy_id,
            condition_type=condition_type,
            trigger_config=trigger_config,
            action_config=action_config,
            condition_name=condition_name,
            is_active=is_active
        )
        return condition.to_dict() if hasattr(condition, 'to_dict') else condition

    def create_from_template(self, template_name: str, is_active: bool = True) -> dict:
        """
        Create a condition from a preset template.

        Args:
            template_name: Name of the template
            is_active: Whether condition is active

        Returns:
            Created condition dictionary
        """
        condition = StrategyCondition.create_from_template(
            self.strategy_id,
            template_name,
            is_active
        )
        return condition.to_dict() if hasattr(condition, 'to_dict') else condition

    def update_condition(self, condition_id: int, **kwargs) -> Optional[dict]:
        """
        Update an existing condition.

        Args:
            condition_id: Condition ID
            **kwargs: Fields to update

        Returns:
            Updated condition dictionary or None
        """
        condition = StrategyCondition.update(condition_id, **kwargs)
        if condition:
            return condition.to_dict() if hasattr(condition, 'to_dict') else condition
        return None

    def delete_condition(self, condition_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a condition.

        Args:
            condition_id: Condition ID
            hard_delete: If True, permanently delete

        Returns:
            True if deleted
        """
        return StrategyCondition.delete(condition_id, hard_delete)

    def evaluate_conditions(self, context: dict) -> List[dict]:
        """
        Evaluate all active conditions against current context.

        Args:
            context: Current trading context with:
                - positions: dict of symbol -> position data
                - prices: dict of symbol -> current price
                - price_history: dict of symbol -> list of historical prices
                - portfolio_value: current portfolio value
                - portfolio_history: list of historical portfolio values
                - cash: available cash
                - current_time: datetime

        Returns:
            List of triggered conditions with actions
        """
        conditions = self.get_conditions(include_inactive=False)
        triggered = []

        for condition in conditions:
            try:
                result = self._evaluate_condition(condition, context)
                if result:
                    triggered.append({
                        'condition': condition,
                        'trigger_result': result
                    })
                    # Mark as triggered
                    StrategyCondition.mark_triggered(condition['id'])
            except Exception as e:
                logger.error(f"Error evaluating condition {condition['id']}: {e}")

        return triggered

    def execute_action(self, condition: dict, context: dict) -> Optional[dict]:
        """
        Execute the action for a triggered condition.

        Args:
            condition: Condition dictionary
            context: Current trading context

        Returns:
            Trade signals dictionary or None
        """
        action_config = condition['action_config']
        action_type = action_config.get('action')

        handler = getattr(self, f'_execute_{action_type}', None)
        if handler:
            return handler(action_config, context)

        logger.warning(f"No handler for action type: {action_type}")
        return None

    def _evaluate_condition(self, condition: dict, context: dict) -> Optional[dict]:
        """
        Evaluate a single condition.

        Returns:
            Trigger result dict if condition triggers, None otherwise
        """
        condition_type = condition['condition_type']
        trigger_config = condition['trigger_config']

        if condition_type == 'price':
            return self._evaluate_price_trigger(trigger_config, context)
        elif condition_type == 'macro':
            return self._evaluate_macro_trigger(trigger_config, context)
        elif condition_type == 'portfolio':
            return self._evaluate_portfolio_trigger(trigger_config, context)
        elif condition_type == 'time':
            return self._evaluate_time_trigger(trigger_config, context)

        return None

    def _evaluate_price_trigger(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate price-based trigger.

        Supports comparisons: percent_change, greater_than, less_than
        """
        symbol = config.get('symbol')
        comparison = config.get('comparison')
        threshold = config.get('threshold')
        lookback_days = config.get('lookback_days', 5)

        price_history = context.get('price_history', {}).get(symbol, [])
        current_price = context.get('prices', {}).get(symbol, 0)

        if not price_history or not current_price:
            return None

        if comparison == 'percent_change':
            if len(price_history) >= lookback_days:
                old_price = price_history[-lookback_days]
                pct_change = (current_price - old_price) / old_price
                if pct_change <= threshold:  # Usually negative threshold
                    return {
                        'triggered': True,
                        'symbol': symbol,
                        'percent_change': pct_change,
                        'threshold': threshold
                    }

        elif comparison == 'greater_than':
            if current_price > threshold:
                return {
                    'triggered': True,
                    'symbol': symbol,
                    'current_price': current_price,
                    'threshold': threshold
                }

        elif comparison == 'less_than':
            if current_price < threshold:
                return {
                    'triggered': True,
                    'symbol': symbol,
                    'current_price': current_price,
                    'threshold': threshold
                }

        return None

    def _evaluate_macro_trigger(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate macro indicator trigger.

        Uses FRED signals for economic indicators.
        """
        signal = config.get('signal')
        comparison = config.get('comparison')
        threshold = config.get('threshold')

        # Get macro signal value
        if self.macro_service.is_enabled():
            signal_value = self.macro_service.get_signal(signal)
            if signal_value is None:
                return None
        else:
            # Check context for macro data
            macro_signals = context.get('macro_signals', {})
            signal_value = macro_signals.get(signal)
            if signal_value is None:
                return None

        triggered = False
        if comparison == 'less_than':
            triggered = signal_value < threshold
        elif comparison == 'greater_than':
            triggered = signal_value > threshold
        elif comparison == 'equals':
            triggered = abs(signal_value - threshold) < 0.001

        if triggered:
            return {
                'triggered': True,
                'signal': signal,
                'value': signal_value,
                'comparison': comparison,
                'threshold': threshold
            }

        return None

    def _evaluate_portfolio_trigger(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate portfolio metric trigger.

        Supports metrics: drawdown, daily_loss, allocation_drift
        """
        metric = config.get('metric')
        comparison = config.get('comparison')
        threshold = config.get('threshold')
        lookback_days = config.get('lookback_days', 30)

        portfolio_value = context.get('portfolio_value', 0)
        portfolio_history = context.get('portfolio_history', [])

        metric_value = None

        if metric == 'drawdown':
            if portfolio_history:
                peak = max(portfolio_history[-lookback_days:]) if len(portfolio_history) >= lookback_days else max(portfolio_history)
                if peak > 0:
                    metric_value = (peak - portfolio_value) / peak

        elif metric == 'daily_loss':
            if len(portfolio_history) >= 2:
                yesterday = portfolio_history[-1]
                if yesterday > 0:
                    metric_value = (yesterday - portfolio_value) / yesterday

        elif metric == 'allocation_drift':
            # Would need target allocations to compute drift
            metric_value = context.get('allocation_drift', 0)

        if metric_value is None:
            return None

        triggered = False
        if comparison == 'greater_than':
            triggered = metric_value > threshold
        elif comparison == 'less_than':
            triggered = metric_value < threshold

        if triggered:
            return {
                'triggered': True,
                'metric': metric,
                'value': metric_value,
                'comparison': comparison,
                'threshold': threshold
            }

        return None

    def _evaluate_time_trigger(self, config: dict, context: dict) -> Optional[dict]:
        """
        Evaluate time-based trigger.

        Supports schedules: daily, weekly, monthly
        """
        schedule = config.get('schedule')
        day_of_week = config.get('day_of_week', 'monday').lower()
        day_of_month = config.get('day_of_month', 1)

        current_time = context.get('current_time', datetime.now(timezone.utc))
        last_triggered = context.get('last_trigger_times', {}).get(self.strategy_id)

        should_trigger = False

        if schedule == 'daily':
            # Trigger once per day
            if last_triggered:
                should_trigger = (current_time.date() > last_triggered.date())
            else:
                should_trigger = True

        elif schedule == 'weekly':
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            target_weekday = weekdays.index(day_of_week) if day_of_week in weekdays else 0
            current_weekday = current_time.weekday()

            if current_weekday == target_weekday:
                if last_triggered:
                    should_trigger = (current_time.date() > last_triggered.date())
                else:
                    should_trigger = True

        elif schedule == 'monthly':
            if current_time.day == day_of_month:
                if last_triggered:
                    should_trigger = (current_time.month != last_triggered.month or
                                    current_time.year != last_triggered.year)
                else:
                    should_trigger = True

        if should_trigger:
            return {
                'triggered': True,
                'schedule': schedule,
                'current_time': current_time.isoformat()
            }

        return None

    def _execute_reduce_position(self, config: dict, context: dict) -> dict:
        """Execute reduce_position action."""
        target = config.get('target')
        reduce_by = config.get('reduce_by', 0.5)  # Default 50% reduction

        positions = context.get('positions', {})
        target_pos = positions.get(target, {})

        current_shares = target_pos.get('shares', 0)
        shares_to_sell = int(current_shares * reduce_by)

        if shares_to_sell > 0:
            return {
                'trades': [{
                    'symbol': target,
                    'action': 'sell',
                    'shares': shares_to_sell,
                    'reason': 'condition_reduce_position'
                }]
            }

        return {'trades': []}

    def _execute_shift_allocation(self, config: dict, context: dict) -> dict:
        """Execute shift_allocation action."""
        reduce = config.get('reduce', {})
        increase = config.get('increase', {})

        portfolio_value = context.get('portfolio_value', 0)
        positions = context.get('positions', {})
        prices = context.get('prices', {})

        trades = []

        # Generate sell orders for reduction
        for sector, pct in reduce.items():
            # Would need to map sector to symbols and generate sells
            pass

        # Generate buy orders for increase
        for sector, pct in increase.items():
            # Would need to map sector to symbols and generate buys
            pass

        return {'trades': trades, 'note': 'shift_allocation_execution'}

    def _execute_reduce_exposure(self, config: dict, context: dict) -> dict:
        """Execute reduce_exposure action."""
        target_cash_pct = config.get('target_cash_pct', 0.30)

        portfolio_value = context.get('portfolio_value', 0)
        cash = context.get('cash', 0)

        current_cash_pct = cash / portfolio_value if portfolio_value > 0 else 0

        if current_cash_pct < target_cash_pct:
            # Need to sell to raise cash
            target_cash = portfolio_value * target_cash_pct
            cash_to_raise = target_cash - cash

            return {
                'trades': [],
                'cash_target': target_cash,
                'cash_to_raise': cash_to_raise,
                'note': 'reduce_exposure_sell_all_proportionally'
            }

        return {'trades': []}

    def _execute_rebalance(self, config: dict, context: dict) -> dict:
        """Execute rebalance action."""
        tolerance = config.get('tolerance', 0.05)

        return {
            'trades': [],
            'note': 'rebalance_to_target_weights',
            'tolerance': tolerance
        }


def get_condition_templates() -> Dict[str, dict]:
    """
    Get all available condition templates.

    Returns:
        Dictionary of template_name -> template info
    """
    return StrategyCondition.get_templates()


def get_condition_template(template_name: str) -> Optional[dict]:
    """
    Get a specific condition template.

    Args:
        template_name: Template name

    Returns:
        Template dictionary or None
    """
    return StrategyCondition.get_template(template_name)
