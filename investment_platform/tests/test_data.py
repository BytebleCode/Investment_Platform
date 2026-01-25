"""
Unit Tests for Data Definitions

Tests stock universe and strategy definitions.
"""
import pytest
from decimal import Decimal

from app.data.stock_universe import STOCK_UNIVERSE, get_stock, get_stocks_by_sector
from app.data.strategies import STRATEGIES, get_strategy, validate_strategy_params


class TestStockUniverse:
    """Tests for stock universe definitions."""

    def test_stock_universe_not_empty(self):
        """Stock universe should have entries."""
        assert len(STOCK_UNIVERSE) > 0

    def test_stock_has_required_fields(self):
        """Each stock should have required fields."""
        required_fields = ['name', 'sector', 'base_price', 'beta']

        for symbol, stock in STOCK_UNIVERSE.items():
            for field in required_fields:
                assert field in stock, f"{symbol} missing field: {field}"

    def test_stock_symbols_uppercase(self):
        """All stock symbols should be uppercase."""
        for symbol in STOCK_UNIVERSE.keys():
            assert symbol == symbol.upper(), f"Symbol not uppercase: {symbol}"

    def test_stock_base_prices_positive(self):
        """All base prices should be positive."""
        for symbol, stock in STOCK_UNIVERSE.items():
            assert stock['base_price'] > 0, f"{symbol} has non-positive base price"

    def test_stock_betas_valid(self):
        """Beta values should be reasonable (0.1 to 3.0)."""
        for symbol, stock in STOCK_UNIVERSE.items():
            beta = stock['beta']
            assert 0.1 <= beta <= 3.0, f"{symbol} has unusual beta: {beta}"

    def test_get_stock_exists(self):
        """get_stock should return stock data for valid symbol."""
        stock = get_stock('AAPL')
        assert stock is not None
        assert stock['name'] == 'Apple Inc.'

    def test_get_stock_not_exists(self):
        """get_stock should return None for invalid symbol."""
        stock = get_stock('INVALID')
        assert stock is None

    def test_get_stocks_by_sector(self):
        """Should return stocks in specified sector."""
        tech_stocks = get_stocks_by_sector('Technology')
        assert len(tech_stocks) > 0
        for symbol, stock in tech_stocks.items():
            assert stock['sector'] == 'Technology'

    def test_sectors_are_strings(self):
        """All sectors should be strings."""
        for symbol, stock in STOCK_UNIVERSE.items():
            assert isinstance(stock['sector'], str)

    def test_expected_stocks_present(self):
        """Expected major stocks should be in universe."""
        expected = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        for symbol in expected:
            assert symbol in STOCK_UNIVERSE, f"Missing expected stock: {symbol}"


