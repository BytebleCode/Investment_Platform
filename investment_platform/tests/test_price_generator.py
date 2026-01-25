"""
Unit Tests for Price Generator Service

Tests the Geometric Brownian Motion price simulation for:
- Price bounds validation
- Volatility behavior
- Reproducibility with seeds
- Portfolio history generation
"""
import pytest
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.price_generator import (
    generate_price,
    generate_prices_batch,
    generate_portfolio_history
)
from app.data.strategies import STRATEGIES


class TestGeneratePrice:
    """Tests for single price generation."""

    def test_positive_price_output(self):
        """Generated prices should always be positive."""
        for _ in range(1000):
            price = generate_price(
                current_price=100.0,
                beta=1.0,
                volatility=0.02,
                drift=0.0003
            )
            assert price > 0, "Price should never be negative"

    def test_extreme_volatility_still_positive(self):
        """Even with extreme volatility, prices stay positive."""
        np.random.seed(42)
        for _ in range(1000):
            price = generate_price(
                current_price=1.0,
                beta=2.0,
                volatility=0.05,
                drift=0.0
            )
            assert price > 0, "Price should be positive even with high volatility"

    def test_zero_volatility_equals_drift(self):
        """With zero volatility, price change equals drift."""
        np.random.seed(42)
        current = 100.0
        drift = 0.001

        # With zero volatility, only drift affects price
        price = generate_price(current, beta=1.0, volatility=0.0, drift=drift)

        # Price should be approximately current * (1 + drift)
        expected = current * (1 + drift)
        assert abs(price - expected) < 0.01

    def test_higher_beta_more_variance(self):
        """Higher beta should result in more price variance."""
        np.random.seed(42)
        current = 100.0
        n_samples = 1000

        low_beta_prices = []
        high_beta_prices = []

        for i in range(n_samples):
            np.random.seed(i)
            low_beta_prices.append(
                generate_price(current, beta=0.5, volatility=0.02)
            )
            np.random.seed(i)
            high_beta_prices.append(
                generate_price(current, beta=2.0, volatility=0.02)
            )

        low_beta_std = np.std(low_beta_prices)
        high_beta_std = np.std(high_beta_prices)

        assert high_beta_std > low_beta_std, \
            "Higher beta should produce more variance"

    def test_price_bounds_reasonable(self):
        """Prices should stay within reasonable bounds for normal conditions."""
        np.random.seed(42)
        current = 100.0

        for _ in range(100):
            price = generate_price(current, beta=1.0, volatility=0.02)
            # Single day movement should be less than 20% typically
            assert 80.0 < price < 120.0

    def test_different_seeds_different_results(self):
        """Different seeds should produce different prices."""
        current = 100.0

        np.random.seed(42)
        price1 = generate_price(current, beta=1.0)

        np.random.seed(123)
        price2 = generate_price(current, beta=1.0)

        assert price1 != price2


class TestGeneratePricesBatch:
    """Tests for batch price generation."""

    def test_batch_returns_all_symbols(self):
        """Batch generation should return prices for all symbols."""
        holdings = {
            'AAPL': {'quantity': 100, 'avg_cost': 150.0},
            'MSFT': {'quantity': 50, 'avg_cost': 300.0},
            'GOOGL': {'quantity': 25, 'avg_cost': 140.0}
        }
        current_prices = {
            'AAPL': 155.0,
            'MSFT': 310.0,
            'GOOGL': 142.0
        }

        new_prices = generate_prices_batch(holdings, current_prices)

        assert 'AAPL' in new_prices
        assert 'MSFT' in new_prices
        assert 'GOOGL' in new_prices

    def test_batch_all_positive(self):
        """All batch generated prices should be positive."""
        holdings = {
            'AAPL': {'quantity': 100, 'avg_cost': 150.0},
            'TSLA': {'quantity': 10, 'avg_cost': 240.0}
        }
        current_prices = {
            'AAPL': 155.0,
            'TSLA': 245.0
        }

        for _ in range(100):
            new_prices = generate_prices_batch(holdings, current_prices)
            for symbol, price in new_prices.items():
                assert price > 0, f"{symbol} price should be positive"

    def test_batch_with_seed_reproducible(self):
        """Batch generation with seed should be reproducible."""
        holdings = {'AAPL': {'quantity': 100, 'avg_cost': 150.0}}
        current_prices = {'AAPL': 155.0}

        np.random.seed(42)
        prices1 = generate_prices_batch(holdings, current_prices)

        np.random.seed(42)
        prices2 = generate_prices_batch(holdings, current_prices)

        assert prices1['AAPL'] == prices2['AAPL']


