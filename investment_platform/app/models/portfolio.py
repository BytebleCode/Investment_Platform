"""
Portfolio State Model

Tracks the overall state of a user's portfolio including cash balance,
current strategy, and realized gains.
"""
from datetime import datetime, timezone
from decimal import Decimal
from app import db


class PortfolioState(db.Model):
    """
    Represents the current state of a user's investment portfolio.

    Attributes:
        id: Primary key
        user_id: Unique identifier for the user (default: 'default')
        initial_value: Starting portfolio value
        current_cash: Available cash balance
        current_strategy: Active investment strategy
        is_initialized: Whether portfolio has been set up
        realized_gains: Total realized gains/losses from closed positions
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = 'portfolio_state'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False, default='default')
    initial_value = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('100000.00'))
    current_cash = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('100000.00'))
    current_strategy = db.Column(db.String(50), nullable=False, default='balanced')
    is_initialized = db.Column(db.SmallInteger, nullable=False, default=0)
    realized_gains = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<PortfolioState {self.user_id}: ${self.current_cash}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'initial_value': float(self.initial_value),
            'current_cash': float(self.current_cash),
            'current_strategy': self.current_strategy,
            'is_initialized': bool(self.is_initialized),
            'realized_gains': float(self.realized_gains),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_or_create(cls, user_id='default'):
        """
        Get existing portfolio or create a new one.

        Args:
            user_id: User identifier

        Returns:
            PortfolioState instance
        """
        portfolio = cls.query.filter_by(user_id=user_id).first()
        if not portfolio:
            portfolio = cls(user_id=user_id)
            db.session.add(portfolio)
            db.session.commit()
        return portfolio

    def reset(self):
        """Reset portfolio to initial state."""
        self.current_cash = self.initial_value
        self.realized_gains = Decimal('0.00')
        self.is_initialized = 0
        self.updated_at = datetime.now(timezone.utc)
