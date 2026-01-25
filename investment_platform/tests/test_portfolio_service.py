"""
Unit Tests for Portfolio Service

Tests portfolio calculations including:
- Valuation calculations
- Gain/loss calculations
- Tax calculations
- Cost basis tracking
"""
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.portfolio_service import (
    calculate_portfolio_value,
    calculate_invested_value,
    calculate_unrealized_gain,
    calculate_unrealized_gain_percent,
    calculate_realized_gain,
    calculate_tax_liability,
    calculate_new_avg_cost,
    calculate_investment_ratio,
    calculate_holding_value,
    calculate_portfolio_metrics
)


class TestPortfolioValuation:
    """Tests for portfolio valuation calculations."""

    def test_portfolio_value_cash_only(self):
        """Portfolio with only cash."""
        cash = Decimal('100000')
        holdings = []
        prices = {}

        total = calculate_portfolio_value(cash, holdings, prices)

        assert total == Decimal('100000')

    def test_portfolio_value_with_holdings(self):
        """Portfolio with cash and holdings."""
        cash = Decimal('50000')
        holdings = [
            {'symbol': 'AAPL', 'quantity': Decimal('100')},
            {'symbol': 'MSFT', 'quantity': Decimal('50')}
        ]
        prices = {
            'AAPL': Decimal('150'),
            'MSFT': Decimal('300')
        }

        total = calculate_portfolio_value(cash, holdings, prices)

        # 50000 + (100 * 150) + (50 * 300) = 50000 + 15000 + 15000 = 80000
        assert total == Decimal('80000')

    def test_portfolio_value_missing_price(self):
        """Holdings without price data should use avg_cost or 0."""
        cash = Decimal('50000')
        holdings = [
            {'symbol': 'AAPL', 'quantity': Decimal('100'), 'avg_cost': Decimal('140')},
            {'symbol': 'UNKNOWN', 'quantity': Decimal('50'), 'avg_cost': Decimal('100')}
        ]
        prices = {'AAPL': Decimal('150')}

        total = calculate_portfolio_value(cash, holdings, prices)

        # 50000 + (100 * 150) + (50 * 100) = 50000 + 15000 + 5000 = 70000
        assert total == Decimal('70000')

    def test_invested_value_calculation(self):
        """Calculate total invested value."""
        holdings = [
            {'symbol': 'AAPL', 'quantity': Decimal('100')},
            {'symbol': 'MSFT', 'quantity': Decimal('50')}
        ]
        prices = {
            'AAPL': Decimal('150'),
            'MSFT': Decimal('300')
        }

        invested = calculate_invested_value(holdings, prices)

        # (100 * 150) + (50 * 300) = 15000 + 15000 = 30000
        assert invested == Decimal('30000')

    def test_invested_value_empty_holdings(self):
        """No holdings means zero invested value."""
        invested = calculate_invested_value([], {})
        assert invested == Decimal('0')


class TestGainLossCalculations:
    """Tests for gain/loss calculations."""

    def test_unrealized_gain_positive(self):
        """Calculate positive unrealized gain."""
        holding = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'avg_cost': Decimal('150')
        }
        current_price = Decimal('160')

        gain = calculate_unrealized_gain(holding, current_price)

        # (160 - 150) * 100 = 1000
        assert gain == Decimal('1000')

    def test_unrealized_gain_negative(self):
        """Calculate negative unrealized gain (loss)."""
        holding = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'avg_cost': Decimal('150')
        }
        current_price = Decimal('140')

        gain = calculate_unrealized_gain(holding, current_price)

        # (140 - 150) * 100 = -1000
        assert gain == Decimal('-1000')

    def test_unrealized_gain_percent_positive(self):
        """Calculate positive percentage gain."""
        holding = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'avg_cost': Decimal('150')
        }
        current_price = Decimal('165')

        percent = calculate_unrealized_gain_percent(holding, current_price)

        # (165 - 150) / 150 * 100 = 10%
        assert percent == Decimal('10')

    def test_unrealized_gain_percent_negative(self):
        """Calculate negative percentage gain."""
        holding = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'avg_cost': Decimal('150')
        }
        current_price = Decimal('135')

        percent = calculate_unrealized_gain_percent(holding, current_price)

        # (135 - 150) / 150 * 100 = -10%
        assert percent == Decimal('-10')

    def test_unrealized_gain_zero_cost_basis(self):
        """Handle zero cost basis edge case."""
        holding = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'avg_cost': Decimal('0')
        }
        current_price = Decimal('150')

        # Should not raise division by zero
        percent = calculate_unrealized_gain_percent(holding, current_price)
        assert percent == Decimal('0') or percent is None

    def test_realized_gain_calculation(self):
        """Calculate realized gain from sale."""
        avg_cost = Decimal('150')
        sale_price = Decimal('170')
        quantity = Decimal('50')

        gain = calculate_realized_gain(avg_cost, sale_price, quantity)

        # (170 - 150) * 50 = 1000
        assert gain == Decimal('1000')

    def test_realized_loss_calculation(self):
        """Calculate realized loss from sale."""
        avg_cost = Decimal('150')
        sale_price = Decimal('130')
        quantity = Decimal('50')

        gain = calculate_realized_gain(avg_cost, sale_price, quantity)

        # (130 - 150) * 50 = -1000
        assert gain == Decimal('-1000')


