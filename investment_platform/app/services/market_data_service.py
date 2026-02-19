"""
Market Data Service

Fetches real market data from local CSV files.
Prioritizes local CSV files in data/tickercsv folder for faster access.
"""
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import pytz

from app.database import get_scoped_session, is_csv_backend, get_csv_storage
from app.models import MarketDataCache, MarketDataMetadata
from app.data import get_stock_info, get_stock_beta

logger = logging.getLogger(__name__)

# Path to local ticker CSV files
TICKER_CSV_DIR = Path(__file__).parent.parent.parent / 'data' / 'tickercsv'
SYMBOLS_LIST_FILE = TICKER_CSV_DIR / 'symbols_filtered.csv'


def get_available_symbols_from_list() -> list:
    """Load available symbols from symbols_filtered.csv."""
    if not SYMBOLS_LIST_FILE.exists():
        return []

    try:
        with open(SYMBOLS_LIST_FILE, 'r') as f:
            symbols = [line.strip() for line in f if line.strip()]
        return symbols
    except Exception as e:
        logger.error(f"Error reading symbols list: {e}")
        return []


class MarketDataService:
    """
    Fetches real market data from local CSV files.

    Priority:
    1. Local CSV files in data/tickercsv folder
    2. Cached data in database/CSV storage
    """

    def __init__(self, cache_hours: int = 24, history_years: int = 5):
        self.cache_hours = cache_hours
        self.history_years = history_years
        self.eastern_tz = pytz.timezone('US/Eastern')
        self._local_csv_cache = {}  # Cache loaded CSV data in memory

    def is_market_open(self) -> bool:
        """Check if NYSE is currently open."""
        now_et = datetime.now(self.eastern_tz)
        if now_et.weekday() >= 5:
            return False
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now_et <= market_close

    def get_last_trading_day(self) -> date:
        """Get the most recent trading day (skip weekends)."""
        today = date.today()
        if today.weekday() == 5:
            return today - timedelta(days=1)
        elif today.weekday() == 6:
            return today - timedelta(days=2)

        now_et = datetime.now(self.eastern_tz)
        if now_et.weekday() < 5 and now_et.hour < 9:
            prev_day = today - timedelta(days=1)
            if prev_day.weekday() == 6:
                return prev_day - timedelta(days=2)
            elif prev_day.weekday() == 5:
                return prev_day - timedelta(days=1)
            return prev_day

        return today

    def _get_csv_filename(self, symbol: str) -> Optional[Path]:
        """Get the CSV file path for a symbol."""
        symbol_upper = symbol.upper()

        # Try different filename patterns
        patterns = [
            f"{symbol_upper}.csv",                              # Direct match: AAPL.csv
            f"{symbol_upper.replace('.', '_')}.csv",            # Dot to underscore: BRK.B -> BRK_B.csv
            f"{symbol_upper.replace('-', '')}.csv",             # Remove dash: BTC-USD -> BTCUSD.csv
            f"{symbol_upper.replace('-USD', '')}.csv",          # Crypto: BTC-USD -> BTC.csv
            f"_{symbol_upper.replace('^', '')}.csv",            # Index: ^GSPC -> _GSPC.csv
            f"{symbol_upper.replace('^', '')}.csv",             # Index alt: ^GSPC -> GSPC.csv
        ]

        for pattern in patterns:
            filepath = TICKER_CSV_DIR / pattern
            if filepath.exists():
                return filepath

        return None

    def _load_from_local_csv(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Load data from local CSV file.

        Supports CSV format with columns:
        Date,Open,High,Low,Close,Volume,Dividends,Stock Splits
        Date format: 2021-01-25 00:00:00-05:00 (with timezone)

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFrame with OHLCV data or None if file doesn't exist
        """
        # Check memory cache first
        symbol_upper = symbol.upper()
        if symbol_upper in self._local_csv_cache:
            logger.debug(f"Using memory-cached data for {symbol_upper}")
            return self._local_csv_cache[symbol_upper].copy()

        filepath = self._get_csv_filename(symbol)
        if not filepath:
            return None

        try:
            df = pd.read_csv(filepath)

            # Standardize column names to lowercase
            df.columns = df.columns.str.lower().str.strip()

            # Parse date column - handles timezone-aware dates like "2021-01-25 00:00:00-05:00"
            if 'date' in df.columns:
                # Parse datetime with timezone, then extract just the date
                df['date'] = pd.to_datetime(df['date'], utc=True).dt.date
                df.set_index('date', inplace=True)

            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} in {filepath}")
                    return None

            # Add adj_close if not present (use close)
            if 'adj_close' not in df.columns:
                df['adj_close'] = df['close']

            # Select only needed columns (ignore dividends, stock splits, etc.)
            df = df[['open', 'high', 'low', 'close', 'adj_close', 'volume']]

            # Sort by date
            df.sort_index(inplace=True)

            # Cache in memory
            self._local_csv_cache[symbol_upper] = df.copy()

            logger.info(f"Loaded {len(df)} records for {symbol} from local CSV: {filepath.name}")
            return df

        except Exception as e:
            logger.error(f"Error loading CSV for {symbol}: {e}")
            return None

    def _save_to_cache(self, symbol: str, df: pd.DataFrame) -> int:
        """Save DataFrame to cache."""
        if df is None or df.empty:
            return 0

        records = []
        for idx, row in df.iterrows():
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
        session = get_scoped_session()
        session.commit()
        self._update_metadata(symbol)
        return len(records)

    def _update_metadata(self, symbol: str):
        """Update metadata after cache changes."""
        if is_csv_backend():
            storage = get_csv_storage()
            data = storage.get_market_data(symbol)
            if data:
                dates = [d.get('date') for d in data if d.get('date')]
                if dates:
                    storage.update_market_metadata(
                        symbol,
                        earliest_date=min(dates),
                        latest_date=max(dates),
                        total_records=len(data),
                        fetch_status='complete'
                    )
            return

        metadata = MarketDataMetadata.get_or_create(symbol)
        from sqlalchemy import func
        session = get_scoped_session()
        result = session.query(
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
            session.commit()

    def _get_cached_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Get data from cache as DataFrame."""
        records = MarketDataCache.get_price_range(symbol, start_date, end_date)

        if not records:
            return pd.DataFrame()

        data = []
        for r in records:
            if isinstance(r, dict):
                data.append({
                    'date': r.get('date'),
                    'open': float(r.get('open')) if r.get('open') else None,
                    'high': float(r.get('high')) if r.get('high') else None,
                    'low': float(r.get('low')) if r.get('low') else None,
                    'close': float(r.get('close')),
                    'adj_close': float(r.get('adj_close')),
                    'volume': r.get('volume')
                })
            else:
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

    def get_price_data(self, symbol: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """
        Get price data for a symbol.

        Priority:
        1. Local CSV files
        2. Database cache
        3. Yahoo Finance
        """
        symbol = symbol.upper()

        if end_date is None:
            end_date = self.get_last_trading_day()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * self.history_years)

        # Try local CSV first
        local_df = self._load_from_local_csv(symbol)
        if local_df is not None and not local_df.empty:
            # Filter by date range
            filtered = local_df[(local_df.index >= start_date) & (local_df.index <= end_date)]
            if not filtered.empty:
                return filtered

        # Try cache
        cached_df = self._get_cached_data(symbol, start_date, end_date)
        if not cached_df.empty:
            return cached_df

        logger.warning(f"No local data available for {symbol}")
        return pd.DataFrame()

    def get_current_price(self, symbol: str) -> dict:
        """
        Get current/latest price for a symbol.

        Priority:
        1. Local CSV files (latest entry)
        2. Database cache
        3. Yahoo Finance
        """
        symbol = symbol.upper()

        # Try local CSV first
        local_df = self._load_from_local_csv(symbol)
        if local_df is not None and not local_df.empty:
            latest_date = local_df.index[-1]
            latest_row = local_df.iloc[-1]
            return {
                'symbol': symbol,
                'price': float(latest_row['adj_close']) if pd.notna(latest_row['adj_close']) else float(latest_row['close']),
                'close': float(latest_row['close']),
                'open': float(latest_row['open']) if pd.notna(latest_row.get('open')) else None,
                'high': float(latest_row['high']) if pd.notna(latest_row.get('high')) else None,
                'low': float(latest_row['low']) if pd.notna(latest_row.get('low')) else None,
                'volume': int(latest_row['volume']) if pd.notna(latest_row.get('volume')) else None,
                'date': latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
                'source': 'local_csv',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # Try cache
        latest = MarketDataCache.get_latest_price(symbol)
        if latest:
            if isinstance(latest, dict):
                latest_date = latest.get('date')
                adj_close = latest.get('adj_close')
                close = latest.get('close')
                open_price = latest.get('open')
                high = latest.get('high')
                low = latest.get('low')
                volume = latest.get('volume')
            else:
                latest_date = latest.date
                adj_close = latest.adj_close
                close = latest.close
                open_price = latest.open
                high = latest.high
                low = latest.low
                volume = latest.volume

            if latest_date:
                return {
                    'symbol': symbol,
                    'price': float(adj_close) if adj_close else 0,
                    'close': float(close) if close else 0,
                    'open': float(open_price) if open_price else None,
                    'high': float(high) if high else None,
                    'low': float(low) if low else None,
                    'volume': volume,
                    'date': latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
                    'source': 'cache',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

        return {
            'symbol': symbol,
            'price': None,
            'close': None,
            'open': None,
            'high': None,
            'low': None,
            'volume': None,
            'date': None,
            'source': 'unavailable',
            'error': f'No market data available for {symbol}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def fetch_multiple_symbols(self, symbols: List[str], start_date: date = None, end_date: date = None) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols."""
        results = {}
        for i, symbol in enumerate(symbols):
            try:
                results[symbol] = self.get_price_data(symbol, start_date, end_date)
                if i < len(symbols) - 1:
                    time.sleep(0.1)  # Reduced delay since we're using local files
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                results[symbol] = pd.DataFrame()
        return results

    def get_cache_status(self, symbol: str) -> dict:
        """Get cache status for a symbol."""
        symbol_upper = symbol.upper()

        # Check local CSV
        csv_path = self._get_csv_filename(symbol)
        if csv_path:
            local_df = self._load_from_local_csv(symbol)
            if local_df is not None and not local_df.empty:
                return {
                    'symbol': symbol_upper,
                    'cached': True,
                    'source': 'local_csv',
                    'file': csv_path.name,
                    'earliest_date': str(local_df.index[0]),
                    'latest_date': str(local_df.index[-1]),
                    'total_records': len(local_df),
                    'last_updated': None
                }

        session = get_scoped_session()
        metadata = session.query(MarketDataMetadata).filter_by(symbol=symbol_upper).first()

        if not metadata:
            return {
                'symbol': symbol_upper,
                'cached': False,
                'earliest_date': None,
                'latest_date': None,
                'total_records': 0,
                'last_updated': None
            }

        return metadata.to_dict()

    def clear_cache(self, symbol: str = None) -> int:
        """Clear cache for a symbol or all symbols."""
        # Clear memory cache
        if symbol:
            symbol = symbol.upper()
            self._local_csv_cache.pop(symbol, None)
            deleted = MarketDataCache.delete_symbol_cache(symbol)
            MarketDataMetadata.delete_metadata(symbol)
        else:
            self._local_csv_cache.clear()
            deleted = MarketDataCache.delete_all_cache()
            session = get_scoped_session()
            session.query(MarketDataMetadata).delete()

        session = get_scoped_session()
        session.commit()
        return deleted

    def refresh_cache(self, symbol: str) -> bool:
        """Force refresh cache for a symbol."""
        symbol = symbol.upper()

        # Clear memory cache to force reload
        self._local_csv_cache.pop(symbol, None)

        # Try local CSV
        local_df = self._load_from_local_csv(symbol)
        if local_df is not None and not local_df.empty:
            return True

        return False

    def list_available_symbols(self) -> List[str]:
        """List all symbols available in local CSV files."""
        if not TICKER_CSV_DIR.exists():
            return []

        symbols = set()

        # Get symbols from actual CSV files
        for f in TICKER_CSV_DIR.glob('*.csv'):
            if f.name == 'symbols_filtered.csv':
                continue  # Skip the symbols list file
            symbol = f.stem.upper()
            # Clean up symbol name
            if symbol.startswith('_'):
                symbol = '^' + symbol[1:]  # _GSPC -> ^GSPC
            symbols.add(symbol)

        return sorted(symbols)

    def list_expected_symbols(self) -> List[str]:
        """List all symbols from symbols_filtered.csv (expected to be available)."""
        return get_available_symbols_from_list()


# Singleton instance
_market_data_service = None


def get_market_data_service() -> MarketDataService:
    """Get or create the market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
