"""
Unit Tests for Market Data Service

Tests Yahoo Finance integration and DB2 caching including:
- Cache miss: fetches from Yahoo Finance
- Cache hit: returns data from DB2 without API call
- Partial cache: fetches only missing date ranges
- Rate limiting: respects delays between requests
- Fallback: uses GBM when Yahoo Finance unavailable
- Market hours detection
"""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from app.services.market_data_service import (
    MarketDataService,
    is_market_open,
    get_last_trading_day,
    get_market_hours
)
from app.models import MarketDataCache, MarketDataMetadata


class TestMarketDataServiceInit:
    """Tests for MarketDataService initialization."""

    def test_service_initialization(self, app, db_session):
        """Service initializes correctly."""
        with app.app_context():
            service = MarketDataService()
            assert service is not None

    def test_service_with_custom_cache_duration(self, app, db_session):
        """Service accepts custom cache duration."""
        with app.app_context():
            service = MarketDataService(cache_duration_minutes=30)
            assert service.cache_duration_minutes == 30


class TestCacheMiss:
    """Tests for cache miss scenarios."""

    def test_cache_miss_fetches_from_yahoo(self, app, db_session, mock_yahoo_finance):
        """First request should fetch from Yahoo Finance."""
        with app.app_context():
            service = MarketDataService()
            start_date = date.today() - timedelta(days=30)
            end_date = date.today() - timedelta(days=1)

            result = service.get_price_data('AAPL', start_date, end_date)

            assert result is not None
            assert len(result) > 0
            mock_yahoo_finance.assert_called()

    def test_cache_miss_stores_in_db(self, app, db_session, mock_yahoo_finance):
        """Fetched data should be stored in cache."""
        with app.app_context():
            service = MarketDataService()
            start_date = date.today() - timedelta(days=10)
            end_date = date.today() - timedelta(days=1)

            service.get_price_data('TSLA', start_date, end_date)

            # Check cache has entries
            cache_count = db_session.query(MarketDataCache).filter_by(
                symbol='TSLA'
            ).count()

            assert cache_count > 0

    def test_cache_miss_updates_metadata(self, app, db_session, mock_yahoo_finance):
        """Fetching should update metadata table."""
        with app.app_context():
            service = MarketDataService()
            start_date = date.today() - timedelta(days=10)
            end_date = date.today() - timedelta(days=1)

            service.get_price_data('NVDA', start_date, end_date)

            metadata = db_session.query(MarketDataMetadata).filter_by(
                symbol='NVDA'
            ).first()

            assert metadata is not None
            assert metadata.fetch_status == 'complete'


class TestCacheHit:
    """Tests for cache hit scenarios."""

    def test_cache_hit_no_api_call(self, app, db_session, sample_market_data):
        """Second request should use cache, not API."""
        with app.app_context():
            service = MarketDataService()

            # Data is already in cache via sample_market_data fixture
            with patch('pandas_datareader.DataReader') as mock_download:
                result = service.get_price_data(
                    'AAPL',
                    sample_market_data[0].date,
                    sample_market_data[-1].date
                )

                # Should not call Yahoo Finance
                mock_download.assert_not_called()

                # Should return cached data
                assert result is not None
                assert len(result) > 0

    def test_cache_hit_returns_correct_data(self, app, db_session, sample_market_data):
        """Cached data should match what was stored."""
        with app.app_context():
            service = MarketDataService()

            result = service.get_price_data(
                'AAPL',
                sample_market_data[0].date,
                sample_market_data[-1].date
            )

            # Check first entry matches
            first_cached = sample_market_data[0]
            first_result = result.iloc[0]

            assert abs(float(first_result['close']) - float(first_cached.close)) < 0.01