class TestTaxCalculations:
    """Tests for tax liability calculations."""

    def test_tax_on_gains(self):
        """Calculate tax on realized gains at 37%."""
        realized_gains = Decimal('10000')

        tax = calculate_tax_liability(realized_gains)

        # 10000 * 0.37 = 3700
        assert tax == Decimal('3700')

    def test_tax_on_zero_gains(self):
        """No tax on zero gains."""
        tax = calculate_tax_liability(Decimal('0'))
        assert tax == Decimal('0')

    def test_tax_on_losses(self):
        """No tax liability on losses (negative gains)."""
        realized_gains = Decimal('-5000')

        tax = calculate_tax_liability(realized_gains)

        # Losses don't create tax liability in this simple model
        assert tax == Decimal('0')

    def test_tax_rate_is_37_percent(self):
        """Verify 37% tax rate."""
        gains = Decimal('1000')
        tax = calculate_tax_liability(gains)

        assert tax == gains * Decimal('0.37')

    def test_tax_decimal_precision(self):
        """Tax should maintain decimal precision."""
        gains = Decimal('1234.56')
        tax = calculate_tax_liability(gains)

        expected = Decimal('456.7872')
        assert abs(tax - expected) < Decimal('0.01')


class TestCostBasisTracking:
    """Tests for weighted average cost basis calculations."""

    def test_new_avg_cost_equal_lots(self):
        """Average cost with equal lot sizes."""
        new_avg = calculate_new_avg_cost(
            old_avg_cost=Decimal('100'),
            old_quantity=Decimal('100'),
            buy_price=Decimal('120'),
            buy_quantity=Decimal('100')
        )

        # (100 * 100 + 120 * 100) / 200 = 22000 / 200 = 110
        assert new_avg == Decimal('110')

    def test_new_avg_cost_different_lots(self):
        """Average cost with different lot sizes."""
        new_avg = calculate_new_avg_cost(
            old_avg_cost=Decimal('100'),
            old_quantity=Decimal('100'),
            buy_price=Decimal('150'),
            buy_quantity=Decimal('50')
        )

        # (100 * 100 + 150 * 50) / 150 = (10000 + 7500) / 150 = 116.67
        expected = Decimal('17500') / Decimal('150')
        assert abs(new_avg - expected) < Decimal('0.01')

    def test_new_avg_cost_first_purchase(self):
        """First purchase sets the cost basis."""
        new_avg = calculate_new_avg_cost(
            old_avg_cost=Decimal('0'),
            old_quantity=Decimal('0'),
            buy_price=Decimal('150'),
            buy_quantity=Decimal('100')
        )

        assert new_avg == Decimal('150')

    def test_new_avg_cost_small_addition(self):
        """Small addition to large position."""
        new_avg = calculate_new_avg_cost(
            old_avg_cost=Decimal('100'),
            old_quantity=Decimal('1000'),
            buy_price=Decimal('200'),
            buy_quantity=Decimal('10')
        )

        # (100 * 1000 + 200 * 10) / 1010 = 102000 / 1010 = ~100.99
        expected = Decimal('102000') / Decimal('1010')
        assert abs(new_avg - expected) < Decimal('0.01')

    def test_new_avg_cost_precision(self):
        """Test decimal precision in cost basis."""
        new_avg = calculate_new_avg_cost(
            old_avg_cost=Decimal('123.45'),
            old_quantity=Decimal('33'),
            buy_price=Decimal('126.78'),
            buy_quantity=Decimal('17')
        )

        # Should handle fractional values without error
        assert new_avg > Decimal('0')
        # Verify it's a weighted average (between the two prices)
        assert Decimal('123.45') < new_avg < Decimal('126.78')


