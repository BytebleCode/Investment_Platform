"""
Yahoo Finance Data Fetcher

Fetches market data from Yahoo Finance and stores it in the database cache.
Can be run as a scheduled job to keep market data up to date.

Usage:
    python scripts/fetch_yahoo_data.py [options]

Options:
    --symbols       Comma-separated list of symbols (default: all in universe)
    --days          Days of history to fetch (default: 30)
    --refresh       Refresh existing data (re-fetch all)
    --missing-only  Only fetch symbols with no cached data
    --batch-size    Number of symbols per batch (default: 10)
    --delay         Delay between batches in seconds (default: 2)

Examples:
    # Fetch last 30 days for all symbols
    python scripts/fetch_yahoo_data.py

    # Fetch specific symbols
    python scripts/fetch_yahoo_data.py --symbols AAPL,MSFT,GOOGL

    # Fetch 1 year of history
    python scripts/fetch_yahoo_data.py --days 365

    # Only fetch symbols not yet in cache
    python scripts/fetch_yahoo_data.py --missing-only
"""
import argparse
import sys
import os
import time
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.config import get_config
from app.models import MarketDataCache, MarketDataMetadata
from app.data.stock_universe import STOCK_UNIVERSE


class YahooDataFetcher:
    """Fetches and caches market data from Yahoo Finance."""

    def __init__(self, app):
        self.app = app
        self.stats = {
            'symbols_processed': 0,
            'symbols_success': 0,
            'symbols_failed': 0,
            'records_added': 0,
            'records_skipped': 0
        }

    def fetch_symbol(self, symbol: str, start_date: date, end_date: date,
                     refresh: bool = False) -> bool:
        """
        Fetch data for a single symbol.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for data fetch
            end_date: End date for data fetch
            refresh: If True, re-fetch existing data

        Returns:
            True if successful, False otherwise
        """
        try:
            import yfinance as yf
        except ImportError:
            print("ERROR: yfinance not installed. Run: pip install yfinance")
            return False

        try:
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  No data returned for {symbol}")
                return False

            records_added = 0
            records_skipped = 0

            with self.app.app_context():
                for idx, row in hist.iterrows():
                    trade_date = idx.date()

                    # Check if exists
                    if not refresh:
                        existing = MarketDataCache.query.filter_by(
                            symbol=symbol,
                            date=trade_date
                        ).first()

                        if existing:
                            records_skipped += 1
                            continue
                    else:
                        # Delete existing for refresh
                        MarketDataCache.query.filter_by(
                            symbol=symbol,
                            date=trade_date
                        ).delete()

                    # Insert new record
                    cache_entry = MarketDataCache(
                        symbol=symbol,
                        date=trade_date,
                        open=Decimal(str(row['Open'])),
                        high=Decimal(str(row['High'])),
                        low=Decimal(str(row['Low'])),
                        close=Decimal(str(row['Close'])),
                        adj_close=Decimal(str(row['Close'])),
                        volume=int(row['Volume']),
                        fetched_at=datetime.now()
                    )
                    db.session.add(cache_entry)
                    records_added += 1

                # Update metadata
                self._update_metadata(symbol, hist)

                db.session.commit()

            self.stats['records_added'] += records_added
            self.stats['records_skipped'] += records_skipped

            print(f"  {symbol}: +{records_added} records ({records_skipped} skipped)")
            return True

        except Exception as e:
            print(f"  {symbol}: ERROR - {e}")
            with self.app.app_context():
                db.session.rollback()
            return False

    def _update_metadata(self, symbol: str, hist):
        """Update market data metadata after fetch."""
        metadata = MarketDataMetadata.query.filter_by(symbol=symbol).first()

        total_records = MarketDataCache.query.filter_by(symbol=symbol).count()
        earliest = MarketDataCache.query.filter_by(symbol=symbol).order_by(
            MarketDataCache.date.asc()
        ).first()
        latest = MarketDataCache.query.filter_by(symbol=symbol).order_by(
            MarketDataCache.date.desc()
        ).first()

        if metadata:
            metadata.last_fetch_date = date.today()
            metadata.total_records = total_records
            if earliest:
                metadata.earliest_date = earliest.date
            if latest:
                metadata.latest_date = latest.date
            metadata.fetch_status = 'complete'
            metadata.last_updated = datetime.now()
        else:
            metadata = MarketDataMetadata(
                symbol=symbol,
                last_fetch_date=date.today(),
                earliest_date=earliest.date if earliest else None,
                latest_date=latest.date if latest else None,
                total_records=total_records,
                fetch_status='complete'
            )
            db.session.add(metadata)

    def fetch_batch(self, symbols: list, start_date: date, end_date: date,
                    refresh: bool = False, delay: float = 2.0):
        """
        Fetch data for multiple symbols with rate limiting.

        Args:
            symbols: List of symbols to fetch
            start_date: Start date
            end_date: End date
            refresh: Refresh existing data
            delay: Delay between symbols (seconds)
        """
        print(f"\nFetching {len(symbols)} symbols...")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Refresh mode: {'ON' if refresh else 'OFF'}")
        print("-" * 50)

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")

            self.stats['symbols_processed'] += 1

            if self.fetch_symbol(symbol, start_date, end_date, refresh):
                self.stats['symbols_success'] += 1
            else:
                self.stats['symbols_failed'] += 1

            # Rate limiting delay (except for last symbol)
            if i < len(symbols) and delay > 0:
                time.sleep(delay)

    def get_missing_symbols(self) -> list:
        """Get symbols that have no cached data."""
        all_symbols = set(STOCK_UNIVERSE.keys())

        with self.app.app_context():
            cached_symbols = set(
                m.symbol for m in MarketDataMetadata.query.all()
                if m.total_records and m.total_records > 0
            )

        return list(all_symbols - cached_symbols)

    def get_stale_symbols(self, max_age_days: int = 1) -> list:
        """Get symbols with stale data (older than max_age_days)."""
        cutoff_date = date.today() - timedelta(days=max_age_days)

        with self.app.app_context():
            stale = MarketDataMetadata.query.filter(
                MarketDataMetadata.last_fetch_date < cutoff_date
            ).all()
            return [m.symbol for m in stale]

    def print_stats(self):
        """Print fetch statistics."""
        print("\n" + "=" * 50)
        print("Fetch Statistics")
        print("=" * 50)
        print(f"Symbols Processed: {self.stats['symbols_processed']}")
        print(f"Successful:        {self.stats['symbols_success']}")
        print(f"Failed:            {self.stats['symbols_failed']}")
        print(f"Records Added:     {self.stats['records_added']}")
        print(f"Records Skipped:   {self.stats['records_skipped']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch market data from Yahoo Finance'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated list of symbols (default: all)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Days of history to fetch (default: 30)'
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Refresh existing data'
    )
    parser.add_argument(
        '--missing-only',
        action='store_true',
        help='Only fetch symbols with no cached data'
    )
    parser.add_argument(
        '--stale-only',
        action='store_true',
        help='Only fetch symbols with stale data'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Symbols per batch (default: 10)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between symbols in seconds (default: 2)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show cache status and exit'
    )

    args = parser.parse_args()

    # Create Flask app
    config = get_config()
    app = create_app(config)

    fetcher = YahooDataFetcher(app)

    # Status only mode
    if args.status:
        print("\n" + "=" * 60)
        print("Market Data Cache Status")
        print("=" * 60)

        with app.app_context():
            total_records = MarketDataCache.query.count()
            total_symbols = MarketDataMetadata.query.count()

            print(f"\nTotal Records: {total_records:,}")
            print(f"Total Symbols: {total_symbols}")

            print("\nSymbol Details:")
            for meta in MarketDataMetadata.query.order_by(MarketDataMetadata.symbol).all():
                print(f"  {meta.symbol}: {meta.total_records or 0} records "
                      f"({meta.earliest_date} to {meta.latest_date}) "
                      f"[last fetch: {meta.last_fetch_date}]")

            missing = fetcher.get_missing_symbols()
            if missing:
                print(f"\nMissing symbols ({len(missing)}): {', '.join(sorted(missing)[:20])}")
                if len(missing) > 20:
                    print(f"  ... and {len(missing) - 20} more")

        return

    # Determine symbols to fetch
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    elif args.missing_only:
        symbols = fetcher.get_missing_symbols()
        if not symbols:
            print("No missing symbols. Cache is complete!")
            return
        print(f"Found {len(symbols)} missing symbols")
    elif args.stale_only:
        symbols = fetcher.get_stale_symbols()
        if not symbols:
            print("No stale symbols. Cache is up to date!")
            return
        print(f"Found {len(symbols)} stale symbols")
    else:
        symbols = list(STOCK_UNIVERSE.keys())

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)

    print("\n" + "=" * 60)
    print("Yahoo Finance Data Fetcher")
    print("=" * 60)
    print(f"Symbols: {len(symbols)}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Delay: {args.delay}s between requests")

    # Fetch data
    fetcher.fetch_batch(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        refresh=args.refresh,
        delay=args.delay
    )

    # Print stats
    fetcher.print_stats()

    print("\nDone!")


if __name__ == '__main__':
    main()
