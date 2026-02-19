"""
Database Initialization Script

Creates all database tables and initializes the system with:
1. Default portfolio state
2. Stock universe data

Usage:
    python scripts/init_database.py [options]

Options:
    --drop-existing       Drop existing tables before creating (WARNING: data loss)
    --verify-only         Only verify database, do not create or modify

Note: For market data, use the CSV scraper instead:
    python scripts/fetch_yahoo_data.py
"""
import argparse
import sys
import os
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import get_scoped_session, create_all, drop_all, get_engine
from app.config import get_config
from app.models import (
    PortfolioState, Holdings, TradesHistory,
    StrategyCustomization, MarketDataCache, MarketDataMetadata
)
from app.data.strategies import STRATEGIES

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

    # Verify
    verify_database(app)

    print("\n" + "="*60)
    print("Database initialization complete!")
    print("="*60)


if __name__ == '__main__':
    main()
