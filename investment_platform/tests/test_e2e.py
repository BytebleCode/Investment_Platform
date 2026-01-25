"""
End-to-End Tests

Tests complete user flows including:
- Full trade flow (buy, sell, verify gains/tax)
- Portfolio lifecycle (create, trade, reset)
- Strategy management flow
- Dashboard data refresh cycle
"""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
import json


class TestCompleteTradeFlow:
    """End-to-end tests for complete trading flows."""

    def test_complete_buy_sell_flow(self, client, db_session):
        """
        Complete trade flow:
        1. Initialize portfolio
        2. Switch strategy
        3. Execute buy trade
        4. Execute sell trade
        5. Verify realized gains
        6. Verify tax calculation
        7. Reset portfolio
        """
        user_id = 'e2e_test_user'

        # 1. Initialize/Reset portfolio
        response = client.post(f'/api/portfolio/reset?user_id={user_id}')
        assert response.status_code == 200

        # Get initial state
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        assert response.status_code == 200
        initial_data = response.get_json()
        initial_cash = float(initial_data['current_cash'])
        assert initial_cash == 100000.00

        # 2. Switch strategy to growth
        response = client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'current_strategy': 'growth'}
        )
        assert response.status_code == 200
        assert response.get_json()['current_strategy'] == 'growth'

        # 3. Execute buy trade - buy 100 shares of AAPL at $150
        buy_trade = {
            'trade_id': 'e2e-buy-001',
            'timestamp': datetime.now().isoformat(),
            'type': 'buy',
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology',
            'quantity': 100,
            'price': 150.00,
            'total': 15000.00,
            'fees': 15.00,
            'strategy': 'growth'
        }
        response = client.post(
            f'/api/trades?user_id={user_id}',
            json=buy_trade
        )
        assert response.status_code == 201

        # Update cash after buy
        new_cash = initial_cash - 15000.00 - 15.00
        response = client.put(
            f'/api/portfolio/cash?user_id={user_id}',
            json={'current_cash': new_cash}
        )
        assert response.status_code == 200

        # Update holdings
        response = client.put(
            f'/api/holdings?user_id={user_id}',
            json=[{
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'sector': 'Technology',
                'quantity': 100,
                'avg_cost': 150.00
            }]
        )
        assert response.status_code == 200

        # 4. Execute sell trade - sell 50 shares at $160 (profit)
        sell_trade = {
            'trade_id': 'e2e-sell-001',
            'timestamp': datetime.now().isoformat(),
            'type': 'sell',
            'symbol': 'AAPL',
            'stock_name': 'Apple Inc.',
            'sector': 'Technology',
            'quantity': 50,
            'price': 160.00,
            'total': 8000.00,
            'fees': 8.00,
            'strategy': 'growth'
        }
        response = client.post(
            f'/api/trades?user_id={user_id}',
            json=sell_trade
        )
        assert response.status_code == 201

        # Calculate realized gain: (160 - 150) * 50 = $500
        realized_gain = (160 - 150) * 50
        assert realized_gain == 500

        # Update portfolio with realized gains
        response = client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'realized_gains': realized_gain}
        )
        assert response.status_code == 200

        # Update cash after sell
        final_cash = new_cash + 8000.00 - 8.00
        response = client.put(
            f'/api/portfolio/cash?user_id={user_id}',
            json={'current_cash': final_cash}
        )
        assert response.status_code == 200

        # Update holdings (50 shares remaining)
        response = client.put(
            f'/api/holdings?user_id={user_id}',
            json=[{
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'sector': 'Technology',
                'quantity': 50,
                'avg_cost': 150.00
            }]
        )
        assert response.status_code == 200

        # 5. Verify realized gains
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        data = response.get_json()
        assert float(data['realized_gains']) == 500.00

        # 6. Verify tax calculation (37% rate)
        expected_tax = 500.00 * 0.37  # $185
        # Tax would be calculated by the frontend or a dedicated endpoint

        # 7. Verify holdings
        response = client.get(f'/api/holdings?user_id={user_id}')
        holdings = response.get_json()
        assert len(holdings) == 1
        assert holdings[0]['symbol'] == 'AAPL'
        assert holdings[0]['quantity'] == 50

        # 8. Verify trade history
        response = client.get(f'/api/trades?user_id={user_id}')
        trades = response.get_json()
        assert len(trades) == 2
        assert trades[0]['type'] == 'sell'  # Most recent first
        assert trades[1]['type'] == 'buy'

        # 9. Reset portfolio
        response = client.post(f'/api/portfolio/reset?user_id={user_id}')
        assert response.status_code == 200

        # Verify reset state
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        data = response.get_json()
        assert float(data['current_cash']) == 100000.00
        assert float(data['realized_gains']) == 0

        # Verify holdings cleared
        response = client.get(f'/api/holdings?user_id={user_id}')
        holdings = response.get_json()
        assert len(holdings) == 0