class TestGeneratePortfolioHistory:
    """Tests for portfolio history generation."""

    def test_history_length_matches_days(self):
        """History should have correct number of entries."""
        history = generate_portfolio_history(
            initial_value=100000,
            strategy='balanced',
            num_days=30,
            seed=42
        )

        assert len(history) == 30

    def test_history_starts_at_initial_value(self):
        """First entry should be close to initial value."""
        history = generate_portfolio_history(
            initial_value=100000,
            strategy='balanced',
            num_days=30,
            seed=42
        )

        # First value should be approximately initial value
        first_value = history[0]['value']
        assert 99000 < first_value < 101000

    def test_history_dates_sequential(self):
        """Dates should be sequential."""
        history = generate_portfolio_history(
            initial_value=100000,
            strategy='balanced',
            num_days=10,
            seed=42
        )

        for i in range(1, len(history)):
            current_date = datetime.fromisoformat(history[i]['date'])
            prev_date = datetime.fromisoformat(history[i-1]['date'])
            assert current_date > prev_date

    def test_history_contains_required_fields(self):
        """Each history entry should have required fields."""
        history = generate_portfolio_history(
            initial_value=100000,
            strategy='balanced',
            num_days=5,
            seed=42
        )

        for entry in history:
            assert 'date' in entry
            assert 'value' in entry
            assert isinstance(entry['value'], (int, float))

    def test_different_strategies_different_volatility(self):
        """Different strategies should produce different volatility levels."""
        n_days = 100
        seed = 42

        # Generate histories for different strategies
        conservative = generate_portfolio_history(100000, 'conservative', n_days, seed)
        aggressive = generate_portfolio_history(100000, 'aggressive', n_days, seed)

        # Calculate standard deviations
        conservative_values = [h['value'] for h in conservative]
        aggressive_values = [h['value'] for h in aggressive]

        conservative_std = np.std(conservative_values)
        aggressive_std = np.std(aggressive_values)

        # Aggressive should have higher volatility
        assert aggressive_std > conservative_std, \
            "Aggressive strategy should have higher volatility"

    def test_seeded_generation_reproducible(self):
        """Same seed should produce identical history."""
        history1 = generate_portfolio_history(100000, 'balanced', 30, seed=42)
        history2 = generate_portfolio_history(100000, 'balanced', 30, seed=42)

        for i in range(len(history1)):
            assert history1[i]['value'] == history2[i]['value']
            assert history1[i]['date'] == history2[i]['date']

    def test_different_seeds_different_history(self):
        """Different seeds should produce different histories."""
        history1 = generate_portfolio_history(100000, 'balanced', 30, seed=42)
        history2 = generate_portfolio_history(100000, 'balanced', 30, seed=123)

        # At least some values should differ
        differences = sum(
            1 for i in range(len(history1))
            if history1[i]['value'] != history2[i]['value']
        )
        assert differences > 0

    def test_all_strategies_valid(self):
        """All defined strategies should produce valid history."""
        for strategy_id in STRATEGIES.keys():
            history = generate_portfolio_history(
                initial_value=100000,
                strategy=strategy_id,
                num_days=10,
                seed=42
            )

            assert len(history) == 10
            for entry in history:
                assert entry['value'] > 0

    def test_invalid_strategy_uses_default(self):
        """Invalid strategy should fall back to balanced."""
        history = generate_portfolio_history(
            initial_value=100000,
            strategy='invalid_strategy',
            num_days=10,
            seed=42
        )

        # Should not raise, should use default
        assert len(history) == 10


class TestPriceStatistics:
    """Statistical tests for price generation quality."""

    def test_mean_returns_near_drift(self):
        """Average returns should be approximately equal to drift."""
        np.random.seed(42)
        current = 100.0
        drift = 0.0003
        n_samples = 10000

        returns = []
        for _ in range(n_samples):
            new_price = generate_price(current, beta=1.0, volatility=0.02, drift=drift)
            daily_return = (new_price - current) / current
            returns.append(daily_return)

        mean_return = np.mean(returns)

        # Mean return should be close to drift (within 1 standard error)
        assert abs(mean_return - drift) < 0.001

    def test_returns_approximately_normal(self):
        """Returns should be approximately normally distributed."""
        np.random.seed(42)
        current = 100.0
        n_samples = 10000

        returns = []
        for _ in range(n_samples):
            new_price = generate_price(current, beta=1.0, volatility=0.02)
            daily_return = (new_price - current) / current
            returns.append(daily_return)

        # Check that returns are roughly symmetric (skewness near 0)
        # Simple skewness calculation without scipy
        returns_array = np.array(returns)
        mean = np.mean(returns_array)
        std = np.std(returns_array)
        skewness = np.mean(((returns_array - mean) / std) ** 3)
        assert abs(skewness) < 0.15, "Returns should be approximately symmetric"

    def test_volatility_scales_with_beta(self):
        """Volatility should scale linearly with beta."""
        np.random.seed(42)
        current = 100.0
        base_vol = 0.02
        n_samples = 5000

        beta_1_returns = []
        beta_2_returns = []

        for i in range(n_samples):
            np.random.seed(i)
            price1 = generate_price(current, beta=1.0, volatility=base_vol)
            np.random.seed(i)
            price2 = generate_price(current, beta=2.0, volatility=base_vol)

            beta_1_returns.append((price1 - current) / current)
            beta_2_returns.append((price2 - current) / current)

        std_1 = np.std(beta_1_returns)
        std_2 = np.std(beta_2_returns)

        # Beta 2 should have approximately 2x the volatility
        ratio = std_2 / std_1
        assert 1.8 < ratio < 2.2, f"Volatility ratio should be approx 2, got {ratio}"
