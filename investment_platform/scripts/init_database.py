"""
Database Initialization Script

Creates all database tables and initializes the system with:
1. Default portfolio state
2. Stock universe data
3. Initial market data from Yahoo Finance

Usage:
    python scripts/init_database.py [--with-market-data] [--symbols AAPL,MSFT,...]

Options:
    --with-market-data    Fetch and cache historical market data from Yahoo Finance
    --symbols             Comma-separated list of symbols to fetch (default: all in universe)
    --days                Number of days of history to fetch (default: 365)
    --drop-existing       Drop existing tables before creating (WARNING: data loss)
"""
import argparse
import sys
import os
from datetime import datetime, date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import get_scoped_session, create_all, drop_all, get_engine
from app.config import get_config
from app.models import (
    PortfolioState, Holdings, TradesHistory,
    StrategyCustomization, MarketDataCache, MarketDataMetadata
)
from app.data.stock_universe import STOCK_UNIVERSE
from app.data.strategies import STRATEGIES

try:
    import pandas_datareader as pdr
    PANDAS_DATAREADER_AVAILABLE = True
except ImportError:
    PANDAS_DATAREADER_AVAILABLE = False


def create_tables(app, drop_existing=False):
    """
    Create all database tables.

    Args:
        app: Flask application instance
        drop_existing: If True, drop existing tables first
    """
    with app.app_context():
        if drop_existing:
            print("WARNING: Dropping existing tables...")
            drop_all()
            print("Tables dropped.")

        print("Creating database tables...")
        create_all()
        print("Tables created successfully!")

        # List created tables
        from sqlalchemy import inspect
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTables in database: {tables}")


def init_default_portfolio(app, user_id='default'):
    """
    Initialize a default portfolio if none exists.

    Args:
        app: Flask application instance
        user_id: User ID for the portfolio
    """
    with app.app_context():
        session = get_scoped_session()
        existing = session.query(PortfolioState).filter_by(user_id=user_id).first()

        if existing:
            print(f"Portfolio already exists for user '{user_id}'")
            return existing

        print(f"Creating default portfolio for user '{user_id}'...")
        portfolio = PortfolioState(
            user_id=user_id,
            initial_value=100000.00,
            current_cash=100000.00,
            current_strategy='balanced',
            is_initialized=False,
            realized_gains=0
        )
        session.add(portfolio)
        session.commit()
        print(f"Portfolio created with ${portfolio.initial_value:,.2f} initial value")
        return portfolio


def init_strategy_customizations(app, user_id='default'):
    """
    Initialize default strategy customizations.

    Args:
        app: Flask application instance
        user_id: User ID
    """
    with app.app_context():
        print("Initializing strategy customizations...")
        session = get_scoped_session()

        for strategy_id in STRATEGIES.keys():
            existing = session.query(StrategyCustomization).filter_by(
                user_id=user_id,
                strategy_id=strategy_id
            ).first()

            if existing:
                print(f"  {strategy_id}: already exists")
                continue

            customization = StrategyCustomization(
                user_id=user_id,
                strategy_id=strategy_id,
                confidence_level=50,
                trade_frequency='medium',
                max_position_size=15,
                stop_loss_percent=10,
                take_profit_percent=20,
                auto_rebalance=True,
                reinvest_dividends=True
            )
            session.add(customization)
            print(f"  {strategy_id}: created")

        session.commit()
        print("Strategy customizations initialized!")


