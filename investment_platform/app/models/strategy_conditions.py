"""
Strategy Conditions Model

Stores conditional triggers and actions for strategies (price, macro, portfolio, time-based).
"""
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class StrategyCondition(Base):
    """
    Represents a conditional trigger with associated action for a strategy.

    Condition Types:
        - price: Price-based triggers (percent change, threshold, etc.)
        - macro: Macro indicator triggers (FRED signals)
        - portfolio: Portfolio metric triggers (drawdown, allocation drift)
        - time: Time-based triggers (scheduled rebalancing)

    Action Types:
        - reduce_position: Sell portion of specific holding
        - shift_allocation: Move weight between sectors
        - reduce_exposure: Increase cash position
        - rebalance: Return to target weights

    Attributes:
        id: Primary key
        strategy_id: The strategy this condition belongs to
        condition_name: Human-readable name for the condition
        condition_type: Type of condition (price, macro, portfolio, time)
        trigger_config: JSON configuration for when to trigger
        action_config: JSON configuration for what to do
        is_active: Whether this condition is currently active
        last_triggered: When this condition was last triggered
        created_at: Record creation timestamp
    """
    __tablename__ = 'strategy_conditions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False, index=True)
    condition_name = Column(String(100))
    condition_type = Column(String(30), nullable=False)
    trigger_config = Column(Text, nullable=False)  # JSON
    action_config = Column(Text, nullable=False)   # JSON
    is_active = Column(Integer, default=1)
    last_triggered = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Valid condition types
    CONDITION_TYPES = ['price', 'macro', 'portfolio', 'time']

    # Valid action types
    ACTION_TYPES = ['reduce_position', 'shift_allocation', 'reduce_exposure', 'rebalance']

    # Trigger schemas for each condition type
    TRIGGER_SCHEMAS = {
        'price': {
            'required': ['symbol', 'comparison', 'threshold'],
            'optional': ['lookback_days'],
            'example': {
                'symbol': 'AAPL',
                'comparison': 'percent_change',
                'threshold': -0.10,
                'lookback_days': 5
            }
        },
        'macro': {
            'required': ['signal', 'comparison', 'threshold'],
            'optional': [],
            'example': {
                'signal': 'T10Y2Y',
                'comparison': 'less_than',
                'threshold': 0
            }
        },
        'portfolio': {
            'required': ['metric', 'comparison', 'threshold'],
            'optional': ['lookback_days'],
            'example': {
                'metric': 'drawdown',
                'comparison': 'greater_than',
                'threshold': 0.15
            }
        },
        'time': {
            'required': ['schedule'],
            'optional': ['day_of_week', 'day_of_month'],
            'example': {
                'schedule': 'weekly',
                'day_of_week': 'monday'
            }
        }
    }

    # Action schemas
    ACTION_SCHEMAS = {
        'reduce_position': {
            'required': ['target', 'reduce_by'],
            'example': {
                'target': 'AAPL',
                'reduce_by': 0.5  # Reduce by 50%
            }
        },
        'shift_allocation': {
            'required': ['reduce', 'increase'],
            'example': {
                'reduce': {'technology': 0.10, 'consumer_discretionary': 0.10},
                'increase': {'utilities': 0.10, 'healthcare': 0.10}
            }
        },
        'reduce_exposure': {
            'required': ['target_cash_pct'],
            'example': {
                'target_cash_pct': 0.30
            }
        },
        'rebalance': {
            'required': [],
            'optional': ['tolerance'],
            'example': {
                'tolerance': 0.05  # Rebalance if off by more than 5%
            }
        }
    }

    # Preset templates
    TEMPLATES = {
        'recession_defense': {
            'name': 'Recession Defense',
            'description': 'Shift to defensive sectors when yield curve inverts',
            'condition_type': 'macro',
            'trigger_config': {
                'signal': 'T10Y2Y',
                'comparison': 'less_than',
                'threshold': 0
            },
            'action_config': {
                'action': 'shift_allocation',
                'reduce': {'technology': 0.10, 'consumer_discretionary': 0.10},
                'increase': {'utilities': 0.10, 'healthcare': 0.10}
            }
        },
        'stop_loss': {
            'name': 'Portfolio Stop Loss',
            'description': 'Reduce exposure on significant drawdown',
            'condition_type': 'portfolio',
            'trigger_config': {
                'metric': 'drawdown',
                'comparison': 'greater_than',
                'threshold': 0.15
            },
            'action_config': {
                'action': 'reduce_exposure',
                'target_cash_pct': 0.40
            }
        },
        'drawdown_protection': {
            'name': 'Drawdown Protection',
            'description': 'Reduce position size after significant loss',
            'condition_type': 'portfolio',
            'trigger_config': {
                'metric': 'daily_loss',
                'comparison': 'greater_than',
                'threshold': 0.05
            },
            'action_config': {
                'action': 'reduce_exposure',
                'target_cash_pct': 0.25
            }
        },
        'volatility_spike': {
            'name': 'Volatility Spike',
            'description': 'Reduce equity exposure when VIX spikes',
            'condition_type': 'macro',
            'trigger_config': {
                'signal': 'VIXCLS',
                'comparison': 'greater_than',
                'threshold': 30
            },
            'action_config': {
                'action': 'reduce_exposure',
                'target_cash_pct': 0.35
            }
        },
        'scheduled_rebalance': {
            'name': 'Scheduled Rebalance',
            'description': 'Weekly rebalance to target weights',
            'condition_type': 'time',
            'trigger_config': {
                'schedule': 'weekly',
                'day_of_week': 'monday'
            },
            'action_config': {
                'action': 'rebalance',
                'tolerance': 0.05
            }
        }
    }

    def __repr__(self):
        return f'<StrategyCondition {self.strategy_id}/{self.condition_name} ({self.condition_type})>'

    def get_trigger_config(self):
        """Parse and return the trigger config as a dictionary."""
        try:
            return json.loads(self.trigger_config) if self.trigger_config else {}
        except json.JSONDecodeError:
            return {}

    def set_trigger_config(self, config_dict):
        """Set the trigger config from a dictionary."""
        self.trigger_config = json.dumps(config_dict)

    def get_action_config(self):
        """Parse and return the action config as a dictionary."""
        try:
            return json.loads(self.action_config) if self.action_config else {}
        except json.JSONDecodeError:
            return {}

    def set_action_config(self, config_dict):
        """Set the action config from a dictionary."""
        self.action_config = json.dumps(config_dict)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'condition_name': self.condition_name,
            'condition_type': self.condition_type,
            'trigger_config': self.get_trigger_config(),
            'action_config': self.get_action_config(),
            'is_active': bool(self.is_active),
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def validate(self):
        """Validate condition parameters and configs."""
        errors = []

        if not self.strategy_id:
            errors.append("strategy_id is required")

        if self.condition_type not in self.CONDITION_TYPES:
            errors.append(f"condition_type must be one of: {', '.join(self.CONDITION_TYPES)}")

        # Validate trigger config schema
        if self.condition_type in self.TRIGGER_SCHEMAS:
            config = self.get_trigger_config()
            schema = self.TRIGGER_SCHEMAS[self.condition_type]
            for required_field in schema['required']:
                if required_field not in config:
                    errors.append(f"trigger_config missing required field: {required_field}")

        # Validate action config
        action_config = self.get_action_config()
        if 'action' in action_config:
            action_type = action_config['action']
            if action_type not in self.ACTION_TYPES:
                errors.append(f"action must be one of: {', '.join(self.ACTION_TYPES)}")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_conditions(cls, strategy_id, include_inactive=False):
        """Get all conditions for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_conditions(strategy_id, include_inactive)

        session = get_scoped_session()
        query = session.query(cls).filter_by(strategy_id=strategy_id)
        if not include_inactive:
            query = query.filter_by(is_active=1)
        return query.all()

    @classmethod
    def get_condition(cls, condition_id):
        """Get a specific condition by ID."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_condition(condition_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(id=condition_id).first()

    @classmethod
    def create(cls, strategy_id, condition_type, trigger_config, action_config,
               condition_name=None, is_active=True):
        """Create a new condition."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.create_strategy_condition(
                strategy_id=strategy_id,
                condition_type=condition_type,
                trigger_config=trigger_config,
                action_config=action_config,
                condition_name=condition_name,
                is_active=is_active
            )

        session = get_scoped_session()
        condition = cls(
            strategy_id=strategy_id,
            condition_name=condition_name,
            condition_type=condition_type,
            is_active=1 if is_active else 0
        )
        condition.set_trigger_config(trigger_config)
        condition.set_action_config(action_config)
        condition.validate()
        session.add(condition)
        session.commit()
        return condition

    @classmethod
    def create_from_template(cls, strategy_id, template_name, is_active=True):
        """Create a condition from a preset template."""
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")

        template = cls.TEMPLATES[template_name]
        return cls.create(
            strategy_id=strategy_id,
            condition_type=template['condition_type'],
            trigger_config=template['trigger_config'],
            action_config=template['action_config'],
            condition_name=template['name'],
            is_active=is_active
        )

    @classmethod
    def update(cls, condition_id, **kwargs):
        """Update an existing condition."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.update_strategy_condition(condition_id, **kwargs)

        session = get_scoped_session()
        condition = cls.get_condition(condition_id)
        if not condition:
            return None

        for key, value in kwargs.items():
            if key == 'trigger_config':
                condition.set_trigger_config(value)
            elif key == 'action_config':
                condition.set_action_config(value)
            elif key == 'is_active':
                condition.is_active = 1 if value else 0
            elif hasattr(condition, key):
                setattr(condition, key, value)

        condition.validate()
        session.commit()
        return condition

    @classmethod
    def mark_triggered(cls, condition_id):
        """Mark a condition as triggered (update last_triggered timestamp)."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.mark_condition_triggered(condition_id)

        session = get_scoped_session()
        condition = cls.get_condition(condition_id)
        if condition:
            condition.last_triggered = datetime.now(timezone.utc)
            session.commit()
            return condition
        return None

    @classmethod
    def delete(cls, condition_id, hard_delete=False):
        """Delete (or deactivate) a condition."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_strategy_condition(condition_id, hard_delete)

        session = get_scoped_session()
        condition = cls.get_condition(condition_id)
        if not condition:
            return False

        if hard_delete:
            session.delete(condition)
        else:
            condition.is_active = 0
        session.commit()
        return True

    @classmethod
    def delete_all_for_strategy(cls, strategy_id, hard_delete=False):
        """Delete all conditions for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_all_strategy_conditions(strategy_id, hard_delete)

        session = get_scoped_session()
        conditions = cls.get_conditions(strategy_id, include_inactive=True)
        for condition in conditions:
            if hard_delete:
                session.delete(condition)
            else:
                condition.is_active = 0
        session.commit()
        return True

    @classmethod
    def get_templates(cls):
        """Get all available preset templates."""
        return {
            name: {
                'name': template['name'],
                'description': template['description'],
                'condition_type': template['condition_type']
            }
            for name, template in cls.TEMPLATES.items()
        }

    @classmethod
    def get_template(cls, template_name):
        """Get a specific template by name."""
        return cls.TEMPLATES.get(template_name)