class TestInvestmentRatio:
    """Tests for investment ratio calculations."""

    def test_investment_ratio_balanced(self):
        """Calculate investment ratio for balanced portfolio."""
        invested = Decimal('50000')
        total = Decimal('100000')

        ratio = calculate_investment_ratio(invested, total)

        assert ratio == Decimal('0.5')

    def test_investment_ratio_fully_invested(self):
        """Fully invested portfolio (no cash)."""
        invested = Decimal('100000')
        total = Decimal('100000')

        ratio = calculate_investment_ratio(invested, total)

        assert ratio == Decimal('1')

    def test_investment_ratio_all_cash(self):
        """All cash portfolio."""
        invested = Decimal('0')
        total = Decimal('100000')

        ratio = calculate_investment_ratio(invested, total)

        assert ratio == Decimal('0')

    def test_investment_ratio_zero_total(self):
        """Handle zero total value edge case."""
        ratio = calculate_investment_ratio(Decimal('0'), Decimal('0'))
        assert ratio == Decimal('0')


class TestHoldingValueCalculation:
    """Tests for individual holding value calculations."""

    def test_holding_value_basic(self):
        """Calculate basic holding value."""
        holding = {
            'quantity': Decimal('100'),
            'avg_cost': Decimal('150')
        }
        price = Decimal('160')

        value = calculate_holding_value(holding, price)

        assert value == Decimal('16000')

    def test_holding_value_fractional_shares(self):
        """Calculate value with fractional shares."""
        holding = {
            'quantity': Decimal('10.5'),
            'avg_cost': Decimal('100')
        }
        price = Decimal('110')

        value = calculate_holding_value(holding, price)

        assert value == Decimal('1155')


class TestPortfolioMetrics:
    """Tests for comprehensive portfolio metrics."""

    def test_calculate_all_metrics(self):
        """Calculate all portfolio metrics at once."""
        cash = Decimal('50000')
        holdings = [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('100'),
                'avg_cost': Decimal('150')
            },
            {
                'symbol': 'MSFT',
                'quantity': Decimal('50'),
                'avg_cost': Decimal('300')
            }
        ]
        prices = {
            'AAPL': Decimal('160'),
            'MSFT': Decimal('320')
        }
        realized_gains = Decimal('5000')

        metrics = calculate_portfolio_metrics(cash, holdings, prices, realized_gains)

        assert 'total_value' in metrics
        assert 'invested_value' in metrics
        assert 'cash' in metrics
        assert 'unrealized_gain' in metrics
        assert 'unrealized_gain_percent' in metrics
        assert 'realized_gains' in metrics
        assert 'tax_liability' in metrics
        assert 'investment_ratio' in metrics

    def test_metrics_values_correct(self):
        """Verify metric calculations are correct."""
        cash = Decimal('50000')
        holdings = [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('100'),
                'avg_cost': Decimal('150')
            }
        ]
        prices = {'AAPL': Decimal('160')}
        realized_gains = Decimal('1000')

        metrics = calculate_portfolio_metrics(cash, holdings, prices, realized_gains)

        # Total: 50000 + (100 * 160) = 66000
        assert metrics['total_value'] == Decimal('66000')

        # Invested: 100 * 160 = 16000
        assert metrics['invested_value'] == Decimal('16000')

        # Unrealized: (160 - 150) * 100 = 1000
        assert metrics['unrealized_gain'] == Decimal('1000')

        # Tax: 1000 * 0.37 = 370
        assert metrics['tax_liability'] == Decimal('370')

        # Investment ratio: 16000 / 66000 = ~0.242
        expected_ratio = Decimal('16000') / Decimal('66000')
        assert abs(metrics['investment_ratio'] - expected_ratio) < Decimal('0.001')
