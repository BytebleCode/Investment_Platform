"""
Strategy Customization Model

Stores user-specific customizations for each investment strategy.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, SmallInteger, DateTime, UniqueConstraint

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class StrategyCustomization(Base):
    """
    Represents user customizations for an investment strategy.

    Attributes:
        id: Primary key
        user_id: User identifier
        strategy_id: Strategy identifier (conservative, growth, etc.)
        confidence_level: User's confidence in strategy (10-100%)
        trade_frequency: How often to trade (low, medium, high)
        max_position_size: Maximum position size as % of portfolio (5-50%)
        stop_loss_percent: Stop loss trigger percentage (5-30%)
        take_profit_percent: Take profit trigger percentage (10-100%)
        auto_rebalance: Whether to auto-rebalance portfolio
        reinvest_dividends: Whether to reinvest dividends
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = 'strategy_customizations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default='default')
    strategy_id = Column(String(50), nullable=False)
    confidence_level = Column(Integer, nullable=False, default=50)
    trade_frequency = Column(String(20), nullable=False, default='medium')
    max_position_size = Column(Integer, nullable=False, default=15)
    stop_loss_percent = Column(Integer, nullable=False, default=10)
    take_profit_percent = Column(Integer, nullable=False, default=20)
    auto_rebalance = Column(SmallInteger, nullable=False, default=1)
    reinvest_dividends = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Unique constraint on user_id + strategy_id
    __table_args__ = (
        UniqueConstraint('user_id', 'strategy_id', name='uix_strategy_user_strategy'),
    )

    # Validation constants
    VALID_FREQUENCIES = ['low', 'medium', 'high']
    MIN_CONFIDENCE = 10
    MAX_CONFIDENCE = 100
    MIN_POSITION_SIZE = 5
    MAX_POSITION_SIZE = 50
    MIN_STOP_LOSS = 5
    MAX_STOP_LOSS = 30
    MIN_TAKE_PROFIT = 10
    MAX_TAKE_PROFIT = 100

    def __repr__(self):
        return f'<StrategyCustomization {self.user_id}/{self.strategy_id}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'confidence_level': self.confidence_level,
            'trade_frequency': self.trade_frequency,
            'max_position_size': self.max_position_size,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'auto_rebalance': bool(self.auto_rebalance),
            'reinvest_dividends': bool(self.reinvest_dividends),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def validate(self):
        """
        Validate all customization parameters.

        Raises:
            ValueError: If any parameter is invalid
        """
        errors = []

        if not self.MIN_CONFIDENCE <= self.confidence_level <= self.MAX_CONFIDENCE:
            errors.append(f"confidence_level must be between {self.MIN_CONFIDENCE} and {self.MAX_CONFIDENCE}")

        if self.trade_frequency not in self.VALID_FREQUENCIES:
            errors.append(f"trade_frequency must be one of: {', '.join(self.VALID_FREQUENCIES)}")

        if not self.MIN_POSITION_SIZE <= self.max_position_size <= self.MAX_POSITION_SIZE:
            errors.append(f"max_position_size must be between {self.MIN_POSITION_SIZE} and {self.MAX_POSITION_SIZE}")

        if not self.MIN_STOP_LOSS <= self.stop_loss_percent <= self.MAX_STOP_LOSS:
            errors.append(f"stop_loss_percent must be between {self.MIN_STOP_LOSS} and {self.MAX_STOP_LOSS}")

        if not self.MIN_TAKE_PROFIT <= self.take_profit_percent <= self.MAX_TAKE_PROFIT:
            errors.append(f"take_profit_percent must be between {self.MIN_TAKE_PROFIT} and {self.MAX_TAKE_PROFIT}")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_user_customizations(cls, user_id='default'):
        """Get all strategy customizations for a user."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_customizations(user_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(user_id=user_id).all()

    @classmethod
    def get_customization(cls, user_id, strategy_id):
        """Get customization for a specific user and strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_customization(user_id, strategy_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(user_id=user_id, strategy_id=strategy_id).first()

    @classmethod
    def upsert(cls, user_id, strategy_id, **kwargs):
        """
        Create or update a strategy customization.

        Args:
            user_id: User identifier
            strategy_id: Strategy identifier
            **kwargs: Customization parameters

        Returns:
            StrategyCustomization instance or dict (if CSV backend)
        """
        if is_csv_backend():
            storage = get_csv_storage()
            storage.upsert_strategy_customization(user_id, strategy_id, **kwargs)
            return storage.get_strategy_customization(user_id, strategy_id)

        session = get_scoped_session()
        customization = cls.get_customization(user_id, strategy_id)

        if customization:
            # Update existing
            for key, value in kwargs.items():
                if hasattr(customization, key):
                    setattr(customization, key, value)
            customization.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            customization = cls(user_id=user_id, strategy_id=strategy_id, **kwargs)
            session.add(customization)

        customization.validate()
        return customization
