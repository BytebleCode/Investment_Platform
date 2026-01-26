"""
User Strategy Model

Stores user-created custom strategies with full customization capabilities.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, SmallInteger, DateTime, Text

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class UserStrategy(Base):
    """
    Represents a user-created custom investment strategy.

    Attributes:
        id: Primary key
        user_id: User identifier
        strategy_id: Unique slug for the strategy
        name: Display name
        description: Strategy description
        color: Hex color for UI display
        is_active: Soft delete flag (1=active, 0=archived)
        risk_level: Risk level 1-5
        expected_return_min: Minimum expected annual return %
        expected_return_max: Maximum expected annual return %
        volatility: Price volatility parameter
        daily_drift: Daily price drift parameter
        trade_frequency_seconds: Base seconds between trades
        target_investment_ratio: Target % of cash to invest
        max_position_pct: Maximum position size as % of portfolio
        stop_loss_percent: Stop loss trigger percentage
        take_profit_percent: Take profit trigger percentage
        auto_rebalance: Whether to auto-rebalance
        based_on_template: Source strategy if cloned
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = 'user_strategies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default='default')
    strategy_id = Column(String(50), nullable=False, unique=True)

    # Basic Info
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(20), default='#3b82f6')
    is_active = Column(SmallInteger, default=1)

    # Core Parameters
    risk_level = Column(Integer, default=3)
    expected_return_min = Column(Integer, default=5)
    expected_return_max = Column(Integer, default=15)

    # Trading Behavior
    volatility = Column(Float, default=0.01)
    daily_drift = Column(Float, default=0.00035)
    trade_frequency_seconds = Column(Integer, default=75)
    target_investment_ratio = Column(Float, default=0.7)
    max_position_pct = Column(Float, default=0.15)

    # Risk Management
    stop_loss_percent = Column(Integer, default=10)
    take_profit_percent = Column(Integer, default=20)
    auto_rebalance = Column(SmallInteger, default=1)

    # Metadata
    based_on_template = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Validation constants
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 50
    MIN_RISK = 1
    MAX_RISK = 5
    MIN_VOLATILITY = 0.001
    MAX_VOLATILITY = 0.1
    MIN_DRIFT = 0.0
    MAX_DRIFT = 0.01
    MIN_TRADE_FREQ = 30
    MAX_TRADE_FREQ = 300
    MIN_INVESTMENT_RATIO = 0.1
    MAX_INVESTMENT_RATIO = 1.0
    MIN_POSITION_PCT = 0.05
    MAX_POSITION_PCT = 0.5
    MIN_STOP_LOSS = 5
    MAX_STOP_LOSS = 30
    MIN_TAKE_PROFIT = 10
    MAX_TAKE_PROFIT = 100

    def __repr__(self):
        return f'<UserStrategy {self.user_id}/{self.strategy_id}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'is_active': bool(self.is_active),
            'risk_level': self.risk_level,
            'expected_return_min': self.expected_return_min,
            'expected_return_max': self.expected_return_max,
            'expected_return': (self.expected_return_min, self.expected_return_max),
            'volatility': self.volatility,
            'daily_drift': self.daily_drift,
            'trade_frequency_seconds': self.trade_frequency_seconds,
            'target_investment_ratio': self.target_investment_ratio,
            'max_position_pct': self.max_position_pct,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'auto_rebalance': bool(self.auto_rebalance),
            'based_on_template': self.based_on_template,
            'is_system': False,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def validate(self):
        """
        Validate all strategy parameters.

        Raises:
            ValueError: If any parameter is invalid
        """
        errors = []

        if not self.name or len(self.name) < self.MIN_NAME_LENGTH:
            errors.append(f"name must be at least {self.MIN_NAME_LENGTH} characters")
        elif len(self.name) > self.MAX_NAME_LENGTH:
            errors.append(f"name must be at most {self.MAX_NAME_LENGTH} characters")

        if not self.MIN_RISK <= self.risk_level <= self.MAX_RISK:
            errors.append(f"risk_level must be between {self.MIN_RISK} and {self.MAX_RISK}")

        if not self.MIN_VOLATILITY <= self.volatility <= self.MAX_VOLATILITY:
            errors.append(f"volatility must be between {self.MIN_VOLATILITY} and {self.MAX_VOLATILITY}")

        if not self.MIN_DRIFT <= self.daily_drift <= self.MAX_DRIFT:
            errors.append(f"daily_drift must be between {self.MIN_DRIFT} and {self.MAX_DRIFT}")

        if not self.MIN_TRADE_FREQ <= self.trade_frequency_seconds <= self.MAX_TRADE_FREQ:
            errors.append(f"trade_frequency_seconds must be between {self.MIN_TRADE_FREQ} and {self.MAX_TRADE_FREQ}")

        if not self.MIN_INVESTMENT_RATIO <= self.target_investment_ratio <= self.MAX_INVESTMENT_RATIO:
            errors.append(f"target_investment_ratio must be between {self.MIN_INVESTMENT_RATIO} and {self.MAX_INVESTMENT_RATIO}")

        if not self.MIN_POSITION_PCT <= self.max_position_pct <= self.MAX_POSITION_PCT:
            errors.append(f"max_position_pct must be between {self.MIN_POSITION_PCT} and {self.MAX_POSITION_PCT}")

        if not self.MIN_STOP_LOSS <= self.stop_loss_percent <= self.MAX_STOP_LOSS:
            errors.append(f"stop_loss_percent must be between {self.MIN_STOP_LOSS} and {self.MAX_STOP_LOSS}")

        if not self.MIN_TAKE_PROFIT <= self.take_profit_percent <= self.MAX_TAKE_PROFIT:
            errors.append(f"take_profit_percent must be between {self.MIN_TAKE_PROFIT} and {self.MAX_TAKE_PROFIT}")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_user_strategies(cls, user_id='default', include_inactive=False):
        """Get all strategies for a user."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_user_strategies(user_id, include_inactive)

        session = get_scoped_session()
        query = session.query(cls).filter_by(user_id=user_id)
        if not include_inactive:
            query = query.filter_by(is_active=1)
        return query.all()

    @classmethod
    def get_strategy(cls, strategy_id, user_id='default'):
        """Get a specific user strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_user_strategy(strategy_id, user_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(strategy_id=strategy_id, user_id=user_id).first()

    @classmethod
    def create(cls, user_id, strategy_id, **kwargs):
        """Create a new user strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.create_user_strategy(user_id, strategy_id, **kwargs)

        session = get_scoped_session()
        strategy = cls(user_id=user_id, strategy_id=strategy_id, **kwargs)
        strategy.validate()
        session.add(strategy)
        session.commit()
        return strategy

    @classmethod
    def update(cls, strategy_id, user_id='default', **kwargs):
        """Update an existing user strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.update_user_strategy(strategy_id, user_id, **kwargs)

        session = get_scoped_session()
        strategy = cls.get_strategy(strategy_id, user_id)
        if not strategy:
            return None

        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        strategy.updated_at = datetime.now(timezone.utc)
        strategy.validate()
        session.commit()
        return strategy

    @classmethod
    def delete(cls, strategy_id, user_id='default', hard_delete=False):
        """Delete (archive) a user strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_user_strategy(strategy_id, user_id, hard_delete)

        session = get_scoped_session()
        strategy = cls.get_strategy(strategy_id, user_id)
        if not strategy:
            return False

        if hard_delete:
            session.delete(strategy)
        else:
            strategy.is_active = 0
            strategy.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True
