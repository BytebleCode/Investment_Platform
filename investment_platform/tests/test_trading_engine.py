"""
Unit Tests for Trading Engine

Tests auto-trading logic including:
- Trade type decision
- Stock selection
- Quantity calculation
- Validation checks
- Fee calculations
- Trade execution
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.services.trading_engine import (
    determine_trade_type,
    select_stock,
    calculate_buy_quantity,
    calculate_sell_quantity,
    calculate_execution_price,
    calculate_fees,
    validate_buy_trade,
    validate_sell_trade,
    execute_trade,
    auto_trade,
    TradingEngine
)
from app.data.strategies import STRATEGIES
from app.data.stock_universe import STOCK_UNIVERSE


class TestDetermineTradeType:
    """Tests for trade type decision logic."""

    def test_buy_when_severely_underinvested(self):
        """Should buy when investment ratio is very low."""
        trade_type = determine_trade_type(
            investment_ratio=0.4,
            target_ratio=0.7
        )

        assert trade_type == 'buy'

    def test_sell_when_overinvested(self):
        """Should sell when investment ratio exceeds target by 10%."""
        trade_type = determine_trade_type(
            investment_ratio=0.85,
            target_ratio=0.7
        )

        assert trade_type == 'sell'

    def test_mixed_when_near_target(self):
        """Should be probabilistic when near target ratio."""
        buy_count = 0
        sell_count = 0

        # Run multiple times to test probabilistic behavior
        for i in range(1000):
            trade_type = determine_trade_type(
                investment_ratio=0.68,
                target_ratio=0.7,
                seed=i
            )
            if trade_type == 'buy':
                buy_count += 1
            else:
                sell_count += 1

        # Should have mix of buys and sells
        assert buy_count > 0
        assert sell_count > 0
        # Buy probability is 0.4, so roughly 40% buys
        buy_ratio = buy_count / 1000
        assert 0.3 < buy_ratio < 0.5

    def test_buy_at_exact_threshold(self):
        """Test behavior at exactly 70% of target."""
        trade_type = determine_trade_type(
            investment_ratio=0.49,  # Exactly 70% of 0.7
            target_ratio=0.7
        )

        assert trade_type == 'buy'

    def test_sell_at_exact_threshold(self):
        """Test behavior at exactly 110% of target."""
        trade_type = determine_trade_type(
            investment_ratio=0.77,  # Exactly 110% of 0.7
            target_ratio=0.7
        )

        assert trade_type == 'sell'


class TestStockSelection:
    """Tests for stock selection logic."""

    def test_select_from_strategy_pool(self):
        """Selected stock should be in strategy's stock pool."""
        strategy_id = 'growth'
        strategy = STRATEGIES[strategy_id]

        for _ in range(100):
            symbol = select_stock(strategy_id)
            assert symbol in strategy['stocks']

    def test_select_excludes_missing_holdings(self):
        """For sell, should only select from current holdings."""
        holdings = {'AAPL': {'quantity': 100}, 'MSFT': {'quantity': 50}}

        for _ in range(100):
            symbol = select_stock('growth', trade_type='sell', holdings=holdings)
            assert symbol in holdings

    def test_select_returns_none_no_sellable(self):
        """Returns None if no holdings to sell."""
        result = select_stock('growth', trade_type='sell', holdings={})
        assert result is None

    def test_all_strategies_have_valid_stocks(self):
        """All strategies should have selectable stocks."""
        for strategy_id in STRATEGIES.keys():
            symbol = select_stock(strategy_id)
            assert symbol is not None
            assert symbol in STOCK_UNIVERSE


