"""
Unit Tests for Data Definitions

Tests stock universe, symbol universe, and macro strategy definitions.
"""
import pytest

from app.data.stock_universe import STOCK_UNIVERSE, get_stock_info, get_stocks_by_sector
from app.data.strategies import (
    STRATEGIES, STRATEGY_IDS, get_strategy, get_strategy_stocks,
    get_strategy_risk_level, get_strategy_volatility
)
from app.data.symbol_universe import (
    SYMBOL_UNIVERSE, SECTOR_METADATA, get_symbols_by_path,
    get_all_sectors, get_sector_for_symbol
)


class TestStockUniverse:
    """Tests for stock universe definitions (legacy display metadata)."""

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
        """Beta values should be reasonable (0.1 to 3.5)."""
        for symbol, stock in STOCK_UNIVERSE.items():
            beta = stock['beta']
            assert 0.1 <= beta <= 3.5, f"{symbol} has unusual beta: {beta}"

    def test_get_stock_exists(self):
        """get_stock_info should return stock data for valid symbol."""
        stock = get_stock_info('AAPL')
        assert stock is not None
        assert stock['name'] == 'Apple Inc.'

    def test_get_stock_not_exists(self):
        """get_stock_info should return None for invalid symbol."""
        stock = get_stock_info('INVALID')
        assert stock is None

    def test_get_stocks_by_sector(self):
        """Should return stocks in specified sector."""
        tech_stocks = get_stocks_by_sector('Technology')
        assert len(tech_stocks) > 0
        for symbol, stock in tech_stocks:
            assert stock['sector'] == 'Technology'

    def test_sectors_are_strings(self):
        """All sectors should be strings."""
        for symbol, stock in STOCK_UNIVERSE.items():
            assert isinstance(stock['sector'], str)

    def test_expected_stocks_present(self):
        """Expected major stocks should be in universe."""
        expected = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        for symbol in expected:
            assert symbol in STOCK_UNIVERSE, f"Missing expected stock: {symbol}"


class TestSymbolUniverse:
    """Tests for the new symbol universe (macro strategy sectors)."""

    def test_symbol_universe_has_sectors(self):
        """Symbol universe should have multiple sectors."""
        assert len(SYMBOL_UNIVERSE) >= 10

    def test_expected_sectors_present(self):
        """Expected macro sectors should be defined."""
        expected_sectors = [
            'financials', 'energy', 'materials', 'technology',
            'utilities', 'healthcare', 'consumer_staples',
            'consumer_discretionary', 'industrials', 'real_estate',
            'futures', 'currency'
        ]
        for sector in expected_sectors:
            assert sector in SYMBOL_UNIVERSE, f"Missing sector: {sector}"

    def test_each_sector_has_subsectors(self):
        """Each sector should have at least one subsector."""
        for sector, subsectors in SYMBOL_UNIVERSE.items():
            assert len(subsectors) > 0, f"{sector} has no subsectors"

    def test_each_subsector_has_symbols(self):
        """Each subsector should have at least one symbol."""
        for sector, subsectors in SYMBOL_UNIVERSE.items():
            for subsector, symbols in subsectors.items():
                assert len(symbols) > 0, f"{sector}.{subsector} has no symbols"

    def test_symbols_are_uppercase(self):
        """All symbols in universe should be uppercase."""
        for sector, subsectors in SYMBOL_UNIVERSE.items():
            for subsector, symbols in subsectors.items():
                for symbol in symbols:
                    assert symbol == symbol.upper(), \
                        f"Symbol not uppercase: {symbol} in {sector}.{subsector}"

    def test_get_symbols_by_path(self):
        """Should get symbols using dot notation path."""
        bank_symbols = get_symbols_by_path('financials.banks')
        assert len(bank_symbols) > 0
        assert 'JPM' in bank_symbols

    def test_sector_metadata_exists(self):
        """Each sector should have metadata."""
        for sector in SYMBOL_UNIVERSE.keys():
            metadata = SECTOR_METADATA.get(sector, {})
            assert 'name' in metadata, f"{sector} missing metadata name"
            assert 'color' in metadata, f"{sector} missing metadata color"

    def test_get_sector_for_symbol(self):
        """Should find sector for a symbol."""
        sector, subsector = get_sector_for_symbol('JPM')
        assert sector == 'financials'
        assert subsector == 'banks'

    def test_futures_symbols_have_suffix(self):
        """Futures symbols should have _F suffix."""
        futures_symbols = []
        for subsector in SYMBOL_UNIVERSE.get('futures', {}).values():
            futures_symbols.extend(subsector)

        for symbol in futures_symbols:
            assert symbol.endswith('_F'), f"Futures symbol missing _F: {symbol}"


