"""
Market Data Service

Fetches real market data from Yahoo Finance via pandas_datareader.
Implements intelligent caching in DB2 to minimize API calls and avoid rate limits.
"""
import logging
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

try:
    import pandas_datareader as pdr
    PANDAS_DATAREADER_AVAILABLE = True
except ImportError:
    PANDAS_DATAREADER_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

import pytz

from app import db
from app.models import MarketDataCache, MarketDataMetadata
from app.data import get_stock_info, get_stock_beta

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter to prevent hitting Yahoo Finance API limits.
    Implements exponential backoff on errors.
    """

    def __init__(self, max_per_second: float = 2.0, min_delay: float = 0.5):
        self.max_per_second = max_per_second
        self.min_delay = min_delay
        self.last_request_time = 0
        self.consecutive_errors = 0

    def wait_if_needed(self):
        """Block until rate limit allows next request."""
        elapsed = time.time() - self.last_request_time
        required_delay = max(1.0 / self.max_per_second, self.min_delay)

        if elapsed < required_delay:
            time.sleep(required_delay - elapsed)

        self.last_request_time = time.time()

    def handle_success(self):
        """Reset error counter on success."""
        self.consecutive_errors = 0

    def handle_error(self) -> float:
        """
        Handle an error with exponential backoff.

        Returns:
            Backoff delay in seconds
        """
        self.consecutive_errors += 1
        delay = min(2 ** self.consecutive_errors, 60)  # Max 60 seconds
        logger.warning(f"Rate limit backoff: {delay}s (error #{self.consecutive_errors})")
        time.sleep(delay)
        return delay


class MarketDataService:
    """
    Fetches real market data from Yahoo Finance with DB2 caching.

    Caching Strategy:
    - On first request: fetch full history (configurable years)
    - On subsequent requests: only fetch missing dates
    - Intraday: cache for configured duration during market hours
    - After hours: use last close price
    """

    def __init__(self, cache_hours: int = 24, history_years: int = 5):
        """
        Initialize the market data service.

        Args:
            cache_hours: Hours to cache intraday data
            history_years: Years of history to fetch on first request
        """
        self.cache_hours = cache_hours
        self.history_years = history_years
        self.rate_limiter = RateLimiter()
        self.eastern_tz = pytz.timezone('US/Eastern')

    def is_market_open(self) -> bool:
        """
        Check if NYSE is currently open.

        Market hours: 9:30 AM - 4:00 PM ET, weekdays
        """
        now_et = datetime.now(self.eastern_tz)

        # Check weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5:
            return False

        # Check time
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now_et <= market_close

    def get_last_trading_day(self) -> date:
        """
        Get the most recent trading day (skip weekends).

        Returns:
            Date of last trading day
        """
        today = date.today()

        # If weekend, go back to Friday
        if today.weekday() == 5:  # Saturday
            return today - timedelta(days=1)
        elif today.weekday() == 6:  # Sunday
            return today - timedelta(days=2)

        # If before market open on weekday, use previous day
        now_et = datetime.now(self.eastern_tz)
        if now_et.weekday() < 5 and now_et.hour < 9:
            prev_day = today - timedelta(days=1)
            if prev_day.weekday() == 6:  # Sunday
                return prev_day - timedelta(days=2)
            elif prev_day.weekday() == 5:  # Saturday
                return prev_day - timedelta(days=1)
            return prev_day

        return today

    def _fetch_from_yahoo(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """
        Fetch data from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with OHLCV data or None on error
        """
        self.rate_limiter.wait_if_needed()

        try:
            # Try yfinance first (more reliable)
            if YFINANCE_AVAILABLE:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date + timedelta(days=1))

                if df.empty:
                    logger.warning(f"No data returned from yfinance for {symbol}")
                    return None

                # Rename columns to match our schema
                df = df.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                df['adj_close'] = df['close']  # yfinance returns adjusted by default
                df.index = df.index.date  # Convert to date
                df = df[['open', 'high', 'low', 'close', 'adj_close', 'volume']]

            # Fallback to pandas_datareader
            elif PANDAS_DATAREADER_AVAILABLE:
                df = pdr.DataReader(symbol, 'yahoo', start_date, end_date)

                # Rename columns
                df = df.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Adj Close': 'adj_close',
                    'Volume': 'volume'
                })
                df.index = df.index.date

            else:
                logger.error("No data fetching library available (yfinance or pandas_datareader)")
                return None

            self.rate_limiter.handle_success()
            logger.info(f"Fetched {len(df)} records for {symbol} from Yahoo Finance")
            return df

        except Exception as e:
            logger.error(f"Error fetching {symbol} from Yahoo Finance: {e}")
            self.rate_limiter.handle_error()
            return None

    def _save_to_cache(self, symbol: str, df: pd.DataFrame) -> int:
        """
        Save DataFrame to DB2 cache.

        Args:
            symbol: Stock ticker symbol
            df: DataFrame with OHLCV data

        Returns:
            Number of records saved
        """
        if df is None or df.empty:
            return 0

        records = []
        for idx, row in df.iterrows():
            # idx is the date
            record_date = idx if isinstance(idx, date) else idx.date()

            records.append({
                'symbol': symbol,
                'date': record_date,
                'open': row.get('open'),
                'high': row.get('high'),
                'low': row.get('low'),
                'close': row['close'],
                'adj_close': row['adj_close'],
                'volume': int(row['volume']) if pd.notna(row.get('volume')) else None
            })

        MarketDataCache.bulk_insert(records)
        db.session.commit()

        # Update metadata
        self._update_metadata(symbol)

        return len(records)

    def _update_metadata(self, symbol: str):
        """Update metadata after cache changes."""
        metadata = MarketDataMetadata.get_or_create(symbol)

        # Get date range from cache
        from sqlalchemy import func
        result = db.session.query(
            func.min(MarketDataCache.date),
            func.max(MarketDataCache.date),
            func.count(MarketDataCache.id)
        ).filter(MarketDataCache.symbol == symbol).first()

        if result and result[0]:
            metadata.update_after_fetch(
                earliest=result[0],
                latest=result[1],
                total_records=result[2]
            )
            db.session.commit()

    def _get_cached_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Get data from cache as DataFrame.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with cached data
        """
        records = MarketDataCache.get_price_range(symbol, start_date, end_date)

        if not records:
            return pd.DataFrame()

        data = []
        for r in records:
            data.append({
                'date': r.date,
                'open': float(r.open) if r.open else None,
                'high': float(r.high) if r.high else None,
                'low': float(r.low) if r.low else None,
                'close': float(r.close),
                'adj_close': float(r.adj_close),
                'volume': r.volume
            })

        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        return df

    def _find_missing_ranges(self, symbol: str, start_date: date, end_date: date) -> List[Tuple[date, date]]:
        """
        Find date ranges not in cache.

        Args:
            symbol: Stock ticker symbol
            start_date: Desired start date
            end_date: Desired end date

        Returns:
            List of (start, end) tuples for missing ranges
        """
        metadata = MarketDataMetadata.query.filter_by(symbol=symbol).first()

        if not metadata or not metadata.earliest_date:
            # No data cached, need entire range
            return [(start_date, end_date)]

        missing = []

        # Gap at the beginning?
        if start_date < metadata.earliest_date:
            missing.append((start_date, metadata.earliest_date - timedelta(days=1)))

        # Gap at the end?
        if end_date > metadata.latest_date:
            missing.append((metadata.latest_date + timedelta(days=1), end_date))

        return missing

    def get_price_data(self, symbol: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """
        Get price data for a symbol, fetching from Yahoo Finance if needed.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date (default: history_years ago)
            end_date: End date (default: today)

        Returns:
            DataFrame with OHLCV data
        """
        symbol = symbol.upper()

        if end_date is None:
            end_date = self.get_last_trading_day()

        if start_date is None:
            start_date = end_date - timedelta(days=365 * self.history_years)

        # Find what's missing from cache
        missing_ranges = self._find_missing_ranges(symbol, start_date, end_date)

        # Fetch missing data
        for range_start, range_end in missing_ranges:
            logger.info(f"Fetching {symbol} data for {range_start} to {range_end}")
            df = self._fetch_from_yahoo(symbol, range_start, range_end)
            if df is not None:
                self._save_to_cache(symbol, df)

        # Return combined data from cache
        return self._get_cached_data(symbol, start_date, end_date)

    def get_current_price(self, symbol: str) -> dict:
        """
        Get current price for a symbol.

        Returns dict with price info and source indicator.
        Falls back to simulation if Yahoo Finance unavailable.
        """
        symbol = symbol.upper()

        # Try to get from cache first (for recent data)
        latest = MarketDataCache.get_latest_price(symbol)

        # Check if cache is fresh enough
        if latest and latest.date >= self.get_last_trading_day() - timedelta(days=1):
            return {
                'symbol': symbol,
                'price': float(latest.adj_close),
                'close': float(latest.close),
                'open': float(latest.open) if latest.open else None,
                'high': float(latest.high) if latest.high else None,
                'low': float(latest.low) if latest.low else None,
                'volume': latest.volume,
                'date': latest.date.isoformat(),
                'source': 'cache',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # Try to fetch fresh data
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)  # Fetch last week
            df = self._fetch_from_yahoo(symbol, start_date, end_date)

            if df is not None and not df.empty:
                self._save_to_cache(symbol, df)
                latest_row = df.iloc[-1]
                latest_date = df.index[-1]

                return {
                    'symbol': symbol,
                    'price': float(latest_row['adj_close']),
                    'close': float(latest_row['close']),
                    'open': float(latest_row['open']) if pd.notna(latest_row.get('open')) else None,
                    'high': float(latest_row['high']) if pd.notna(latest_row.get('high')) else None,
                    'low': float(latest_row['low']) if pd.notna(latest_row.get('low')) else None,
                    'volume': int(latest_row['volume']) if pd.notna(latest_row.get('volume')) else None,
                    'date': latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
                    'source': 'yahoo',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.warning(f"Could not fetch current price for {symbol}: {e}")

        # Fall back to simulation
        return self._generate_simulated_price(symbol)

    def _generate_simulated_price(self, symbol: str) -> dict:
        """
        Generate a simulated price as fallback.

        Uses stock universe base price and adds random variation.
        """
        from app.services.price_generator import generate_price

        stock_info = get_stock_info(symbol)
        if stock_info:
            base_price = stock_info['base_price']
            beta = stock_info['beta']
        else:
            base_price = 100.0
            beta = 1.0

        # Generate slightly randomized price
        simulated_price = generate_price(base_price, beta, volatility=0.02)

        return {
            'symbol': symbol,
            'price': simulated_price,
            'close': simulated_price,
            'open': None,
            'high': None,
            'low': None,
            'volume': None,
            'date': date.today().isoformat(),
            'source': 'simulated',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def fetch_multiple_symbols(self, symbols: List[str], start_date: date = None, end_date: date = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols with batching.

        Args:
            symbols: List of stock ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            Dict of {symbol: DataFrame}
        """
        results = {}

        for i, symbol in enumerate(symbols):
            try:
                results[symbol] = self.get_price_data(symbol, start_date, end_date)

                # Add delay between symbols to avoid rate limits
                if i < len(symbols) - 1:
                    time.sleep(1.0)

            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                results[symbol] = pd.DataFrame()

        return results

    def get_cache_status(self, symbol: str) -> dict:
        """Get cache status for a symbol."""
        metadata = MarketDataMetadata.query.filter_by(symbol=symbol.upper()).first()

        if not metadata:
            return {
                'symbol': symbol.upper(),
                'cached': False,
                'earliest_date': None,
                'latest_date': None,
                'total_records': 0,
                'last_updated': None
            }

        return metadata.to_dict()

    def clear_cache(self, symbol: str = None) -> int:
        """
        Clear cache for a symbol or all symbols.

        Returns:
            Number of records deleted
        """
        if symbol:
            symbol = symbol.upper()
            deleted = MarketDataCache.delete_symbol_cache(symbol)
            MarketDataMetadata.delete_metadata(symbol)
        else:
            deleted = MarketDataCache.delete_all_cache()
            MarketDataMetadata.query.delete()

        db.session.commit()
        return deleted

    def refresh_cache(self, symbol: str) -> bool:
        """
        Force refresh cache for a symbol.

        Returns:
            True if refresh successful
        """
        symbol = symbol.upper()
        metadata = MarketDataMetadata.get_or_create(symbol)

        # Fetch from latest cached date to today
        start_date = metadata.latest_date + timedelta(days=1) if metadata.latest_date else date.today() - timedelta(days=365 * self.history_years)
        end_date = date.today()

        if start_date > end_date:
            logger.info(f"Cache for {symbol} is already up to date")
            return True

        df = self._fetch_from_yahoo(symbol, start_date, end_date)
        if df is not None:
            self._save_to_cache(symbol, df)
            return True

        return False


# Singleton instance
_market_data_service = None


def get_market_data_service() -> MarketDataService:
    """Get or create the market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