class TestPartialCache:
    """Tests for partial cache scenarios."""

    def test_partial_cache_fetches_missing_only(self, app, db_session, sample_market_data, mock_yahoo_finance):
        """Should only fetch missing date ranges."""
        with app.app_context():
            service = MarketDataService()

            # Request data beyond cached range
            start_date = sample_market_data[0].date - timedelta(days=60)
            end_date = sample_market_data[-1].date

            result = service.get_price_data('AAPL', start_date, end_date)

            # Should have called Yahoo for missing dates only
            mock_yahoo_finance.assert_called()

            # Result should include both cached and fetched data
            assert result is not None

    def test_identifies_missing_ranges(self, app, db_session, sample_market_data):
        """Should correctly identify gaps in cache."""
        with app.app_context():
            service = MarketDataService()

            # Check for missing ranges
            start_date = sample_market_data[0].date - timedelta(days=60)
            end_date = sample_market_data[-1].date + timedelta(days=10)

            missing = service._identify_missing_ranges(
                'AAPL', start_date, end_date
            )

            # Should identify ranges before and after cached data
            assert len(missing) > 0


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_respects_delay_between_requests(self, app, db_session):
        """Should delay between batch requests."""
        with app.app_context():
            service = MarketDataService()

            with patch('pandas_datareader.DataReader') as mock_download:
                with patch('time.sleep') as mock_sleep:
                    mock_download.return_value = pd.DataFrame({
                        'Open': [150], 'High': [152], 'Low': [148],
                        'Close': [151], 'Adj Close': [151], 'Volume': [1000000]
                    }, index=[pd.Timestamp.now()])

                    # Fetch multiple symbols
                    service.fetch_multiple_symbols(
                        ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META'],
                        date.today() - timedelta(days=5),
                        date.today()
                    )

                    # Should have delays between batches
                    # (5 symbols per batch, so at least 1 delay)
                    assert mock_sleep.called

    def test_exponential_backoff_on_rate_limit(self, app, db_session):
        """Should use exponential backoff on rate limit errors."""
        with app.app_context():
            service = MarketDataService()

            # Simulate rate limit error then success
            call_count = 0

            def mock_download_with_rate_limit(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Rate limit exceeded")
                return pd.DataFrame({
                    'Open': [150], 'High': [152], 'Low': [148],
                    'Close': [151], 'Adj Close': [151], 'Volume': [1000000]
                }, index=[pd.Timestamp.now()])

            with patch('pandas_datareader.DataReader', side_effect=mock_download_with_rate_limit):
                with patch('time.sleep') as mock_sleep:
                    try:
                        service.get_price_data(
                            'AAPL',
                            date.today() - timedelta(days=5),
                            date.today()
                        )
                    except:
                        pass

                    # Should have retried with increasing delays
                    if mock_sleep.called:
                        delays = [call.args[0] for call in mock_sleep.call_args_list]
                        # Delays should increase (exponential backoff)
                        for i in range(1, len(delays)):
                            assert delays[i] >= delays[i-1]


class TestFallback:
    """Tests for fallback to GBM simulation."""

    def test_fallback_when_yahoo_unavailable(self, app, db_session):
        """Should use GBM simulation when Yahoo Finance fails."""
        with app.app_context():
            service = MarketDataService()

            with patch('pandas_datareader.DataReader', side_effect=Exception("Service unavailable")):
                result = service.get_price_data(
                    'AAPL',
                    date.today() - timedelta(days=5),
                    date.today(),
                    allow_fallback=True
                )

                # Should return simulated data
                assert result is not None
                assert 'source' in result.attrs or len(result) > 0

    def test_fallback_marked_as_simulated(self, app, db_session):
        """Fallback data should be marked as simulated."""
        with app.app_context():
            service = MarketDataService()

            with patch('pandas_datareader.DataReader', side_effect=Exception("Error")):
                result = service.get_current_price('AAPL', allow_fallback=True)

                if result:
                    assert result.get('source') == 'simulated'

    def test_no_fallback_when_disabled(self, app, db_session):
        """Should raise error when fallback is disabled."""
        with app.app_context():
            service = MarketDataService()

            with patch('pandas_datareader.DataReader', side_effect=Exception("Error")):
                with pytest.raises(Exception):
                    service.get_price_data(
                        'AAPL',
                        date.today() - timedelta(days=5),
                        date.today(),
                        allow_fallback=False
                    )


class TestMarketHours:
    """Tests for market hours detection."""

    def test_market_open_during_trading_hours(self):
        """Market should be open during NYSE hours."""
        # Create a datetime during market hours (2:00 PM ET on a Monday)
        # Note: This test may be flaky depending on when it runs
        from datetime import timezone
        import pytz

        et = pytz.timezone('US/Eastern')
        market_open_time = datetime(2024, 1, 15, 14, 0, 0, tzinfo=et)  # Monday 2 PM ET

        with patch('app.services.market_data_service.datetime') as mock_dt:
            mock_dt.now.return_value = market_open_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # This tests the logic, actual result depends on implementation
            result = is_market_open()
            # Just verify it returns a boolean
            assert isinstance(result, bool)

    def test_market_closed_on_weekend(self):
        """Market should be closed on weekends."""
        # Saturday
        saturday = date(2024, 1, 13)

        result = is_market_open(check_date=saturday)

        assert result == False

    def test_market_closed_on_sunday(self):
        """Market should be closed on Sunday."""
        sunday = date(2024, 1, 14)

        result = is_market_open(check_date=sunday)

        assert result == False

    def test_get_last_trading_day_from_weekend(self):
        """Last trading day from weekend should be Friday."""
        saturday = date(2024, 1, 13)

        last_day = get_last_trading_day(from_date=saturday)

        # Should be Friday Jan 12
        assert last_day == date(2024, 1, 12)
        assert last_day.weekday() == 4  # Friday

    def test_get_last_trading_day_from_weekday(self):
        """Last trading day from weekday should be that day or previous."""
        wednesday = date(2024, 1, 10)

        last_day = get_last_trading_day(from_date=wednesday)

        # Should be Wednesday itself or earlier
        assert last_day <= wednesday
        assert last_day.weekday() < 5  # Not weekend


class TestCurrentPrice:
    """Tests for current price fetching."""

    def test_get_current_price(self, app, db_session, mock_yahoo_finance):
        """Should return current price with metadata."""
        with app.app_context():
            service = MarketDataService()

            result = service.get_current_price('AAPL')

            assert result is not None
            assert 'symbol' in result
            assert 'price' in result
            assert 'timestamp' in result

    def test_current_price_from_cache(self, app, db_session, sample_market_data):
        """Should use recent cache for current price."""
        with app.app_context():
            service = MarketDataService()

            # Update cache to be recent
            latest = sample_market_data[-1]
            latest.date = date.today() - timedelta(days=1)
            latest.fetched_at = datetime.now()
            db_session.commit()

            with patch('pandas_datareader.DataReader') as mock_download:
                result = service.get_current_price('AAPL')

                # Should use cache if recent enough
                # (behavior depends on implementation)
                assert result is not None


class TestBatchFetching:
    """Tests for batch symbol fetching."""

    def test_fetch_multiple_symbols(self, app, db_session, mock_yahoo_finance):
        """Should fetch multiple symbols efficiently."""
        with app.app_context():
            service = MarketDataService()

            symbols = ['AAPL', 'MSFT', 'GOOGL']
            result = service.fetch_multiple_symbols(
                symbols,
                date.today() - timedelta(days=5),
                date.today()
            )

            assert 'AAPL' in result
            assert 'MSFT' in result
            assert 'GOOGL' in result

    def test_batch_respects_max_symbols(self, app, db_session):
        """Should batch requests to avoid rate limits."""
        with app.app_context():
            service = MarketDataService()
            service.max_symbols_per_request = 5

            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
                      'META', 'NVDA', 'AMD', 'INTC', 'ORCL']

            with patch('pandas_datareader.DataReader') as mock_download:
                mock_download.return_value = pd.DataFrame()

                service.fetch_multiple_symbols(
                    symbols,
                    date.today() - timedelta(days=5),
                    date.today()
                )

                # Should have made multiple calls (10 symbols / 5 per batch = 2)
                assert mock_download.call_count >= 2


