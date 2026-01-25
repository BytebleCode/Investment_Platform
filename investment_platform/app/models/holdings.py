"""
Holdings Model

Tracks current stock positions including quantity and average cost basis.
"""
from datetime import datetime, timezone
from decimal import Decimal
from app import db


class Holdings(db.Model):
    """
    Represents a stock holding in a user's portfolio.

    Attributes:
        id: Primary key
        user_id: User identifier
        symbol: Stock ticker symbol (e.g., 'AAPL')
        name: Company name
        sector: Industry sector
        quantity: Number of shares held
        avg_cost: Average cost per share
        created_at: When position was first opened
        updated_at: Last modification timestamp
    """
    __tablename__ = 'holdings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), nullable=False, default='default')
    symbol = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    sector = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Numeric(15, 4), nullable=False)
    avg_cost = db.Column(db.Numeric(15, 4), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Unique constraint on user_id + symbol
    __table_args__ = (
        db.UniqueConstraint('user_id', 'symbol', name='uix_holdings_user_symbol'),
    )

    def __repr__(self):
        return f'<Holdings {self.symbol}: {self.quantity} @ ${self.avg_cost}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'quantity': float(self.quantity),
            'avg_cost': float(self.avg_cost),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def total_cost(self):
        """Calculate total cost basis for this holding."""
        return self.quantity * self.avg_cost

    def update_on_buy(self, buy_quantity, buy_price):
        """
        Update holding after a buy transaction using weighted average cost.

        Args:
            buy_quantity: Number of shares purchased
            buy_price: Price per share
        """
        old_total = self.quantity * self.avg_cost
        new_total = Decimal(str(buy_quantity)) * Decimal(str(buy_price))
        new_quantity = self.quantity + Decimal(str(buy_quantity))

        if new_quantity > 0:
            self.avg_cost = (old_total + new_total) / new_quantity
        self.quantity = new_quantity
        self.updated_at = datetime.now(timezone.utc)

    def update_on_sell(self, sell_quantity):
        """
        Update holding after a sell transaction.
        Average cost remains unchanged on sells.

        Args:
            sell_quantity: Number of shares sold

        Returns:
            Decimal: Cost basis of sold shares (for realized gain calculation)
        """
        sell_qty = Decimal(str(sell_quantity))
        if sell_qty > self.quantity:
            raise ValueError(f"Cannot sell {sell_quantity} shares, only {self.quantity} held")

        cost_basis = sell_qty * self.avg_cost
        self.quantity -= sell_qty
        self.updated_at = datetime.now(timezone.utc)
        return cost_basis

    @classmethod
    def get_user_holdings(cls, user_id='default'):
        """Get all holdings for a user, ordered by symbol."""
        return cls.query.filter_by(user_id=user_id).order_by(cls.symbol).all()

    @classmethod
    def get_holding(cls, user_id, symbol):
        """Get a specific holding by user and symbol."""
        return cls.query.filter_by(user_id=user_id, symbol=symbol).first()

    @classmethod
    def delete_user_holdings(cls, user_id='default'):
        """Delete all holdings for a user (used in portfolio reset)."""
        cls.query.filter_by(user_id=user_id).delete()