class TestMacroStrategies:
    """Tests for macro strategy definitions."""

    def test_strategies_not_empty(self):
        """Strategies should have entries."""
        assert len(STRATEGIES) == 5

    def test_strategy_has_required_fields(self):
        """Each strategy should have required fields."""
        required_fields = [
            'id', 'name', 'description', 'risk_level', 'expected_return',
            'color', 'volatility', 'daily_drift', 'trade_frequency_seconds',
            'target_investment_ratio', 'max_position_pct', 'stocks'
        ]

        for strategy_id, strategy in STRATEGIES.items():
            for field in required_fields:
                assert field in strategy, f"{strategy_id} missing field: {field}"

    def test_expected_macro_strategies_present(self):
        """All five macro strategies should be defined."""
        expected = [
            'monetary_policy', 'inflation_hedge', 'growth_expansion',
            'defensive_quality', 'liquidity_cycle'
        ]
        for strategy_id in expected:
            assert strategy_id in STRATEGIES, f"Missing strategy: {strategy_id}"
        assert STRATEGY_IDS == expected

    def test_risk_levels_valid(self):
        """Risk levels should be 1-5."""
        for strategy_id, strategy in STRATEGIES.items():
            risk = strategy['risk_level']
            assert 1 <= risk <= 5, f"{strategy_id} has invalid risk level: {risk}"

    def test_strategy_volatility_positive(self):
        """Strategy volatility should be positive."""
        for strategy_id, strategy in STRATEGIES.items():
            assert strategy['volatility'] > 0, \
                f"{strategy_id} has non-positive volatility"

    def test_get_strategy_exists(self):
        """get_strategy should return strategy data."""
        strategy = get_strategy('monetary_policy')
        assert strategy is not None
        assert strategy['risk_level'] == 3

    def test_get_strategy_not_exists(self):
        """get_strategy should return None for invalid ID."""
        strategy = get_strategy('invalid_strategy')
        assert strategy is None

    def test_defensive_is_low_risk(self):
        """Defensive quality strategy should have low risk."""
        strategy = get_strategy('defensive_quality')
        assert strategy['risk_level'] == 1
        assert strategy['volatility'] < 0.01

    def test_growth_expansion_is_high_risk(self):
        """Growth expansion strategy should have high risk."""
        strategy = get_strategy('growth_expansion')
        assert strategy['risk_level'] == 5
        assert strategy['volatility'] > 0.02

    def test_strategy_expected_returns_format(self):
        """Expected returns should be a tuple with (min, max)."""
        for strategy_id, strategy in STRATEGIES.items():
            ret = strategy['expected_return']
            assert isinstance(ret, tuple), f"{strategy_id} expected_return not tuple"
            assert len(ret) == 2, f"{strategy_id} expected_return should have 2 elements"
            assert ret[0] <= ret[1], f"{strategy_id} min > max"

    def test_strategy_colors_are_hex(self):
        """Strategy colors should be valid hex codes."""
        for strategy_id, strategy in STRATEGIES.items():
            color = strategy['color']
            assert color.startswith('#'), f"{strategy_id} color not hex: {color}"
            assert len(color) == 7, f"{strategy_id} color wrong length: {color}"


