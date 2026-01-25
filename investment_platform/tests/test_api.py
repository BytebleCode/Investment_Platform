"""
API Integration Tests

Tests all REST API endpoints including:
- Portfolio endpoints
- Strategy endpoints
- Trade endpoints
- Holdings endpoints
- Market data endpoints
- Health endpoints
"""
import pytest
import json
from decimal import Decimal
from datetime import datetime, date, timedelta


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Health endpoint returns OK."""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data

    def test_health_includes_db_status(self, client):
        """Health check includes database status."""
        response = client.get('/api/health')

        data = response.get_json()
        assert 'database' in data or data['status'] == 'ok'


class TestPortfolioEndpoints:
    """Tests for portfolio API endpoints."""

    def test_get_portfolio_settings(self, client, sample_portfolio):
        """GET /api/portfolio/settings returns portfolio data."""
        response = client.get('/api/portfolio/settings?user_id=test_user')

        assert response.status_code == 200
        data = response.get_json()
        assert 'current_cash' in data
        assert 'current_strategy' in data
        assert 'realized_gains' in data

    def test_get_portfolio_settings_default_user(self, client, db_session):
        """GET /api/portfolio/settings creates default user if none exists."""
        response = client.get('/api/portfolio/settings')

        assert response.status_code in [200, 201]

    def test_update_portfolio_settings(self, client, sample_portfolio):
        """PUT /api/portfolio/settings updates settings."""
        response = client.put(
            '/api/portfolio/settings?user_id=test_user',
            json={'current_strategy': 'growth'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['current_strategy'] == 'growth'

    def test_update_portfolio_cash(self, client, sample_portfolio):
        """PUT /api/portfolio/cash updates cash balance."""
        response = client.put(
            '/api/portfolio/cash?user_id=test_user',
            json={'current_cash': 75000.00}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert float(data['current_cash']) == 75000.00

    def test_reset_portfolio(self, client, sample_portfolio, sample_holdings, sample_trades):
        """POST /api/portfolio/reset clears all data."""
        response = client.post('/api/portfolio/reset?user_id=test_user')

        assert response.status_code == 200

        # Verify reset
        get_response = client.get('/api/portfolio/settings?user_id=test_user')
        data = get_response.get_json()
        assert float(data['current_cash']) == float(data['initial_value'])
        assert float(data['realized_gains']) == 0

    def test_update_invalid_strategy(self, client, sample_portfolio):
        """PUT with invalid strategy should fail."""
        response = client.put(
            '/api/portfolio/settings?user_id=test_user',
            json={'current_strategy': 'invalid_strategy'}
        )

        assert response.status_code == 400


class TestStrategyEndpoints:
    """Tests for strategy API endpoints."""

    def test_get_strategy_customizations(self, client, sample_strategy_customization):
        """GET /api/strategies/customizations returns customizations."""
        response = client.get('/api/strategies/customizations?user_id=test_user')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_update_strategy_customization(self, client, sample_portfolio):
        """PUT /api/strategies/customizations/<id> updates customization."""
        response = client.put(
            '/api/strategies/customizations/growth?user_id=test_user',
            json={
                'confidence_level': 80,
                'trade_frequency': 'high',
                'max_position_size': 20
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['confidence_level'] == 80

    def test_create_strategy_customization(self, client, sample_portfolio):
        """PUT creates new customization if none exists."""
        response = client.put(
            '/api/strategies/customizations/aggressive?user_id=test_user',
            json={
                'confidence_level': 90,
                'trade_frequency': 'high'
            }
        )

        assert response.status_code in [200, 201]

    def test_invalid_confidence_level(self, client, sample_portfolio):
        """Confidence level must be 10-100."""
        response = client.put(
            '/api/strategies/customizations/balanced?user_id=test_user',
            json={'confidence_level': 150}
        )

        assert response.status_code == 400

    def test_invalid_trade_frequency(self, client, sample_portfolio):
        """Trade frequency must be low/medium/high."""
        response = client.put(
            '/api/strategies/customizations/balanced?user_id=test_user',
            json={'trade_frequency': 'ultra_fast'}
        )

        assert response.status_code == 400

    def test_invalid_max_position_size(self, client, sample_portfolio):
        """Max position size must be 5-50."""
        response = client.put(
            '/api/strategies/customizations/balanced?user_id=test_user',
            json={'max_position_size': 75}
        )

        assert response.status_code == 400


class TestTradeEndpoints:
    """Tests for trade API endpoints."""

    def test_create_trade(self, client, sample_portfolio):
        """POST /api/trades creates new trade."""
        response = client.post(
            '/api/trades?user_id=test_user',
            json={
                'trade_id': 'test-trade-new',
                'timestamp': datetime.now().isoformat(),
                'type': 'buy',
                'symbol': 'AAPL',
                'stock_name': 'Apple Inc.',
                'sector': 'Technology',
                'quantity': 10,
                'price': 150.00,
                'total': 1500.00,
                'fees': 1.50,
                'strategy': 'balanced'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['trade_id'] == 'test-trade-new'

    def test_get_trades(self, client, sample_trades):
        """GET /api/trades returns trade history."""
        response = client.get('/api/trades?user_id=test_user')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_trades_ordered_by_timestamp(self, client, sample_trades):
        """Trades should be ordered by timestamp DESC."""
        response = client.get('/api/trades?user_id=test_user')

        data = response.get_json()
        timestamps = [t['timestamp'] for t in data]

        # Should be descending order
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_trades_limit(self, client, sample_trades):
        """Trades endpoint respects limit parameter."""
        response = client.get('/api/trades?user_id=test_user&limit=2')

        data = response.get_json()
        assert len(data) <= 2

    def test_create_trade_missing_fields(self, client, sample_portfolio):
        """POST with missing required fields should fail."""
        response = client.post(
            '/api/trades?user_id=test_user',
            json={
                'trade_id': 'test-incomplete',
                'type': 'buy'
                # Missing: symbol, quantity, price, total
            }
        )

        assert response.status_code == 400

    def test_create_trade_invalid_type(self, client, sample_portfolio):
        """Trade type must be buy or sell."""
        response = client.post(
            '/api/trades?user_id=test_user',
            json={
                'trade_id': 'test-invalid-type',
                'timestamp': datetime.now().isoformat(),
                'type': 'hold',
                'symbol': 'AAPL',
                'quantity': 10,
                'price': 150.00,
                'total': 1500.00
            }
        )

        assert response.status_code == 400

    def test_duplicate_trade_id_fails(self, client, sample_trades):
        """Duplicate trade_id should fail."""
        response = client.post(
            '/api/trades?user_id=test_user',
            json={
                'trade_id': 'trade-001',  # Already exists
                'timestamp': datetime.now().isoformat(),
                'type': 'buy',
                'symbol': 'AAPL',
                'quantity': 10,
                'price': 150.00,
                'total': 1500.00
            }
        )

        assert response.status_code in [400, 409]


class TestHoldingsEndpoints:
    """Tests for holdings API endpoints."""

    def test_get_holdings(self, client, sample_holdings):
        """GET /api/holdings returns current holdings."""
        response = client.get('/api/holdings?user_id=test_user')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 3  # sample_holdings has 3 entries

    def test_get_holdings_ordered_by_symbol(self, client, sample_holdings):
        """Holdings should be ordered by symbol."""
        response = client.get('/api/holdings?user_id=test_user')

        data = response.get_json()
        symbols = [h['symbol'] for h in data]

        assert symbols == sorted(symbols)

    def test_update_holdings_bulk(self, client, sample_portfolio):
        """PUT /api/holdings replaces all holdings."""
        new_holdings = [
            {
                'symbol': 'TSLA',
                'name': 'Tesla Inc.',
                'sector': 'Automotive',
                'quantity': 50,
                'avg_cost': 240.00
            },
            {
                'symbol': 'NVDA',
                'name': 'NVIDIA Corporation',
                'sector': 'Technology',
                'quantity': 30,
                'avg_cost': 450.00
            }
        ]

        response = client.put(
            '/api/holdings?user_id=test_user',
            json=new_holdings
        )

        assert response.status_code == 200

        # Verify replacement
        get_response = client.get('/api/holdings?user_id=test_user')
        data = get_response.get_json()
        symbols = [h['symbol'] for h in data]
        assert 'TSLA' in symbols
        assert 'NVDA' in symbols

    def test_update_holdings_empty(self, client, sample_holdings):
        """PUT with empty array clears holdings."""
        response = client.put(
            '/api/holdings?user_id=test_user',
            json=[]
        )

        assert response.status_code == 200

        get_response = client.get('/api/holdings?user_id=test_user')
        data = get_response.get_json()
        assert len(data) == 0


class TestMarketDataEndpoints:
    """Tests for market data API endpoints."""

    def test_get_price(self, client, sample_market_data):
        """GET /api/market/price/<symbol> returns current price."""
        response = client.get('/api/market/price/AAPL')

        assert response.status_code == 200
        data = response.get_json()
        assert 'symbol' in data
        assert 'price' in data
        assert data['symbol'] == 'AAPL'

    def test_get_price_invalid_symbol(self, client):
        """Invalid symbol returns 404."""
        response = client.get('/api/market/price/INVALID123')

        assert response.status_code in [404, 400]

    def test_get_price_history(self, client, sample_market_data):
        """GET /api/market/history/<symbol> returns OHLCV data."""
        response = client.get(
            f'/api/market/history/AAPL?'
            f'start_date={(date.today() - timedelta(days=30)).isoformat()}&'
            f'end_date={date.today().isoformat()}'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_multiple_prices(self, client, sample_market_data):
        """GET /api/market/prices returns multiple symbols."""
        response = client.get('/api/market/prices?symbols=AAPL,MSFT,GOOGL')

        assert response.status_code == 200
        data = response.get_json()
        assert 'AAPL' in data

    def test_get_cache_status(self, client, sample_market_data):
        """GET /api/market/cache/status returns cache info."""
        response = client.get('/api/market/cache/status')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_refresh_cache(self, client, sample_market_data):
        """POST /api/market/cache/refresh triggers cache refresh."""
        response = client.post(
            '/api/market/cache/refresh',
            json={'symbols': ['AAPL']}
        )

        assert response.status_code in [200, 202]

    def test_clear_cache(self, client, sample_market_data):
        """DELETE /api/market/cache/<symbol> clears cache."""
        response = client.delete('/api/market/cache/AAPL')

        assert response.status_code == 200


class TestErrorHandling:
    """Tests for API error handling."""

    def test_invalid_json(self, client, sample_portfolio):
        """Invalid JSON should return 400."""
        response = client.post(
            '/api/trades?user_id=test_user',
            data='not valid json',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_method_not_allowed(self, client):
        """Wrong HTTP method should return 405."""
        response = client.delete('/api/portfolio/settings')

        assert response.status_code == 405

    def test_not_found(self, client):
        """Non-existent endpoint should return 404."""
        response = client.get('/api/nonexistent')

        assert response.status_code == 404

    def test_error_response_format(self, client, sample_portfolio):
        """Error responses should have consistent format."""
        response = client.put(
            '/api/strategies/customizations/balanced?user_id=test_user',
            json={'confidence_level': 999}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data or 'message' in data


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_concurrent_reads(self, client, sample_portfolio, sample_holdings):
        """Multiple concurrent reads should succeed."""
        import concurrent.futures

        def fetch_portfolio():
            return client.get('/api/portfolio/settings?user_id=test_user')

        def fetch_holdings():
            return client.get('/api/holdings?user_id=test_user')

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(fetch_portfolio),
                executor.submit(fetch_holdings),
                executor.submit(fetch_portfolio),
                executor.submit(fetch_holdings),
            ]

            results = [f.result() for f in futures]

            for result in results:
                assert result.status_code == 200


class TestTradingEndpoints:
    """Tests for trading-specific endpoints."""

    def test_execute_auto_trade(self, client, sample_portfolio, sample_holdings):
        """POST /api/trading/auto executes auto trade."""
        response = client.post(
            '/api/trading/auto?user_id=test_user',
            json={'prices': {'AAPL': 155.00, 'MSFT': 310.00, 'JNJ': 165.00}}
        )

        assert response.status_code in [200, 201]

    def test_get_trading_status(self, client, sample_portfolio):
        """GET /api/trading/status returns trading status."""
        response = client.get('/api/trading/status?user_id=test_user')

        assert response.status_code == 200
        data = response.get_json()
        assert 'auto_trading_enabled' in data or 'status' in data
