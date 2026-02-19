"""
Unit Tests for Market Data Service

Tests local CSV file reading and database caching including:
- Loading data from local CSV files
- Cache hit: returns data from database without file read
- Market hours detection
- Current price retrieval
- Batch fetching
- Cache management
"""
import pytest
import os
import tempfile
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
import numpy as np

from app.services.market_data_service import MarketDataService, get_market_data_service
from app.models import MarketDataCache, MarketDataMetadata


class TestMarketDataServiceInit:
    """Tests for MarketDataService initialization."""

    def test_service_initialization(self, app, db_session):
        """Service initializes correctly."""
        with app.app_context():
            service = MarketDataService()
            assert service is not None
            assert service.cache_hours == 24
            assert service.history_years == 5

    def test_service_with_custom_params(self, app, db_session):
        """Service accepts custom parameters."""
        with app.app_context():
            service = MarketDataService(cache_hours=12, history_years=3)
            assert service.cache_hours == 12
            assert service.history_years == 3

    def test_singleton_service(self, app, db_session):
        """get_market_data_service returns singleton."""
        with app.app_context():
            service1 = get_market_data_service()
            service2 = get_market_data_service()
            assert service1 is service2


class TestMarketHours:
    """Tests for market hours detection."""

    def test_is_market_open_returns_bool(self, app, db_session):
        """is_market_open should return a boolean."""
        with app.app_context():
            service = MarketDataService()
            result = service.is_market_open()
            assert isinstance(result, bool)

    def test_get_last_trading_day_not_weekend(self, app, db_session):
        """Last trading day should never be a weekend."""
        with app.app_context():
            service = MarketDataService()
            last_day = service.get_last_trading_day()
            assert last_day.weekday() < 5  # Not Saturday or Sunday


class TestLocalCSV:
    """Tests for local CSV file loading."""

    def test_load_nonexistent_symbol(self, app, db_session):
        """Loading a symbol with no CSV should return None."""
        with app.app_context():
            service = MarketDataService()
            result = service._load_from_local_csv('NONEXISTENT_SYMBOL_XYZ')
            assert result is None

    def test_csv_filename_patterns(self, app, db_session):
        """Should try multiple filename patterns."""
        with app.app_context():
            service = MarketDataService()
            # Test that _get_csv_filename returns None for missing symbols
            result = service._get_csv_filename('NONEXISTENT')
            assert result is None

    def test_csv_memory_cache(self, app, db_session, tmp_path):
        """Should cache CSV data in memory after first load."""
        with app.app_context():
            service = MarketDataService()

            # Create a temp CSV file
            csv_content = "Date,Open,High,Low,Close,Volume\n2024-01-15,150.0,152.0,148.0,151.0,1000000\n"
            csv_file = tmp_path / "TEST.csv"
            csv_file.write_text(csv_content)

            # Patch TICKER_CSV_DIR to use tmp_path
            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                # First load
                result1 = service._load_from_local_csv('TEST')
                assert result1 is not None
                assert len(result1) == 1

                # Second load should come from memory cache
                assert 'TEST' in service._local_csv_cache


class TestGetPriceData:
    """Tests for get_price_data method."""

    def test_returns_dataframe(self, app, db_session, tmp_path):
        """Should return a DataFrame."""
        with app.app_context():
            service = MarketDataService()

            # Create test CSV
            dates = pd.date_range(start='2024-01-01', periods=20, freq='B')
            csv_lines = ["Date,Open,High,Low,Close,Volume"]
            for d in dates:
                csv_lines.append(f"{d.strftime('%Y-%m-%d')},150.0,152.0,148.0,151.0,1000000")
            csv_file = tmp_path / "AAPL.csv"
            csv_file.write_text("\n".join(csv_lines))

            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                result = service.get_price_data('AAPL', date(2024, 1, 1), date(2024, 2, 1))
                assert isinstance(result, pd.DataFrame)
                assert len(result) > 0

    def test_returns_empty_for_unknown_symbol(self, app, db_session):
        """Should return empty DataFrame for unknown symbol."""
        with app.app_context():
            service = MarketDataService()
            result = service.get_price_data('ZZZZZ_FAKE', date(2024, 1, 1), date(2024, 1, 31))
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    def test_falls_back_to_cache(self, app, db_session, sample_market_data):
        """Should use database cache when no CSV file exists."""
        with app.app_context():
            service = MarketDataService()
            result = service.get_price_data(
                'AAPL',
                sample_market_data[0].date,
                sample_market_data[-1].date
            )
            assert result is not None
            assert len(result) > 0


