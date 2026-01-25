"""
Pytest Configuration and Fixtures

Provides shared fixtures for all tests including:
- Flask test client
- Database session with automatic cleanup
- Mock data generators
"""
import os
import sys
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.config import TestingConfig
from app.models import (
    PortfolioState, Holdings, TradesHistory,
    StrategyCustomization, MarketDataCache, MarketDataMetadata
)


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    application = create_app(TestingConfig)

    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client for API testing."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session with automatic cleanup."""
    with app.app_context():
        # Clear all tables before each test
        db.session.query(TradesHistory).delete()
        db.session.query(Holdings).delete()
        db.session.query(StrategyCustomization).delete()
        db.session.query(MarketDataCache).delete()
        db.session.query(MarketDataMetadata).delete()
        db.session.query(PortfolioState).delete()
        db.session.commit()

        yield db.session

        # Cleanup after test
        db.session.rollback()


@pytest.fixture
def sample_portfolio(db_session):
    """Create a sample portfolio for testing."""
    portfolio = PortfolioState(
        user_id='test_user',
        initial_value=Decimal('100000.00'),
        current_cash=Decimal('50000.00'),
        current_strategy='balanced',
        is_initialized=True,
        realized_gains=Decimal('1000.00')
    )
    db_session.add(portfolio)
    db_session.commit()
    return portfolio


@pytest.fixture
def sample_holdings(db_session, sample_portfolio):
    """Create sample holdings for testing."""
    holdings = [
        Holdings(
            user_id='test_user',
            symbol='AAPL',
            name='Apple Inc.',
            sector='Technology',
            quantity=Decimal('100'),
            avg_cost=Decimal('150.00')
        ),
        Holdings(
            user_id='test_user',
            symbol='MSFT',
            name='Microsoft Corporation',
            sector='Technology',
            quantity=Decimal('50'),
            avg_cost=Decimal('300.00')
        ),
        Holdings(
            user_id='test_user',
            symbol='JNJ',
            name='Johnson & Johnson',
            sector='Healthcare',
            quantity=Decimal('75'),
            avg_cost=Decimal('160.00')
        )
    ]
    for holding in holdings:
        db_session.add(holding)
    db_session.commit()
    return holdings


@pytest.fixture
def sample_trades(db_session, sample_portfolio):
    """Create sample trade history for testing."""
    trades = [
        TradesHistory(
            user_id='test_user',
            trade_id='trade-001',
            timestamp=datetime.now() - timedelta(days=5),
            type='buy',
            symbol='AAPL',
            stock_name='Apple Inc.',
            sector='Technology',
            quantity=100,
            price=Decimal('150.00'),
            total=Decimal('15000.00'),
            fees=Decimal('15.00'),
            strategy='balanced'
        ),
        TradesHistory(
            user_id='test_user',
            trade_id='trade-002',
            timestamp=datetime.now() - timedelta(days=3),
            type='buy',
            symbol='MSFT',
            stock_name='Microsoft Corporation',
            sector='Technology',
            quantity=50,
            price=Decimal('300.00'),
            total=Decimal('15000.00'),
            fees=Decimal('15.00'),
            strategy='balanced'
        ),
        TradesHistory(
            user_id='test_user',
            trade_id='trade-003',
            timestamp=datetime.now() - timedelta(days=1),
            type='sell',
            symbol='AAPL',
            stock_name='Apple Inc.',
            sector='Technology',
            quantity=20,
            price=Decimal('155.00'),
            total=Decimal('3100.00'),
            fees=Decimal('3.10'),
            strategy='balanced'
        )
    ]
    for trade in trades:
        db_session.add(trade)
    db_session.commit()
    return trades


@pytest.fixture
def sample_strategy_customization(db_session, sample_portfolio):
    """Create sample strategy customization for testing."""
    customization = StrategyCustomization(
        user_id='test_user',
        strategy_id='balanced',
        confidence_level=75,
        trade_frequency='medium',
        max_position_size=15,
        stop_loss_percent=10,
        take_profit_percent=25,
        auto_rebalance=True,
        reinvest_dividends=True
    )
    db_session.add(customization)
    db_session.commit()
    return customization


@pytest.fixture
def sample_market_data(db_session):
    """Create sample market data cache for testing."""
    base_date = date.today() - timedelta(days=30)
    cache_entries = []

    for i in range(30):
        current_date = base_date + timedelta(days=i)
        # Skip weekends
        if current_date.weekday() >= 5:
            continue

        entry = MarketDataCache(
            symbol='AAPL',
            date=current_date,
            open=Decimal('150.00') + Decimal(str(i * 0.5)),
            high=Decimal('152.00') + Decimal(str(i * 0.5)),
            low=Decimal('148.00') + Decimal(str(i * 0.5)),
            close=Decimal('151.00') + Decimal(str(i * 0.5)),
            adj_close=Decimal('151.00') + Decimal(str(i * 0.5)),
            volume=1000000 + i * 10000,
            fetched_at=datetime.now()
        )
        cache_entries.append(entry)
        db_session.add(entry)

    # Add metadata
    metadata = MarketDataMetadata(
        symbol='AAPL',
        last_fetch_date=date.today(),
        earliest_date=base_date,
        latest_date=date.today() - timedelta(days=1),
        total_records=len(cache_entries),
        fetch_status='complete'
    )
    db_session.add(metadata)
    db_session.commit()

    return cache_entries


@pytest.fixture
def mock_yahoo_finance():
    """Mock Yahoo Finance API responses."""
    import pandas as pd
    import numpy as np

    def create_mock_data(symbol, start_date, end_date):
        """Generate mock OHLCV data."""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        n = len(dates)

        base_price = 150.0
        prices = base_price + np.cumsum(np.random.randn(n) * 2)

        return pd.DataFrame({
            'Open': prices - np.random.rand(n),
            'High': prices + np.random.rand(n) * 2,
            'Low': prices - np.random.rand(n) * 2,
            'Close': prices,
            'Adj Close': prices,
            'Volume': np.random.randint(1000000, 5000000, n)
        }, index=dates)

    with patch('yfinance.download') as mock_download:
        mock_download.side_effect = create_mock_data
        yield mock_download


@pytest.fixture
def current_prices():
    """Return mock current prices for testing."""
    return {
        'AAPL': Decimal('155.00'),
        'MSFT': Decimal('310.00'),
        'GOOGL': Decimal('140.00'),
        'JNJ': Decimal('165.00'),
        'PG': Decimal('155.00'),
        'KO': Decimal('62.00'),
        'JPM': Decimal('175.00'),
        'BAC': Decimal('35.00'),
        'COIN': Decimal('250.00'),
        'TSLA': Decimal('245.00')
    }


# Helper functions for tests

def create_test_portfolio(db_session, user_id='test_user', cash=Decimal('100000')):
    """Helper to create a test portfolio."""
    portfolio = PortfolioState(
        user_id=user_id,
        initial_value=Decimal('100000.00'),
        current_cash=cash,
        current_strategy='balanced',
        is_initialized=True,
        realized_gains=Decimal('0')
    )
    db_session.add(portfolio)
    db_session.commit()
    return portfolio


def create_test_holding(db_session, user_id='test_user', symbol='AAPL',
                        quantity=100, avg_cost=Decimal('150')):
    """Helper to create a test holding."""
    holding = Holdings(
        user_id=user_id,
        symbol=symbol,
        name=f'{symbol} Inc.',
        sector='Technology',
        quantity=Decimal(str(quantity)),
        avg_cost=avg_cost
    )
    db_session.add(holding)
    db_session.commit()
    return holding
