"""
Unit Tests for Database Models

Tests all SQLAlchemy models for correct behavior and constraints.
"""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError

from app.models import (
    PortfolioState, Holdings, TradesHistory,
    StrategyCustomization, MarketDataCache, MarketDataMetadata
)


class TestPortfolioStateModel:
    """Tests for PortfolioState model."""

    def test_create_portfolio(self, db_session):
        """Test creating a new portfolio."""
        portfolio = PortfolioState(
            user_id='new_user',
            initial_value=Decimal('100000.00'),
            current_cash=Decimal('100000.00'),
            current_strategy='balanced'
        )
        db_session.add(portfolio)
        db_session.commit()

        assert portfolio.id is not None
        assert portfolio.user_id == 'new_user'
        assert portfolio.initial_value == Decimal('100000.00')
        assert portfolio.is_initialized == False
        assert portfolio.realized_gains == Decimal('0')

    def test_portfolio_defaults(self, db_session):
        """Test default values are applied."""
        portfolio = PortfolioState(user_id='default_test')
        db_session.add(portfolio)
        db_session.commit()

        assert portfolio.initial_value == Decimal('100000.00')
        assert portfolio.current_cash == Decimal('100000.00')
        assert portfolio.current_strategy == 'balanced'
        assert portfolio.is_initialized == False
        assert portfolio.realized_gains == Decimal('0')

    def test_unique_user_id(self, db_session, sample_portfolio):
        """Test that user_id must be unique."""
        duplicate = PortfolioState(user_id='test_user')
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_portfolio_timestamps(self, db_session):
        """Test that timestamps are auto-generated."""
        portfolio = PortfolioState(user_id='timestamp_test')
        db_session.add(portfolio)
        db_session.commit()

        assert portfolio.created_at is not None
        assert portfolio.updated_at is not None

    def test_portfolio_to_dict(self, sample_portfolio):
        """Test portfolio serialization."""
        data = sample_portfolio.to_dict()

        assert data['user_id'] == 'test_user'
        assert data['initial_value'] == 100000.00
        assert data['current_cash'] == 50000.00
        assert data['current_strategy'] == 'balanced'
        assert data['is_initialized'] == True