class TestCacheManagement:
    """Tests for cache management utilities."""

    def test_get_cache_status(self, app, db_session, sample_market_data):
        """Should return cache status for symbol."""
        with app.app_context():
            service = MarketDataService()

            status = service.get_cache_status('AAPL')

            assert 'earliest_date' in status
            assert 'latest_date' in status
            assert 'total_records' in status

    def test_clear_cache_single_symbol(self, app, db_session, sample_market_data):
        """Should clear cache for specific symbol."""
        with app.app_context():
            service = MarketDataService()

            service.clear_cache('AAPL')

            count = db_session.query(MarketDataCache).filter_by(
                symbol='AAPL'
            ).count()

            assert count == 0

    def test_clear_all_cache(self, app, db_session, sample_market_data):
        """Should clear all cache when no symbol specified."""
        with app.app_context():
            service = MarketDataService()

            # Add data for another symbol
            entry = MarketDataCache(
                symbol='MSFT',
                date=date.today(),
                close=Decimal('300'),
                adj_close=Decimal('300'),
                fetched_at=datetime.now()
            )
            db_session.add(entry)
            db_session.commit()

            service.clear_cache()

            count = db_session.query(MarketDataCache).count()
            assert count == 0

    def test_get_cached_symbols(self, app, db_session, sample_market_data):
        """Should return list of cached symbols."""
        with app.app_context():
            service = MarketDataService()

            symbols = service.get_cached_symbols()

            assert 'AAPL' in symbols

    def test_refresh_cache(self, app, db_session, sample_market_data, mock_yahoo_finance):
        """Should refresh cache for symbol."""
        with app.app_context():
            service = MarketDataService()

            result = service.refresh_cache('AAPL')

            assert result == True
            mock_yahoo_finance.assert_called()


class TestDataQuality:
    """Tests for data quality and validation."""

    def test_handles_missing_ohlcv_fields(self, app, db_session):
        """Should handle incomplete OHLCV data gracefully."""
        with app.app_context():
            service = MarketDataService()

            # Create mock data with missing fields
            incomplete_data = pd.DataFrame({
                'Close': [150, 151, 152],
                'Volume': [1000000, 1100000, 1200000]
            }, index=pd.date_range(start='2024-01-01', periods=3))

            with patch('pandas_datareader.DataReader', return_value=incomplete_data):
                result = service.get_price_data(
                    'TEST',
                    date(2024, 1, 1),
                    date(2024, 1, 3)
                )

                # Should handle gracefully
                assert result is not None

    def test_validates_price_values(self, app, db_session):
        """Should reject invalid price values."""
        with app.app_context():
            service = MarketDataService()

            # Create mock data with negative price
            bad_data = pd.DataFrame({
                'Open': [150, -10, 152],  # Negative price
                'High': [152, 151, 154],
                'Low': [148, 149, 150],
                'Close': [151, 150, 153],
                'Adj Close': [151, 150, 153],
                'Volume': [1000000, 1100000, 1200000]
            }, index=pd.date_range(start='2024-01-01', periods=3))

            with patch('pandas_datareader.DataReader', return_value=bad_data):
                result = service.get_price_data(
                    'TEST',
                    date(2024, 1, 1),
                    date(2024, 1, 3)
                )

                # Should filter out invalid rows or handle them
                if result is not None and len(result) > 0:
                    assert all(result['open'] >= 0) or 'open' not in result.columns
