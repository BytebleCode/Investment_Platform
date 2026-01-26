"""
Strategy Rules Model

Stores relational trading rules for strategies (hedge, pair, rebalance, correlation).
"""
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class StrategyRule(Base):
    """
    Represents a relational trading rule within a strategy.

    Rule Types:
        - hedge: When position A changes, adjust position B inversely
        - pair: Long/short spread trading between two components
        - rebalance: Threshold-based rebalancing rules
        - correlation: Reduce exposure when correlation spikes

    Attributes:
        id: Primary key
        strategy_id: The strategy this rule belongs to
        rule_name: Human-readable name for the rule
        rule_type: Type of rule (hedge, pair, rebalance, correlation)
        is_active: Whether this rule is currently active
        priority: Execution priority (higher = first)
        config: JSON configuration for the rule
        created_at: Record creation timestamp
    """
    __tablename__ = 'strategy_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(30), nullable=False)
    is_active = Column(Integer, default=1)
    priority = Column(Integer, default=0)
    config = Column(Text, nullable=False)  # JSON configuration
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Valid rule types
    RULE_TYPES = ['hedge', 'pair', 'rebalance', 'correlation']

    # Config schemas for each rule type
    CONFIG_SCHEMAS = {
        'hedge': {
            'required': ['primary', 'hedge', 'ratio'],
            'optional': ['trigger'],
            'example': {
                'primary': 'NVDA',
                'hedge': 'GLD',
                'ratio': -0.3,
                'trigger': 'position_change'
            }
        },
        'pair': {
            'required': ['long', 'short', 'spread_target'],
            'optional': ['rebalance_threshold'],
            'example': {
                'long': 'technology.semiconductors',
                'short': 'utilities.electric',
                'spread_target': 0.02,
                'rebalance_threshold': 0.05
            }
        },
        'rebalance': {
            'required': ['components', 'threshold'],
            'optional': ['frequency'],
            'example': {
                'components': ['financials', 'technology', 'healthcare'],
                'threshold': 0.05,
                'frequency': 'weekly'
            }
        },
        'correlation': {
            'required': ['components', 'target_correlation', 'action'],
            'optional': ['lookback_days'],
            'example': {
                'components': ['AAPL', 'MSFT', 'GOOGL'],
                'target_correlation': 0.6,
                'action': 'reduce_on_high_correlation',
                'lookback_days': 30
            }
        }
    }

    def __repr__(self):
        return f'<StrategyRule {self.strategy_id}/{self.rule_name} ({self.rule_type})>'

    def get_config(self):
        """Parse and return the config as a dictionary."""
        try:
            return json.loads(self.config) if self.config else {}
        except json.JSONDecodeError:
            return {}

    def set_config(self, config_dict):
        """Set the config from a dictionary."""
        self.config = json.dumps(config_dict)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'is_active': bool(self.is_active),
            'priority': self.priority,
            'config': self.get_config(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def validate(self):
        """Validate rule parameters and config."""
        errors = []

        if not self.strategy_id:
            errors.append("strategy_id is required")

        if not self.rule_name:
            errors.append("rule_name is required")

        if self.rule_type not in self.RULE_TYPES:
            errors.append(f"rule_type must be one of: {', '.join(self.RULE_TYPES)}")

        # Validate config schema
        if self.rule_type in self.CONFIG_SCHEMAS:
            config = self.get_config()
            schema = self.CONFIG_SCHEMAS[self.rule_type]
            for required_field in schema['required']:
                if required_field not in config:
                    errors.append(f"config missing required field: {required_field}")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_rules(cls, strategy_id, include_inactive=False):
        """Get all rules for a strategy, ordered by priority."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_rules(strategy_id, include_inactive)

        session = get_scoped_session()
        query = session.query(cls).filter_by(strategy_id=strategy_id)
        if not include_inactive:
            query = query.filter_by(is_active=1)
        return query.order_by(cls.priority.desc()).all()

    @classmethod
    def get_rule(cls, rule_id):
        """Get a specific rule by ID."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_rule(rule_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(id=rule_id).first()

    @classmethod
    def create(cls, strategy_id, rule_name, rule_type, config, priority=0, is_active=True):
        """Create a new rule."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.create_strategy_rule(
                strategy_id=strategy_id,
                rule_name=rule_name,
                rule_type=rule_type,
                config=config,
                priority=priority,
                is_active=is_active
            )

        session = get_scoped_session()
        rule = cls(
            strategy_id=strategy_id,
            rule_name=rule_name,
            rule_type=rule_type,
            priority=priority,
            is_active=1 if is_active else 0
        )
        rule.set_config(config)
        rule.validate()
        session.add(rule)
        session.commit()
        return rule

    @classmethod
    def update(cls, rule_id, **kwargs):
        """Update an existing rule."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.update_strategy_rule(rule_id, **kwargs)

        session = get_scoped_session()
        rule = cls.get_rule(rule_id)
        if not rule:
            return None

        for key, value in kwargs.items():
            if key == 'config':
                rule.set_config(value)
            elif key == 'is_active':
                rule.is_active = 1 if value else 0
            elif hasattr(rule, key):
                setattr(rule, key, value)

        rule.validate()
        session.commit()
        return rule

    @classmethod
    def delete(cls, rule_id, hard_delete=False):
        """Delete (or deactivate) a rule."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_strategy_rule(rule_id, hard_delete)

        session = get_scoped_session()
        rule = cls.get_rule(rule_id)
        if not rule:
            return False

        if hard_delete:
            session.delete(rule)
        else:
            rule.is_active = 0
        session.commit()
        return True

    @classmethod
    def delete_all_for_strategy(cls, strategy_id, hard_delete=False):
        """Delete all rules for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_all_strategy_rules(strategy_id, hard_delete)

        session = get_scoped_session()
        rules = cls.get_rules(strategy_id, include_inactive=True)
        for rule in rules:
            if hard_delete:
                session.delete(rule)
            else:
                rule.is_active = 0
        session.commit()
        return True

    @classmethod
    def get_template(cls, rule_type):
        """Get a template configuration for a rule type."""
        if rule_type in cls.CONFIG_SCHEMAS:
            return cls.CONFIG_SCHEMAS[rule_type]['example']
        return {}