class TestHoldingsModel:
    """Tests for Holdings model."""

    def test_create_holding(self, db_session, sample_portfolio):
        """Test creating a new holding."""
        holding = Holdings(
            user_id='test_user',
            symbol='NVDA',
            name='NVIDIA Corporation',
            sector='Technology',
            quantity=Decimal('25'),
            avg_cost=Decimal('450.00')
        )
        db_session.add(holding)
        db_session.commit()

        assert holding.id is not None
        assert holding.symbol == 'NVDA'
        assert holding.quantity == Decimal('25')

    def test_holding_unique_constraint(self, db_session, sample_holdings):
        """Test unique constraint on user_id + symbol."""
        duplicate = Holdings(
            user_id='test_user',
            symbol='AAPL',  # Already exists
            name='Apple',
            quantity=Decimal('10'),
            avg_cost=Decimal('100.00')
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_holding_current_value(self, sample_holdings):
        """Test current value calculation."""
        aapl = sample_holdings[0]
        current_price = Decimal('160.00')

        value = aapl.current_value(current_price)

        assert value == Decimal('16000.00')  # 100 * 160

    def test_holding_unrealized_gain(self, sample_holdings):
        """Test unrealized gain calculation."""
        aapl = sample_holdings[0]
        current_price = Decimal('160.00')

        gain = aapl.unrealized_gain(current_price)
        gain_percent = aapl.unrealized_gain_percent(current_price)

        assert gain == Decimal('1000.00')  # (160 - 150) * 100
        assert abs(gain_percent - Decimal('6.67')) < Decimal('0.01')

    def test_holding_to_dict(self, sample_holdings, current_prices):
        """Test holding serialization with current price."""
        aapl = sample_holdings[0]
        data = aapl.to_dict(current_prices['AAPL'])

        assert data['symbol'] == 'AAPL'
        assert data['quantity'] == 100
        assert data['avg_cost'] == 150.00
        assert 'current_price' in data
        assert 'current_value' in data
        assert 'unrealized_gain' in data


class TestTradesHistoryModel:
    """Tests for TradesHistory model."""

    def test_create_trade(self, db_session, sample_portfolio):
        """Test creating a new trade."""
        trade = TradesHistory(
            user_id='test_user',
            trade_id='trade-new-001',
            timestamp=datetime.now(),
            type='buy',
            symbol='GOOGL',
            stock_name='Alphabet Inc.',
            sector='Technology',
            quantity=10,
            price=Decimal('140.00'),
            total=Decimal('1400.00'),
            fees=Decimal('1.40'),
            strategy='growth'
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.id is not None
        assert trade.trade_id == 'trade-new-001'

    def test_trade_id_unique(self, db_session, sample_trades):
        """Test that trade_id must be unique."""
        duplicate = TradesHistory(
            user_id='test_user',
            trade_id='trade-001',  # Already exists
            timestamp=datetime.now(),
            type='buy',
            symbol='AAPL',
            quantity=10,
            price=Decimal('100'),
            total=Decimal('1000')
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_trade_type_validation(self, db_session, sample_portfolio):
        """Test that trade type is validated."""
        # This should work - model doesn't enforce, but API should
        trade = TradesHistory(
            user_id='test_user',
            trade_id='trade-invalid-type',
            timestamp=datetime.now(),
            type='invalid',  # Not 'buy' or 'sell'
            symbol='AAPL',
            quantity=10,
            price=Decimal('100'),
            total=Decimal('1000')
        )
        db_session.add(trade)
        db_session.commit()

        # Model allows it, validation should be at API layer
        assert trade.type == 'invalid'

    def test_trade_to_dict(self, sample_trades):
        """Test trade serialization."""
        trade = sample_trades[0]
        data = trade.to_dict()

        assert data['trade_id'] == 'trade-001'
        assert data['type'] == 'buy'
        assert data['symbol'] == 'AAPL'
        assert data['quantity'] == 100
        assert data['price'] == 150.00


class TestStrategyCustomizationModel:
    """Tests for StrategyCustomization model."""

    def test_create_customization(self, db_session, sample_portfolio):
        """Test creating a strategy customization."""
        customization = StrategyCustomization(
            user_id='test_user',
            strategy_id='growth',
            confidence_level=80,
            trade_frequency='high',
            max_position_size=20
        )
        db_session.add(customization)
        db_session.commit()

        assert customization.id is not None
        assert customization.confidence_level == 80

    def test_customization_defaults(self, db_session, sample_portfolio):
        """Test default values."""
        customization = StrategyCustomization(
            user_id='test_user',
            strategy_id='conservative'
        )
        db_session.add(customization)
        db_session.commit()

        assert customization.confidence_level == 50
        assert customization.trade_frequency == 'medium'
        assert customization.max_position_size == 15
        assert customization.stop_loss_percent == 10
        assert customization.take_profit_percent == 20
        assert customization.auto_rebalance == True
        assert customization.reinvest_dividends == True

    def test_unique_user_strategy_combo(self, db_session, sample_strategy_customization):
        """Test unique constraint on user_id + strategy_id."""
        duplicate = StrategyCustomization(
            user_id='test_user',
            strategy_id='balanced'  # Already exists for test_user
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_validate_confidence_level(self):
        """Test confidence level validation."""
        customization = StrategyCustomization(strategy_id='test')

        # Valid values
        assert customization.validate_confidence_level(50) == True
        assert customization.validate_confidence_level(10) == True
        assert customization.validate_confidence_level(100) == True

        # Invalid values
        assert customization.validate_confidence_level(5) == False
        assert customization.validate_confidence_level(150) == False

    def test_validate_trade_frequency(self):
        """Test trade frequency validation."""
        customization = StrategyCustomization(strategy_id='test')

        assert customization.validate_trade_frequency('low') == True
        assert customization.validate_trade_frequency('medium') == True
        assert customization.validate_trade_frequency('high') == True
        assert customization.validate_trade_frequency('invalid') == False


class TestMarketDataCacheModel:
    """Tests for MarketDataCache model."""

    def test_create_cache_entry(self, db_session):
        """Test creating a market data cache entry."""
        entry = MarketDataCache(
            symbol='TSLA',
            date=date.today(),
            open=Decimal('240.00'),
            high=Decimal('250.00'),
            low=Decimal('235.00'),
            close=Decimal('245.00'),
            adj_close=Decimal('245.00'),
            volume=50000000,
            fetched_at=datetime.now()
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.id is not None
        assert entry.symbol == 'TSLA'

    def test_unique_symbol_date(self, db_session, sample_market_data):
        """Test unique constraint on symbol + date."""
        existing = sample_market_data[0]

        duplicate = MarketDataCache(
            symbol=existing.symbol,
            date=existing.date,
            close=Decimal('999.00'),
            adj_close=Decimal('999.00'),
            fetched_at=datetime.now()
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_cache_entry_to_dict(self, sample_market_data):
        """Test cache entry serialization."""
        entry = sample_market_data[0]
        data = entry.to_dict()

        assert 'symbol' in data
        assert 'date' in data
        assert 'open' in data
        assert 'high' in data
        assert 'low' in data
        assert 'close' in data
        assert 'volume' in data


class TestMarketDataMetadataModel:
    """Tests for MarketDataMetadata model."""

    def test_create_metadata(self, db_session):
        """Test creating market data metadata."""
        metadata = MarketDataMetadata(
            symbol='NVDA',
            last_fetch_date=date.today(),
            earliest_date=date.today() - timedelta(days=365),
            latest_date=date.today(),
            total_records=252,
            fetch_status='complete'
        )
        db_session.add(metadata)
        db_session.commit()

        assert metadata.id is not None
        assert metadata.total_records == 252

    def test_unique_symbol(self, db_session):
        """Test unique constraint on symbol."""
        metadata1 = MarketDataMetadata(symbol='AMD')
        db_session.add(metadata1)
        db_session.commit()

        metadata2 = MarketDataMetadata(symbol='AMD')
        db_session.add(metadata2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_default_fetch_status(self, db_session):
        """Test default fetch status."""
        metadata = MarketDataMetadata(symbol='INTC')
        db_session.add(metadata)
        db_session.commit()

        assert metadata.fetch_status == 'pending'
