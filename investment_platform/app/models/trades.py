"""
Trades History Model

Records all buy and sell transactions for audit trail and analysis.
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class TradesHistory(Base):
    """
    Represents a completed trade transaction.

    Attributes:
        id: Primary key
        user_id: User identifier
        trade_id: Unique trade identifier (UUID)
        timestamp: When the trade was executed
        type: Trade type ('buy' or 'sell')
        symbol: Stock ticker symbol
        stock_name: Company name
        sector: Industry sector
        quantity: Number of shares traded
        price: Price per share
        total: Total transaction value
        fees: Trading fees
        strategy: Strategy used for this trade
        created_at: Record creation timestamp
    """
    __tablename__ = 'trades_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default='default')
    trade_id = Column(String(100), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    type = Column(String(10), nullable=False)  # 'buy' or 'sell'
    symbol = Column(String(10), nullable=False)
    stock_name = Column(String(100), nullable=True)
    sector = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    total = Column(Numeric(15, 2), nullable=False)
    fees = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    strategy = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Trade {self.trade_id}: {self.type} {self.quantity} {self.symbol} @ ${self.price}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'trade_id': self.trade_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'type': self.type,
            'symbol': self.symbol,
            'stock_name': self.stock_name,
            'sector': self.sector,
            'quantity': self.quantity,
            'price': float(self.price),
            'total': float(self.total),
            'fees': float(self.fees),
            'strategy': self.strategy,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_user_trades(cls, user_id='default', limit=100):
        """
        Get trades for a user, ordered by timestamp descending.

        Args:
            user_id: User identifier
            limit: Maximum number of trades to return

        Returns:
            List of TradesHistory instances or dicts (if CSV backend)
        """
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_trades(user_id, limit=limit)

        session = get_scoped_session()
        return session.query(cls).filter_by(user_id=user_id)\
            .order_by(cls.timestamp.desc())\
            .limit(limit)\
            .all()

    @classmethod
    def get_trades_by_type(cls, user_id='default', trade_type=None, limit=100):
        """
        Get trades filtered by type.

        Args:
            user_id: User identifier
            trade_type: 'buy', 'sell', or None for all
            limit: Maximum number of trades to return
        """
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_trades(user_id, limit=limit, trade_type=trade_type)

        session = get_scoped_session()
        query = session.query(cls).filter_by(user_id=user_id)
        if trade_type:
            query = query.filter_by(type=trade_type)
        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def delete_user_trades(cls, user_id='default'):
        """Delete all trades for a user (used in portfolio reset)."""
        if is_csv_backend():
            storage = get_csv_storage()
            storage.delete_user_trades(user_id)
            return

        session = get_scoped_session()
        session.query(cls).filter_by(user_id=user_id).delete()

    @classmethod
    def get_trade_count(cls, user_id='default'):
        """Get total number of trades for a user."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_trade_count(user_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(user_id=user_id).count()
