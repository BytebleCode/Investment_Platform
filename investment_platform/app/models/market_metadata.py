"""
Market Data Metadata Model

Tracks cache status for each symbol to enable smart cache refresh.
"""
from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, DateTime, Date

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class MarketDataMetadata(Base):
    """
    Tracks metadata about cached market data for each symbol.

    Used to determine when to fetch new data and what date ranges
    are already cached.

    Attributes:
        id: Primary key
        symbol: Stock ticker symbol (unique)
        last_fetch_date: Date of most recent data fetch
        earliest_date: Earliest date in cache for this symbol
        latest_date: Most recent date in cache for this symbol
        total_records: Number of cached price records
        last_updated: When metadata was last updated
        fetch_status: Current status (pending, fetching, complete, error)
    """
    __tablename__ = 'market_data_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    last_fetch_date = Column(Date, nullable=True)
    earliest_date = Column(Date, nullable=True)
    latest_date = Column(Date, nullable=True)
    total_records = Column(Integer, nullable=True, default=0)
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fetch_status = Column(String(20), nullable=False, default='pending')

    # Valid status values
    STATUS_PENDING = 'pending'
    STATUS_FETCHING = 'fetching'
    STATUS_COMPLETE = 'complete'
    STATUS_ERROR = 'error'

    def __repr__(self):
        return f'<MarketDataMetadata {self.symbol}: {self.earliest_date} to {self.latest_date}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'last_fetch_date': self.last_fetch_date.isoformat() if self.last_fetch_date else None,
            'earliest_date': self.earliest_date.isoformat() if self.earliest_date else None,
            'latest_date': self.latest_date.isoformat() if self.latest_date else None,
            'total_records': self.total_records,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'fetch_status': self.fetch_status
        }

    def needs_refresh(self, target_date=None):
        """
        Check if this symbol's cache needs refreshing.

        Args:
            target_date: Date to check against (defaults to today)

        Returns:
            bool: True if cache needs refresh
        """
        if target_date is None:
            target_date = date.today()

        # Never fetched
        if self.latest_date is None:
            return True

        # Cache is stale (latest date is before target)
        if self.latest_date < target_date:
            return True

        return False

    def get_missing_range(self, start_date, end_date):
        """
        Determine what date ranges need to be fetched.

        Args:
            start_date: Desired start date
            end_date: Desired end date

        Returns:
            List of (start, end) tuples representing missing ranges
        """
        missing = []

        if self.earliest_date is None or self.latest_date is None:
            # No data cached, need entire range
            return [(start_date, end_date)]

        # Check for gap at the beginning
        if start_date < self.earliest_date:
            missing.append((start_date, self.earliest_date))

        # Check for gap at the end
        if end_date > self.latest_date:
            missing.append((self.latest_date, end_date))

        return missing

    @classmethod
    def get_or_create(cls, symbol):
        """
        Get existing metadata or create new entry.

        Args:
            symbol: Stock ticker symbol

        Returns:
            MarketDataMetadata instance or dict (if CSV backend)
        """
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_or_create_market_metadata(symbol)

        session = get_scoped_session()
        metadata = session.query(cls).filter_by(symbol=symbol).first()
        if not metadata:
            metadata = cls(symbol=symbol)
            session.add(metadata)
            session.commit()
        return metadata

    @classmethod
    def get_all_symbols(cls):
        """Get list of all symbols with cached data."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_all_symbols()

        session = get_scoped_session()
        results = session.query(cls.symbol).all()
        return [r[0] for r in results]

    @classmethod
    def get_stale_symbols(cls, before_date=None):
        """
        Get symbols that need refreshing.

        Args:
            before_date: Consider stale if latest_date is before this date

        Returns:
            List of symbol strings
        """
        if before_date is None:
            before_date = date.today()

        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_stale_symbols(before_date)

        session = get_scoped_session()
        results = session.query(cls).filter(
            (cls.latest_date < before_date) | (cls.latest_date.is_(None))
        ).all()
        return [r.symbol for r in results]

    def update_after_fetch(self, earliest, latest, total_records):
        """
        Update metadata after a successful data fetch.

        Args:
            earliest: Earliest date in fetched data
            latest: Latest date in fetched data
            total_records: Total number of records now in cache
        """
        self.earliest_date = earliest if self.earliest_date is None else min(self.earliest_date, earliest)
        self.latest_date = latest if self.latest_date is None else max(self.latest_date, latest)
        self.total_records = total_records
        self.last_fetch_date = date.today()
        self.last_updated = datetime.now(timezone.utc)
        self.fetch_status = self.STATUS_COMPLETE

    @classmethod
    def delete_metadata(cls, symbol):
        """Delete metadata for a symbol."""
        if is_csv_backend():
            # For CSV, metadata is auto-managed
            return

        session = get_scoped_session()
        return session.query(cls).filter_by(symbol=symbol).delete()