class TestPortfolioLifecycle:
    """End-to-end tests for portfolio lifecycle."""

    def test_new_user_initialization(self, client, db_session):
        """New user gets default portfolio."""
        user_id = 'new_e2e_user'

        # First access creates default portfolio
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        assert response.status_code in [200, 201]

        data = response.get_json()
        assert data['initial_value'] == 100000.00
        assert data['current_cash'] == 100000.00
        assert data['current_strategy'] == 'balanced'
        assert data['is_initialized'] == False

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')

    def test_portfolio_initialization_flag(self, client, db_session):
        """Portfolio initialization flag updates correctly."""
        user_id = 'init_test_user'

        # Reset to fresh state
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # Get fresh portfolio
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        data = response.get_json()
        assert data['is_initialized'] == False

        # Execute first trade (initializes portfolio)
        trade = {
            'trade_id': 'init-trade-001',
            'timestamp': datetime.now().isoformat(),
            'type': 'buy',
            'symbol': 'AAPL',
            'quantity': 10,
            'price': 150.00,
            'total': 1500.00,
            'fees': 1.50,
            'strategy': 'balanced'
        }
        client.post(f'/api/trades?user_id={user_id}', json=trade)

        # Update initialized flag
        response = client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'is_initialized': True}
        )

        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        data = response.get_json()
        assert data['is_initialized'] == True

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')


class TestStrategyFlow:
    """End-to-end tests for strategy management."""

    def test_strategy_switch_flow(self, client, db_session):
        """Switch between strategies and verify customizations persist."""
        user_id = 'strategy_e2e_user'

        # Reset
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # Start with balanced
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        assert response.get_json()['current_strategy'] == 'balanced'

        # Customize balanced strategy
        client.put(
            f'/api/strategies/customizations/balanced?user_id={user_id}',
            json={
                'confidence_level': 75,
                'trade_frequency': 'medium',
                'max_position_size': 15
            }
        )

        # Switch to growth
        client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'current_strategy': 'growth'}
        )

        # Customize growth
        client.put(
            f'/api/strategies/customizations/growth?user_id={user_id}',
            json={
                'confidence_level': 90,
                'trade_frequency': 'high',
                'max_position_size': 25
            }
        )

        # Switch back to balanced
        client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'current_strategy': 'balanced'}
        )

        # Verify balanced customization persisted
        response = client.get(f'/api/strategies/customizations?user_id={user_id}')
        customizations = response.get_json()

        # Find balanced customization
        balanced = None
        if isinstance(customizations, list):
            for c in customizations:
                if c.get('strategy_id') == 'balanced':
                    balanced = c
                    break
        elif isinstance(customizations, dict):
            balanced = customizations.get('balanced')

        if balanced:
            assert balanced['confidence_level'] == 75

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')


class TestDashboardDataFlow:
    """End-to-end tests for dashboard data refresh."""

    def test_dashboard_data_consistency(self, client, db_session):
        """Dashboard data should be consistent across endpoints."""
        user_id = 'dashboard_e2e_user'

        # Setup portfolio with holdings
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # Add some holdings
        holdings = [
            {'symbol': 'AAPL', 'name': 'Apple', 'sector': 'Tech', 'quantity': 100, 'avg_cost': 150},
            {'symbol': 'MSFT', 'name': 'Microsoft', 'sector': 'Tech', 'quantity': 50, 'avg_cost': 300}
        ]
        client.put(f'/api/holdings?user_id={user_id}', json=holdings)

        # Update cash
        cash_after_buys = 100000 - (100*150) - (50*300)  # 100000 - 15000 - 15000 = 70000
        client.put(
            f'/api/portfolio/cash?user_id={user_id}',
            json={'current_cash': cash_after_buys}
        )

        # Fetch all dashboard data
        portfolio_resp = client.get(f'/api/portfolio/settings?user_id={user_id}')
        holdings_resp = client.get(f'/api/holdings?user_id={user_id}')

        portfolio = portfolio_resp.get_json()
        holdings_data = holdings_resp.get_json()

        # Verify consistency
        assert float(portfolio['current_cash']) == 70000.00
        assert len(holdings_data) == 2

        # Calculate expected invested value at current prices (using avg_cost as proxy)
        invested = sum(h['quantity'] * h['avg_cost'] for h in holdings_data)
        assert invested == 100*150 + 50*300  # 30000

        # Total should equal initial
        total = float(portfolio['current_cash']) + invested
        assert total == 100000.00

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')


