"""
User Strategy Stocks Model

Stores the stock symbols associated with each user strategy.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class UserStrategyStock(Base):
    """
    Represents a stock in a user's custom strategy.

    Attributes:
        id: Primary key
        user_strategy_id: Foreign key to user_strategies.id
        strategy_id: Strategy identifier (denormalized for easier queries)
        symbol: Stock ticker symbol
        weight: Allocation weight (for future weighted allocation feature)
        created_at: Record creation timestamp
    """
    __tablename__ = 'user_strategy_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_strategy_id = Column(Integer, ForeignKey('user_strategies.id'))
    strategy_id = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Validation constants
    MIN_STOCKS = 1
    MAX_STOCKS = 50

    def __repr__(self):
        return f'<UserStrategyStock {self.strategy_id}/{self.symbol}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_strategy_id': self.user_strategy_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_stocks_for_strategy(cls, strategy_id):
        """Get all stocks for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_stocks(strategy_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(strategy_id=strategy_id).all()

    @classmethod
    def get_symbols_for_strategy(cls, strategy_id):
        """Get just the symbol list for a strategy."""
        stocks = cls.get_stocks_for_strategy(strategy_id)
        if not stocks:
            return []
        if isinstance(stocks[0], dict):
            return [s['symbol'] for s in stocks]
        return [s.symbol for s in stocks]

    @classmethod
    def set_stocks_for_strategy(cls, strategy_id, symbols, user_strategy_id=None):
        """
        Replace all stocks for a strategy with new list.

        Args:
            strategy_id: Strategy identifier
            symbols: List of stock symbols
            user_strategy_id: Optional FK to user_strategies table
        """
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.set_strategy_stocks(strategy_id, symbols, user_strategy_id)

        session = get_scoped_session()

        # Delete existing stocks
        session.query(cls).filter_by(strategy_id=strategy_id).delete()

        # Add new stocks
        for symbol in symbols:
            stock = cls(
                user_strategy_id=user_strategy_id,
                strategy_id=strategy_id,
                symbol=symbol.upper(),
                weight=1.0
            )
            session.add(stock)

        session.commit()
        return True

    @classmethod
    def add_stock(cls, strategy_id, symbol, weight=1.0, user_strategy_id=None):
        """Add a single stock to a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.add_strategy_stock(strategy_id, symbol, weight, user_strategy_id)

        session = get_scoped_session()

        # Check if already exists
        existing = session.query(cls).filter_by(
            strategy_id=strategy_id,
            symbol=symbol.upper()
        ).first()

        if existing:
            existing.weight = weight
            session.commit()
            return existing

        stock = cls(
            user_strategy_id=user_strategy_id,
            strategy_id=strategy_id,
            symbol=symbol.upper(),
            weight=weight
        )
        session.add(stock)
        session.commit()
        return stock

    @classmethod
    def remove_stock(cls, strategy_id, symbol):
        """Remove a stock from a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.remove_strategy_stock(strategy_id, symbol)

        session = get_scoped_session()
        result = session.query(cls).filter_by(
            strategy_id=strategy_id,
            symbol=symbol.upper()
        ).delete()
        session.commit()
        return result > 0

    @classmethod
    def delete_all_for_strategy(cls, strategy_id):
        """Delete all stocks for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_all_strategy_stocks(strategy_id)

        session = get_scoped_session()
        session.query(cls).filter_by(strategy_id=strategy_id).delete()
        session.commit()
        return True