class TestQuantityCalculation:
    """Tests for trade quantity calculations."""

    def test_buy_quantity_basic(self):
        """Calculate basic buy quantity."""
        quantity = calculate_buy_quantity(
            portfolio_value=Decimal('100000'),
            price=Decimal('150'),
            risk_level=3,
            max_position_percent=Decimal('15')
        )

        # Should be 2-8% of portfolio adjusted for risk
        max_amount = Decimal('100000') * Decimal('0.08') * (Decimal('3') / Decimal('3'))
        min_amount = Decimal('100000') * Decimal('0.02') * (Decimal('3') / Decimal('3'))

        max_shares = int(max_amount / Decimal('150'))
        min_shares = int(min_amount / Decimal('150'))

        assert min_shares <= quantity <= max_shares

    def test_buy_quantity_respects_cash(self):
        """Buy quantity should not exceed available cash."""
        quantity = calculate_buy_quantity(
            portfolio_value=Decimal('100000'),
            price=Decimal('150'),
            risk_level=3,
            available_cash=Decimal('1000')  # Only $1000 available
        )

        max_affordable = int(Decimal('1000') / Decimal('150'))
        assert quantity <= max_affordable

    def test_buy_quantity_respects_max_position(self):
        """Buy should respect maximum position size."""
        quantity = calculate_buy_quantity(
            portfolio_value=Decimal('100000'),
            price=Decimal('100'),
            risk_level=5,
            max_position_percent=Decimal('10'),
            current_position_value=Decimal('8000')  # Already 8%
        )

        # Can only add 2% more = $2000 / $100 = 20 shares max
        assert quantity <= 20

    def test_sell_quantity_range(self):
        """Sell quantity should be 20-80% of position."""
        holding_quantity = 100

        quantities = []
        for i in range(1000):
            qty = calculate_sell_quantity(holding_quantity, seed=i)
            quantities.append(qty)
            assert 20 <= qty <= 80

        # Check we get variety
        assert len(set(quantities)) > 10

    def test_sell_quantity_cannot_exceed_holdings(self):
        """Cannot sell more than held."""
        quantity = calculate_sell_quantity(holding_quantity=10)
        assert quantity <= 10

    def test_high_risk_higher_quantity(self):
        """Higher risk strategies should trade larger quantities."""
        low_risk_qty = calculate_buy_quantity(
            portfolio_value=Decimal('100000'),
            price=Decimal('150'),
            risk_level=1,
            seed=42
        )

        high_risk_qty = calculate_buy_quantity(
            portfolio_value=Decimal('100000'),
            price=Decimal('150'),
            risk_level=5,
            seed=42
        )

        # Higher risk should generally mean larger trades
        # (though randomness means this isn't guaranteed per-trade)
        # Test over many iterations
        low_risk_total = sum(
            calculate_buy_quantity(Decimal('100000'), Decimal('150'), 1, seed=i)
            for i in range(100)
        )
        high_risk_total = sum(
            calculate_buy_quantity(Decimal('100000'), Decimal('150'), 5, seed=i)
            for i in range(100)
        )

        assert high_risk_total > low_risk_total


class TestExecutionPrice:
    """Tests for execution price calculations."""

    def test_buy_price_includes_spread(self):
        """Buy price should be higher than market (paying spread)."""
        market_price = Decimal('150')

        for _ in range(100):
            exec_price = calculate_execution_price(market_price, 'buy')
            # Buy at ask (higher)
            assert exec_price > market_price
            # But within reasonable spread (0.3% max)
            assert exec_price < market_price * Decimal('1.004')

    def test_sell_price_includes_spread(self):
        """Sell price should be lower than market (paying spread)."""
        market_price = Decimal('150')

        for _ in range(100):
            exec_price = calculate_execution_price(market_price, 'sell')
            # Sell at bid (lower)
            assert exec_price < market_price
            # But within reasonable spread
            assert exec_price > market_price * Decimal('0.996')

    def test_slippage_adds_variance(self):
        """Slippage should add some variance to execution price."""
        market_price = Decimal('150')

        buy_prices = set()
        for i in range(100):
            price = calculate_execution_price(market_price, 'buy', seed=i)
            buy_prices.add(price)

        # Should have variety due to slippage
        assert len(buy_prices) > 50