def fetch_market_data(app, symbols=None, days=365):
    """
    Fetch historical market data from Yahoo Finance via pandas_datareader.

    Args:
        app: Flask application instance
        symbols: List of symbols to fetch (None = all in universe)
        days: Number of days of history to fetch
    """
    if not PANDAS_DATAREADER_AVAILABLE:
        print("ERROR: pandas_datareader not installed. Run: pip install pandas-datareader")
        return

    if symbols is None:
        symbols = list(STOCK_UNIVERSE.keys())

    print(f"\nFetching market data for {len(symbols)} symbols...")
    print(f"History: {days} days")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with app.app_context():
        session = get_scoped_session()
        success_count = 0
        error_count = 0

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Fetching {symbol}...", end=" ")

            try:
                # Fetch data from Yahoo Finance via pandas_datareader
                hist = pdr.DataReader(symbol, 'yahoo', start_date, end_date)

                if hist.empty:
                    print("No data available")
                    error_count += 1
                    continue

                # Store in database
                records_added = 0
                for idx, row in hist.iterrows():
                    trade_date = idx.date()

                    # Check if already exists
                    existing = session.query(MarketDataCache).filter_by(
                        symbol=symbol,
                        date=trade_date
                    ).first()

                    if existing:
                        continue

                    cache_entry = MarketDataCache(
                        symbol=symbol,
                        date=trade_date,
                        open=row['Open'],
                        high=row['High'],
                        low=row['Low'],
                        close=row['Close'],
                        adj_close=row['Adj Close'],
                        volume=int(row['Volume']),
                        fetched_at=datetime.now()
                    )
                    session.add(cache_entry)
                    records_added += 1

                # Update metadata
                metadata = session.query(MarketDataMetadata).filter_by(symbol=symbol).first()
                if metadata:
                    metadata.last_fetch_date = date.today()
                    metadata.latest_date = hist.index[-1].date()
                    if metadata.earliest_date is None or hist.index[0].date() < metadata.earliest_date:
                        metadata.earliest_date = hist.index[0].date()
                    metadata.total_records = session.query(MarketDataCache).filter_by(symbol=symbol).count() + records_added
                    metadata.fetch_status = 'complete'
                else:
                    metadata = MarketDataMetadata(
                        symbol=symbol,
                        last_fetch_date=date.today(),
                        earliest_date=hist.index[0].date(),
                        latest_date=hist.index[-1].date(),
                        total_records=records_added,
                        fetch_status='complete'
                    )
                    session.add(metadata)

                session.commit()
                print(f"OK ({records_added} new records)")
                success_count += 1

            except Exception as e:
                print(f"ERROR: {e}")
                error_count += 1
                session.rollback()

        print(f"\n{'='*50}")
        print(f"Market Data Fetch Complete")
        print(f"{'='*50}")
        print(f"Successful: {success_count}")
        print(f"Errors:     {error_count}")
        print(f"Total records in cache: {session.query(MarketDataCache).count()}")


def verify_database(app):
    """
    Verify database is properly initialized.

    Args:
        app: Flask application instance
    """
    print("\n" + "="*50)
    print("Database Verification")
    print("="*50)

    with app.app_context():
        # Check tables exist
        from sqlalchemy import inspect
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'portfolio_state', 'holdings', 'trades_history',
            'strategy_customizations', 'market_data_cache', 'market_data_metadata'
        ]

        print("\nTable Status:")
        for table in expected_tables:
            status = "OK" if table in tables else "MISSING"
            print(f"  {table}: {status}")

        # Check record counts
        session = get_scoped_session()
        print("\nRecord Counts:")
        print(f"  Portfolios: {session.query(PortfolioState).count()}")
        print(f"  Holdings: {session.query(Holdings).count()}")
        print(f"  Trades: {session.query(TradesHistory).count()}")
        print(f"  Strategy Customizations: {session.query(StrategyCustomization).count()}")
        print(f"  Market Data Cache: {session.query(MarketDataCache).count()}")
        print(f"  Market Data Metadata: {session.query(MarketDataMetadata).count()}")

        # Check market data coverage
        if session.query(MarketDataMetadata).count() > 0:
            print("\nMarket Data Coverage:")
            for meta in session.query(MarketDataMetadata).limit(10).all():
                print(f"  {meta.symbol}: {meta.total_records} records "
                      f"({meta.earliest_date} to {meta.latest_date})")

            remaining = session.query(MarketDataMetadata).count() - 10
            if remaining > 0:
                print(f"  ... and {remaining} more symbols")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Initialize Investment Platform database'
    )
    parser.add_argument(
        '--with-market-data',
        action='store_true',
        help='Fetch historical market data from Yahoo Finance'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated list of symbols to fetch (default: all)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days of history to fetch (default: 365)'
    )
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing tables before creating (WARNING: data loss)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify database, do not create or modify'
    )

    args = parser.parse_args()

    # Create Flask app
    config = get_config()
    app = create_app(config)

    print("\n" + "="*60)
    print("Investment Platform - Database Initialization")
    print("="*60)
    print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")

    if args.verify_only:
        verify_database(app)
        return

    # Create tables
    create_tables(app, drop_existing=args.drop_existing)

    # Initialize default data
    init_default_portfolio(app)
    init_strategy_customizations(app)

    # Fetch market data if requested
    if args.with_market_data:
        symbols = args.symbols.split(',') if args.symbols else None
        fetch_market_data(app, symbols=symbols, days=args.days)

    # Verify
    verify_database(app)

    print("\n" + "="*60)
    print("Database initialization complete!")
    print("="*60)


if __name__ == '__main__':
    main()