class TestGetCurrentPrice:
    """Tests for current price retrieval."""

    def test_current_price_from_csv(self, app, db_session, tmp_path):
        """Should return current price from CSV."""
        with app.app_context():
            service = MarketDataService()

            csv_content = "Date,Open,High,Low,Close,Volume\n2024-01-15,150.0,152.0,148.0,151.0,1000000\n"
            csv_file = tmp_path / "AAPL.csv"
            csv_file.write_text(csv_content)

            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                result = service.get_current_price('AAPL')
                assert result is not None
                assert result['symbol'] == 'AAPL'
                assert result['price'] == 151.0
                assert result['source'] == 'local_csv'

    def test_current_price_from_cache(self, app, db_session, sample_market_data):
        """Should return current price from cache."""
        with app.app_context():
            service = MarketDataService()
            result = service.get_current_price('AAPL')
            assert result is not None
            assert result['symbol'] == 'AAPL'
            assert result['price'] is not None

    def test_unavailable_price(self, app, db_session):
        """Should return unavailable status for unknown symbol."""
        with app.app_context():
            service = MarketDataService()
            result = service.get_current_price('ZZZZZ_FAKE')
            assert result['source'] == 'unavailable'
            assert result['price'] is None


class TestBatchFetching:
    """Tests for batch symbol fetching."""

    def test_fetch_multiple_symbols(self, app, db_session, tmp_path):
        """Should fetch data for multiple symbols."""
        with app.app_context():
            service = MarketDataService()

            # Create test CSVs
            for sym in ['AAPL', 'MSFT', 'GOOGL']:
                csv_content = f"Date,Open,High,Low,Close,Volume\n2024-01-15,150.0,152.0,148.0,151.0,1000000\n"
                (tmp_path / f"{sym}.csv").write_text(csv_content)

            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                results = service.fetch_multiple_symbols(
                    ['AAPL', 'MSFT', 'GOOGL'],
                    date(2024, 1, 1),
                    date(2024, 2, 1)
                )

                assert 'AAPL' in results
                assert 'MSFT' in results
                assert 'GOOGL' in results


class TestCacheManagement:
    """Tests for cache management utilities."""

    def test_get_cache_status(self, app, db_session, sample_market_data):
        """Should return cache status for symbol."""
        with app.app_context():
            service = MarketDataService()
            status = service.get_cache_status('AAPL')
            assert 'earliest_date' in status or 'cached' in status

    def test_clear_cache_single_symbol(self, app, db_session, sample_market_data):
        """Should clear cache for specific symbol."""
        with app.app_context():
            service = MarketDataService()
            service.clear_cache('AAPL')
            count = db_session.query(MarketDataCache).filter_by(symbol='AAPL').count()
            assert count == 0

    def test_clear_all_cache(self, app, db_session, sample_market_data):
        """Should clear all cache when no symbol specified."""
        with app.app_context():
            service = MarketDataService()
            service.clear_cache()
            count = db_session.query(MarketDataCache).count()
            assert count == 0

    def test_refresh_cache_from_csv(self, app, db_session, tmp_path):
        """Should refresh cache by reloading CSV."""
        with app.app_context():
            service = MarketDataService()

            csv_content = "Date,Open,High,Low,Close,Volume\n2024-01-15,150.0,152.0,148.0,151.0,1000000\n"
            (tmp_path / "AAPL.csv").write_text(csv_content)

            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                result = service.refresh_cache('AAPL')
                assert result is True

    def test_refresh_cache_no_data(self, app, db_session):
        """Should return False when no data available."""
        with app.app_context():
            service = MarketDataService()
            result = service.refresh_cache('ZZZZZ_FAKE')
            assert result is False

    def test_list_available_symbols(self, app, db_session, tmp_path):
        """Should list symbols from CSV files."""
        with app.app_context():
            service = MarketDataService()

            # Create test CSV files
            for sym in ['AAPL', 'MSFT']:
                (tmp_path / f"{sym}.csv").write_text("Date,Close\n2024-01-15,151.0\n")

            with patch('app.services.market_data_service.TICKER_CSV_DIR', tmp_path):
                symbols = service.list_available_symbols()
                assert 'AAPL' in symbols
                assert 'MSFT' in symbols