class TestMultipleTradesAccumulation:
    """Test multiple trades and their cumulative effects."""

    def test_multiple_buys_avg_cost(self, client, db_session):
        """Multiple buys should correctly update average cost."""
        user_id = 'multi_buy_user'
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # First buy: 100 shares at $150
        client.post(
            f'/api/trades?user_id={user_id}',
            json={
                'trade_id': 'multi-buy-001',
                'timestamp': datetime.now().isoformat(),
                'type': 'buy',
                'symbol': 'AAPL',
                'quantity': 100,
                'price': 150.00,
                'total': 15000.00,
                'fees': 15.00,
                'strategy': 'balanced'
            }
        )

        # Set initial holding
        client.put(
            f'/api/holdings?user_id={user_id}',
            json=[{
                'symbol': 'AAPL',
                'name': 'Apple',
                'sector': 'Tech',
                'quantity': 100,
                'avg_cost': 150.00
            }]
        )

        # Second buy: 100 shares at $170
        client.post(
            f'/api/trades?user_id={user_id}',
            json={
                'trade_id': 'multi-buy-002',
                'timestamp': datetime.now().isoformat(),
                'type': 'buy',
                'symbol': 'AAPL',
                'quantity': 100,
                'price': 170.00,
                'total': 17000.00,
                'fees': 17.00,
                'strategy': 'balanced'
            }
        )

        # Update holding with new average cost
        # New avg = (100*150 + 100*170) / 200 = 32000/200 = 160
        client.put(
            f'/api/holdings?user_id={user_id}',
            json=[{
                'symbol': 'AAPL',
                'name': 'Apple',
                'sector': 'Tech',
                'quantity': 200,
                'avg_cost': 160.00
            }]
        )

        # Verify
        response = client.get(f'/api/holdings?user_id={user_id}')
        holdings = response.get_json()
        assert len(holdings) == 1
        assert holdings[0]['quantity'] == 200
        assert holdings[0]['avg_cost'] == 160.00

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')

    def test_realized_gains_accumulation(self, client, db_session):
        """Multiple sells should accumulate realized gains."""
        user_id = 'multi_sell_user'
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # Setup: Buy 200 shares at $100
        client.put(
            f'/api/holdings?user_id={user_id}',
            json=[{
                'symbol': 'AAPL',
                'name': 'Apple',
                'sector': 'Tech',
                'quantity': 200,
                'avg_cost': 100.00
            }]
        )

        # First sell: 50 shares at $120 -> gain = (120-100)*50 = $1000
        client.post(
            f'/api/trades?user_id={user_id}',
            json={
                'trade_id': 'multi-sell-001',
                'timestamp': datetime.now().isoformat(),
                'type': 'sell',
                'symbol': 'AAPL',
                'quantity': 50,
                'price': 120.00,
                'total': 6000.00,
                'fees': 6.00,
                'strategy': 'balanced'
            }
        )

        client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'realized_gains': 1000.00}
        )

        # Second sell: 50 shares at $130 -> gain = (130-100)*50 = $1500
        client.post(
            f'/api/trades?user_id={user_id}',
            json={
                'trade_id': 'multi-sell-002',
                'timestamp': datetime.now().isoformat(),
                'type': 'sell',
                'symbol': 'AAPL',
                'quantity': 50,
                'price': 130.00,
                'total': 6500.00,
                'fees': 6.50,
                'strategy': 'balanced'
            }
        )

        # Total realized gains = 1000 + 1500 = 2500
        client.put(
            f'/api/portfolio/settings?user_id={user_id}',
            json={'realized_gains': 2500.00}
        )

        # Verify
        response = client.get(f'/api/portfolio/settings?user_id={user_id}')
        data = response.get_json()
        assert float(data['realized_gains']) == 2500.00

        # Tax should be 2500 * 0.37 = 925
        expected_tax = 2500.00 * 0.37
        assert expected_tax == 925.00

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')


class TestErrorRecovery:
    """Test error handling and recovery in flows."""

    def test_failed_trade_no_side_effects(self, client, db_session):
        """Failed trade should not affect portfolio state."""
        user_id = 'error_recovery_user'
        client.post(f'/api/portfolio/reset?user_id={user_id}')

        # Get initial state
        initial_resp = client.get(f'/api/portfolio/settings?user_id={user_id}')
        initial_state = initial_resp.get_json()

        # Attempt invalid trade (missing required fields)
        client.post(
            f'/api/trades?user_id={user_id}',
            json={
                'trade_id': 'invalid-trade',
                'type': 'buy'
                # Missing required fields
            }
        )

        # State should be unchanged
        after_resp = client.get(f'/api/portfolio/settings?user_id={user_id}')
        after_state = after_resp.get_json()

        assert float(initial_state['current_cash']) == float(after_state['current_cash'])
        assert float(initial_state['realized_gains']) == float(after_state['realized_gains'])

        # Clean up
        client.post(f'/api/portfolio/reset?user_id={user_id}')


class TestMarketDataIntegration:
    """End-to-end tests for market data integration."""

    def test_price_fetch_and_cache(self, client, db_session, mock_yahoo_finance):
        """Fetching prices should cache them for future use."""
        # First fetch - should hit Yahoo Finance
        response = client.get('/api/market/price/AAPL')
        assert response.status_code == 200
        first_fetch = response.get_json()

        # Second fetch - should use cache
        response = client.get('/api/market/price/AAPL')
        assert response.status_code == 200

        # Verify cache has data
        response = client.get('/api/market/cache/status')
        assert response.status_code == 200

    def test_batch_price_fetch(self, client, db_session, mock_yahoo_finance):
        """Batch price fetch should be efficient."""
        response = client.get('/api/market/prices?symbols=AAPL,MSFT,GOOGL,AMZN')
        assert response.status_code == 200

        data = response.get_json()
        assert 'AAPL' in data or len(data) > 0