class TestMacroSectorAllocation:
    """Tests for macro strategy sector allocations."""

    def test_strategies_have_sector_allocation(self):
        """Each macro strategy should have sector_allocation."""
        for strategy_id, strategy in STRATEGIES.items():
            assert 'sector_allocation' in strategy, \
                f"{strategy_id} missing sector_allocation"
            assert len(strategy['sector_allocation']) > 0

    def test_sector_allocation_weights_valid(self):
        """Sector allocation weights should sum to ~1.0."""
        for strategy_id, strategy in STRATEGIES.items():
            allocation = strategy.get('sector_allocation', {})
            total = sum(allocation.values())
            assert 0.95 <= total <= 1.05, \
                f"{strategy_id} allocation weights sum to {total}, should be ~1.0"

    def test_sector_paths_valid(self):
        """Sector allocation paths should exist in symbol universe."""
        for strategy_id, strategy in STRATEGIES.items():
            allocation = strategy.get('sector_allocation', {})
            for path in allocation.keys():
                symbols = get_symbols_by_path(path)
                assert len(symbols) > 0, \
                    f"{strategy_id} has invalid sector path: {path}"

    def test_strategies_have_max_min_symbols(self):
        """Strategies should have max_symbols and min_symbols."""
        for strategy_id, strategy in STRATEGIES.items():
            assert 'max_symbols' in strategy
            assert 'min_symbols' in strategy
            assert strategy['min_symbols'] <= strategy['max_symbols']

    def test_defensive_focuses_on_safe_sectors(self):
        """Defensive strategy should focus on utilities, staples, healthcare."""
        strategy = get_strategy('defensive_quality')
        allocation = strategy['sector_allocation']

        safe_weight = sum(
            weight for path, weight in allocation.items()
            if any(s in path for s in ['utilities', 'consumer_staples', 'healthcare'])
        )
        assert safe_weight >= 0.5, "Defensive should have >50% in safe sectors"

    def test_inflation_hedge_focuses_on_commodities(self):
        """Inflation hedge should focus on energy, materials, futures."""
        strategy = get_strategy('inflation_hedge')
        allocation = strategy['sector_allocation']

        commodity_weight = sum(
            weight for path, weight in allocation.items()
            if any(s in path for s in ['energy', 'materials', 'futures'])
        )
        assert commodity_weight >= 0.7, "Inflation hedge should have >70% in commodities"


class TestMacroSignals:
    """Tests for macro signal configurations in strategies."""

    def test_strategies_have_signals(self):
        """Each macro strategy should have FRED signal configuration."""
        for strategy_id, strategy in STRATEGIES.items():
            assert 'signals' in strategy, f"{strategy_id} missing signals"
            assert len(strategy['signals']) > 0

    def test_signal_configs_valid(self):
        """Signal configs should have required fields."""
        for strategy_id, strategy in STRATEGIES.items():
            for signal_name, config in strategy.get('signals', {}).items():
                assert 'series' in config, \
                    f"{strategy_id}.{signal_name} missing series"
                assert 'weight' in config, \
                    f"{strategy_id}.{signal_name} missing weight"

    def test_signal_weights_valid(self):
        """Signal weights should sum to ~1.0."""
        for strategy_id, strategy in STRATEGIES.items():
            signals = strategy.get('signals', {})
            total = sum(s.get('weight', 0) for s in signals.values())
            assert 0.95 <= total <= 1.05, \
                f"{strategy_id} signal weights sum to {total}, should be ~1.0"

    def test_defensive_has_inverted_signals(self):
        """Defensive strategy should have some inverted signals."""
        strategy = get_strategy('defensive_quality')
        signals = strategy.get('signals', {})

        has_inverted = any(
            config.get('invert', False)
            for config in signals.values()
        )
        assert has_inverted, "Defensive should have inverted signals (risk-off)"


class TestDynamicStockSelection:
    """Tests for dynamic stock selection from strategies."""

    def test_get_strategy_stocks_returns_list(self):
        """get_strategy_stocks should return a list."""
        for strategy_id in STRATEGY_IDS:
            stocks = get_strategy_stocks(strategy_id)
            assert isinstance(stocks, list)
            assert len(stocks) > 0

    def test_fallback_stocks_exist(self):
        """Each strategy should have fallback static stocks."""
        for strategy_id, strategy in STRATEGIES.items():
            assert 'stocks' in strategy
            assert len(strategy['stocks']) >= 5