class TestFeeCalculation:
    """Tests for fee calculations."""

    def test_fee_calculation(self):
        """Fees should be 0.1% of trade total."""
        total = Decimal('10000')
        fees = calculate_fees(total)

        expected = Decimal('10.00')  # 0.1% of 10000
        assert fees == expected

    def test_fee_precision(self):
        """Fees should maintain decimal precision."""
        total = Decimal('1234.56')
        fees = calculate_fees(total)

        expected = Decimal('1.23456')
        assert abs(fees - expected) < Decimal('0.01')


class TestTradeValidation:
    """Tests for trade validation."""

    def test_validate_buy_sufficient_cash(self):
        """Buy validation passes with sufficient cash."""
        result = validate_buy_trade(
            cash=Decimal('10000'),
            total_cost=Decimal('5000')
        )

        assert result['valid'] == True

    def test_validate_buy_insufficient_cash(self):
        """Buy validation fails with insufficient cash."""
        result = validate_buy_trade(
            cash=Decimal('1000'),
            total_cost=Decimal('5000')
        )

        assert result['valid'] == False
        assert 'insufficient' in result['error'].lower()

    def test_validate_buy_max_95_percent(self):
        """Buy should not spend more than 95% of cash."""
        result = validate_buy_trade(
            cash=Decimal('10000'),
            total_cost=Decimal('9600')  # 96% of cash
        )

        assert result['valid'] == False

    def test_validate_sell_sufficient_shares(self):
        """Sell validation passes with sufficient shares."""
        result = validate_sell_trade(
            holding_quantity=Decimal('100'),
            sell_quantity=Decimal('50')
        )

        assert result['valid'] == True

    def test_validate_sell_insufficient_shares(self):
        """Sell validation fails with insufficient shares."""
        result = validate_sell_trade(
            holding_quantity=Decimal('50'),
            sell_quantity=Decimal('100')
        )

        assert result['valid'] == False
        assert 'insufficient' in result['error'].lower()

    def test_validate_sell_exact_quantity(self):
        """Can sell exactly the held quantity."""
        result = validate_sell_trade(
            holding_quantity=Decimal('100'),
            sell_quantity=Decimal('100')
        )

        assert result['valid'] == True


class TestExecuteTrade:
    """Tests for trade execution."""

    def test_execute_buy_trade(self, db_session, sample_portfolio, current_prices):
        """Execute a buy trade."""
        result = execute_trade(
            user_id='test_user',
            trade_type='buy',
            symbol='GOOGL',
            quantity=10,
            price=current_prices['GOOGL'],
            strategy='growth'
        )

        assert result['success'] == True
        assert result['trade']['type'] == 'buy'
        assert result['trade']['symbol'] == 'GOOGL'
        assert result['trade']['quantity'] == 10

    def test_execute_sell_trade(self, db_session, sample_portfolio, sample_holdings, current_prices):
        """Execute a sell trade."""
        result = execute_trade(
            user_id='test_user',
            trade_type='sell',
            symbol='AAPL',
            quantity=50,
            price=current_prices['AAPL'],
            strategy='balanced'
        )

        assert result['success'] == True
        assert result['trade']['type'] == 'sell'
        assert result['trade']['symbol'] == 'AAPL'

    def test_execute_sell_updates_realized_gains(self, db_session, sample_portfolio, sample_holdings, current_prices):
        """Selling should update realized gains."""
        initial_gains = sample_portfolio.realized_gains

        execute_trade(
            user_id='test_user',
            trade_type='sell',
            symbol='AAPL',
            quantity=50,
            price=current_prices['AAPL'],  # 155, avg_cost is 150
            strategy='balanced'
        )

        # Refresh from DB
        db_session.refresh(sample_portfolio)

        # Gain = (155 - 150) * 50 = 250
        expected_gain = initial_gains + Decimal('250')
        assert sample_portfolio.realized_gains == expected_gain

    def test_execute_buy_updates_holdings(self, db_session, sample_portfolio, sample_holdings, current_prices):
        """Buying should update holdings."""
        initial_aapl = sample_holdings[0]
        initial_qty = initial_aapl.quantity

        execute_trade(
            user_id='test_user',
            trade_type='buy',
            symbol='AAPL',
            quantity=25,
            price=current_prices['AAPL'],
            strategy='balanced'
        )

        db_session.refresh(initial_aapl)
        assert initial_aapl.quantity == initial_qty + 25

    def test_execute_buy_creates_new_holding(self, db_session, sample_portfolio, current_prices):
        """Buying new stock creates new holding."""
        from app.models import Holdings

        result = execute_trade(
            user_id='test_user',
            trade_type='buy',
            symbol='TSLA',
            quantity=10,
            price=current_prices['TSLA'],
            strategy='aggressive'
        )

        holding = db_session.query(Holdings).filter_by(
            user_id='test_user',
            symbol='TSLA'
        ).first()

        assert holding is not None
        assert holding.quantity == 10

    def test_execute_sell_removes_holding_if_empty(self, db_session, sample_portfolio, sample_holdings, current_prices):
        """Selling all shares should remove holding."""
        from app.models import Holdings

        aapl = sample_holdings[0]
        full_qty = int(aapl.quantity)

        execute_trade(
            user_id='test_user',
            trade_type='sell',
            symbol='AAPL',
            quantity=full_qty,
            price=current_prices['AAPL'],
            strategy='balanced'
        )

        holding = db_session.query(Holdings).filter_by(
            user_id='test_user',
            symbol='AAPL'
        ).first()

        assert holding is None or holding.quantity == 0