class TestStrategies:
    """Tests for strategy definitions."""

    def test_strategies_not_empty(self):
        """Strategies should have entries."""
        assert len(STRATEGIES) > 0

    def test_strategy_has_required_fields(self):
        """Each strategy should have required fields."""
        required_fields = ['name', 'risk_level', 'expected_return', 'stocks', 'volatility', 'drift']

        for strategy_id, strategy in STRATEGIES.items():
            for field in required_fields:
                assert field in strategy, f"{strategy_id} missing field: {field}"

    def test_expected_strategies_present(self):
        """All five strategies should be defined."""
        expected = ['conservative', 'growth', 'value', 'balanced', 'aggressive']
        for strategy_id in expected:
            assert strategy_id in STRATEGIES, f"Missing strategy: {strategy_id}"

    def test_risk_levels_valid(self):
        """Risk levels should be 1-5."""
        for strategy_id, strategy in STRATEGIES.items():
            risk = strategy['risk_level']
            assert 1 <= risk <= 5, f"{strategy_id} has invalid risk level: {risk}"

    def test_strategy_stocks_exist(self):
        """All stocks in strategies should exist in universe."""
        for strategy_id, strategy in STRATEGIES.items():
            for symbol in strategy['stocks']:
                assert symbol in STOCK_UNIVERSE, \
                    f"{strategy_id} references unknown stock: {symbol}"

    def test_strategy_volatility_positive(self):
        """Strategy volatility should be positive."""
        for strategy_id, strategy in STRATEGIES.items():
            assert strategy['volatility'] > 0, \
                f"{strategy_id} has non-positive volatility"

    def test_get_strategy_exists(self):
        """get_strategy should return strategy data."""
        strategy = get_strategy('balanced')
        assert strategy is not None
        assert strategy['risk_level'] == 3

    def test_get_strategy_not_exists(self):
        """get_strategy should return None for invalid ID."""
        strategy = get_strategy('invalid_strategy')
        assert strategy is None

    def test_conservative_is_low_risk(self):
        """Conservative strategy should have low risk."""
        strategy = get_strategy('conservative')
        assert strategy['risk_level'] == 1
        assert strategy['volatility'] < 0.01

    def test_aggressive_is_high_risk(self):
        """Aggressive strategy should have high risk."""
        strategy = get_strategy('aggressive')
        assert strategy['risk_level'] == 5
        assert strategy['volatility'] > 0.02

    def test_strategy_expected_returns_format(self):
        """Expected returns should be a dict with min/max."""
        for strategy_id, strategy in STRATEGIES.items():
            ret = strategy['expected_return']
            assert isinstance(ret, dict), f"{strategy_id} expected_return not dict"
            assert 'min' in ret, f"{strategy_id} expected_return missing min"
            assert 'max' in ret, f"{strategy_id} expected_return missing max"
            assert ret['min'] <= ret['max'], f"{strategy_id} min > max"

    def test_validate_strategy_params_valid(self):
        """Valid params should pass validation."""
        params = {
            'confidence_level': 75,
            'trade_frequency': 'medium',
            'max_position_size': 15,
            'stop_loss_percent': 10,
            'take_profit_percent': 25
        }
        result = validate_strategy_params(params)
        assert result['valid'] == True

    def test_validate_strategy_params_invalid_confidence(self):
        """Invalid confidence level should fail."""
        params = {'confidence_level': 150}
        result = validate_strategy_params(params)
        assert result['valid'] == False

    def test_validate_strategy_params_invalid_frequency(self):
        """Invalid trade frequency should fail."""
        params = {'trade_frequency': 'ultra_fast'}
        result = validate_strategy_params(params)
        assert result['valid'] == False


class TestStrategyStockAllocation:
    """Tests for strategy stock allocations."""

    def test_conservative_stocks_are_stable(self):
        """Conservative stocks should have low beta."""
        strategy = get_strategy('conservative')
        for symbol in strategy['stocks']:
            stock = get_stock(symbol)
            assert stock['beta'] <= 1.5, \
                f"{symbol} in conservative has high beta: {stock['beta']}"

    def test_aggressive_stocks_are_volatile(self):
        """Aggressive stocks should have higher beta."""
        strategy = get_strategy('aggressive')
        avg_beta = sum(
            get_stock(s)['beta'] for s in strategy['stocks']
        ) / len(strategy['stocks'])
        assert avg_beta >= 1.0, f"Aggressive avg beta too low: {avg_beta}"

    def test_balanced_has_diverse_sectors(self):
        """Balanced strategy should span multiple sectors."""
        strategy = get_strategy('balanced')
        sectors = set()
        for symbol in strategy['stocks']:
            stock = get_stock(symbol)
            sectors.add(stock['sector'])
        assert len(sectors) >= 3, "Balanced should have at least 3 sectors"

    def test_each_strategy_has_enough_stocks(self):
        """Each strategy should have at least 5 stocks."""
        for strategy_id, strategy in STRATEGIES.items():
            assert len(strategy['stocks']) >= 5, \
                f"{strategy_id} has too few stocks: {len(strategy['stocks'])}"
