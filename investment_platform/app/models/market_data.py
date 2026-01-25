"""
Market Data Cache Model

Caches historical price data from Yahoo Finance to minimize API calls.
"""
from datetime import datetime, date, timezone
from decimal import Decimal
from app import db


class MarketDataCache(db.Model):
    """
    Caches OHLCV (Open, High, Low, Close, Volume) price data.

    Attributes:
        id: Primary key
        symbol: Stock ticker symbol
        date: Trading date
        open: Opening price
        high: Highest price of the day
        low: Lowest price of the day
        close: Closing price
        adj_close: Adjusted closing price (accounts for splits/dividends)
        volume: Trading volume
        fetched_at: When this data was fetched from Yahoo Finance
    """
    __tablename__ = 'market_data_cache'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    open = db.Column(db.Numeric(15, 4), nullable=True)
    high = db.Column(db.Numeric(15, 4), nullable=True)
    low = db.Column(db.Numeric(15, 4), nullable=True)
    close = db.Column(db.Numeric(15, 4), nullable=False)
    adj_close = db.Column(db.Numeric(15, 4), nullable=False)
    volume = db.Column(db.BigInteger, nullable=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Unique constraint on symbol + date
    __table_args__ = (
        db.UniqueConstraint('symbol', 'date', name='uix_market_data_symbol_date'),
        db.Index('ix_market_data_symbol_date', 'symbol', 'date'),
    )

    def __repr__(self):
        return f'<MarketDataCache {self.symbol} {self.date}: ${self.close}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat() if self.date else None,
            'open': float(self.open) if self.open else None,
            'high': float(self.high) if self.high else None,
            'low': float(self.low) if self.low else None,
            'close': float(self.close),
            'adj_close': float(self.adj_close),
            'volume': self.volume,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None
        }

    @classmethod
    def get_price_range(cls, symbol, start_date, end_date):
        """
        Get cached price data for a symbol within a date range.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of MarketDataCache instances ordered by date
        """
        return cls.query.filter(
            cls.symbol == symbol,
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date).all()

    @classmethod
    def get_latest_price(cls, symbol):
        """
        Get the most recent cached price for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            MarketDataCache instance or None
        """
        return cls.query.filter_by(symbol=symbol)\
            .order_by(cls.date.desc())\
            .first()

    @classmethod
    def get_cached_dates(cls, symbol):
        """
        Get all dates for which we have cached data for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Set of date objects
        """
        results = db.session.query(cls.date)\
            .filter_by(symbol=symbol)\
            .all()
        return {r[0] for r in results}

    @classmethod
    def bulk_insert(cls, records):
        """
        Insert multiple price records efficiently.

        Args:
            records: List of dicts with symbol, date, open, high, low, close, adj_close, volume
        """
        for record in records:
            # Check if record exists
            existing = cls.query.filter_by(
                symbol=record['symbol'],
                date=record['date']
            ).first()

            if existing:
                # Update existing record
                existing.open = record.get('open')
                existing.high = record.get('high')
                existing.low = record.get('low')
                existing.close = record['close']
                existing.adj_close = record['adj_close']
                existing.volume = record.get('volume')
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                # Insert new record
                new_record = cls(
                    symbol=record['symbol'],
                    date=record['date'],
                    open=record.get('open'),
                    high=record.get('high'),
                    low=record.get('low'),
                    close=record['close'],
                    adj_close=record['adj_close'],
                    volume=record.get('volume'),
                    fetched_at=datetime.now(timezone.utc)
                )
                db.session.add(new_record)

    @classmethod
    def delete_symbol_cache(cls, symbol):
        """Delete all cached data for a symbol."""
        return cls.query.filter_by(symbol=symbol).delete()

    @classmethod
    def delete_all_cache(cls):
        """Delete all cached market data."""
        return cls.query.delete()