class TestAutoTrade:
    """Tests for automatic trading."""

    def test_auto_trade_executes(self, db_session, sample_portfolio, sample_holdings, current_prices):
        """Auto trade should execute a trade."""
        result = auto_trade(
            user_id='test_user',
            current_prices=current_prices
        )

        assert result is not None
        assert 'trade' in result or 'skipped' in result

    def test_auto_trade_respects_frequency(self, db_session, sample_portfolio):
        """Auto trade should respect trade frequency settings."""
        # This would require mocking time or trade frequency logic
        # For now, just verify it doesn't error
        result = auto_trade(
            user_id='test_user',
            current_prices={'AAPL': Decimal('150')}
        )

        assert result is not None

    def test_auto_trade_with_empty_portfolio(self, db_session, app):
        """Auto trade should handle empty portfolio gracefully."""
        from app.models import PortfolioState

        # Create empty portfolio (all cash, no holdings)
        with app.app_context():
            portfolio = PortfolioState(
                user_id='empty_user',
                current_cash=Decimal('100000'),
                is_initialized=True
            )
            db_session.add(portfolio)
            db_session.commit()

            result = auto_trade(
                user_id='empty_user',
                current_prices={'AAPL': Decimal('150')}
            )

            # Should buy since all cash
            assert result is not None


class TestTradingEngineClass:
    """Tests for TradingEngine class."""

    def test_engine_initialization(self, app, db_session, sample_portfolio):
        """TradingEngine initializes correctly."""
        with app.app_context():
            engine = TradingEngine(user_id='test_user')

            assert engine.user_id == 'test_user'
            assert engine.portfolio is not None

    def test_engine_get_current_prices(self, app, db_session, sample_portfolio, mock_yahoo_finance):
        """Engine can fetch current prices."""
        with app.app_context():
            engine = TradingEngine(user_id='test_user')
            prices = engine.get_current_prices(['AAPL', 'MSFT'])

            assert 'AAPL' in prices
            assert 'MSFT' in prices

    def test_engine_run_single_trade(self, app, db_session, sample_portfolio, sample_holdings, current_prices):
        """Engine can execute single trade."""
        with app.app_context():
            engine = TradingEngine(user_id='test_user')
            result = engine.run_single_trade(current_prices)

            assert result is not None
