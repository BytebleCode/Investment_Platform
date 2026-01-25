"""
Portfolio Calculation Service

Handles all portfolio-related calculations including valuation, gains/losses,
tax computation, and cost basis tracking.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

from app.config import Config


# Tax rate for short-term capital gains
TAX_RATE = Decimal(str(Config.DEFAULT_TAX_RATE))


def to_decimal(value) -> Decimal:
    """Convert value to Decimal safely."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_currency(value: Decimal) -> Decimal:
    """Round to 2 decimal places for currency."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def quantize_price(value: Decimal) -> Decimal:
    """Round to 4 decimal places for price."""
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def calculate_portfolio_value(
    current_cash: Decimal,
    holdings: List[Dict],
    current_prices: Dict[str, float]
) -> Decimal:
    """
    Calculate total portfolio value.

    Formula: total_value = current_cash + sum(holding.quantity * current_price)

    Args:
        current_cash: Available cash balance
        holdings: List of holdings with 'symbol' and 'quantity'
        current_prices: Dict of {symbol: price}

    Returns:
        Total portfolio value as Decimal
    """
    current_cash = to_decimal(current_cash)
    invested_value = Decimal('0')

    for holding in holdings:
        symbol = holding['symbol']
        quantity = to_decimal(holding['quantity'])

        if symbol in current_prices:
            price = to_decimal(current_prices[symbol])
            invested_value += quantity * price

    return quantize_currency(current_cash + invested_value)


def calculate_invested_value(
    holdings: List[Dict],
    current_prices: Dict[str, float]
) -> Decimal:
    """
    Calculate total value invested in stocks.

    Args:
        holdings: List of holdings with 'symbol' and 'quantity'
        current_prices: Dict of {symbol: price}

    Returns:
        Total invested value
    """
    invested = Decimal('0')

    for holding in holdings:
        symbol = holding['symbol']
        quantity = to_decimal(holding['quantity'])

        if symbol in current_prices:
            price = to_decimal(current_prices[symbol])
            invested += quantity * price

    return quantize_currency(invested)


def calculate_unrealized_gain(
    holding: Dict,
    current_price: float
) -> Tuple[Decimal, Decimal]:
    """
    Calculate unrealized gain for a single holding.

    Formulas:
        gain = (current_price - avg_cost) * quantity
        gain_percent = ((current_price - avg_cost) / avg_cost) * 100

    Args:
        holding: Dict with 'quantity' and 'avg_cost'
        current_price: Current market price

    Returns:
        Tuple of (gain_amount, gain_percent)
    """
    quantity = to_decimal(holding['quantity'])
    avg_cost = to_decimal(holding['avg_cost'])
    current = to_decimal(current_price)

    # Calculate dollar gain
    gain = (current - avg_cost) * quantity

    # Calculate percentage gain
    if avg_cost > 0:
        gain_percent = ((current - avg_cost) / avg_cost) * Decimal('100')
    else:
        gain_percent = Decimal('0')

    return quantize_currency(gain), quantize_price(gain_percent)


def calculate_total_unrealized_gains(
    holdings: List[Dict],
    current_prices: Dict[str, float]
) -> Decimal:
    """
    Calculate total unrealized gains across all holdings.

    Args:
        holdings: List of holdings with 'symbol', 'quantity', 'avg_cost'
        current_prices: Dict of {symbol: price}

    Returns:
        Total unrealized gains (positive or negative)
    """
    total_gain = Decimal('0')

    for holding in holdings:
        symbol = holding['symbol']
        if symbol in current_prices:
            gain, _ = calculate_unrealized_gain(holding, current_prices[symbol])
            total_gain += gain

    return quantize_currency(total_gain)


def calculate_realized_gain(
    sale_price: float,
    quantity_sold: int,
    avg_cost: float
) -> Decimal:
    """
    Calculate realized gain from a sale.

    Formula: realized_gain = sale_proceeds - (avg_cost * quantity_sold)

    Args:
        sale_price: Price per share at sale
        quantity_sold: Number of shares sold
        avg_cost: Average cost basis per share

    Returns:
        Realized gain (positive) or loss (negative)
    """
    sale_price = to_decimal(sale_price)
    quantity = to_decimal(quantity_sold)
    cost = to_decimal(avg_cost)

    sale_proceeds = sale_price * quantity
    cost_basis = cost * quantity

    return quantize_currency(sale_proceeds - cost_basis)


def calculate_estimated_tax(realized_gains: Decimal) -> Decimal:
    """
    Calculate estimated tax liability on realized gains.

    Uses short-term capital gains rate (37% by default).
    Only applies to positive gains (no tax on losses).

    Args:
        realized_gains: Total realized gains

    Returns:
        Estimated tax amount (0 if gains are negative)
    """
    gains = to_decimal(realized_gains)

    if gains <= 0:
        return Decimal('0')

    tax = gains * TAX_RATE
    return quantize_currency(tax)


def calculate_new_avg_cost(
    old_avg_cost: float,
    old_quantity: int,
    buy_price: float,
    buy_quantity: int
) -> Decimal:
    """
    Calculate new weighted average cost after a purchase.

    Formula: new_avg = (old_avg * old_qty + buy_price * buy_qty) / (old_qty + buy_qty)

    Args:
        old_avg_cost: Previous average cost per share
        old_quantity: Previous quantity held
        buy_price: Price of new shares
        buy_quantity: Number of new shares

    Returns:
        New weighted average cost per share
    """
    old_avg = to_decimal(old_avg_cost)
    old_qty = to_decimal(old_quantity)
    new_price = to_decimal(buy_price)
    new_qty = to_decimal(buy_quantity)

    total_cost = (old_avg * old_qty) + (new_price * new_qty)
    total_quantity = old_qty + new_qty

    if total_quantity == 0:
        return Decimal('0')

    return quantize_price(total_cost / total_quantity)


def calculate_investment_ratio(
    invested_value: Decimal,
    total_value: Decimal
) -> Decimal:
    """
    Calculate what percentage of portfolio is invested vs cash.

    Formula: ratio = invested_value / total_value

    Args:
        invested_value: Value in stocks
        total_value: Total portfolio value

    Returns:
        Ratio as decimal (e.g., 0.75 = 75% invested)
    """
    invested = to_decimal(invested_value)
    total = to_decimal(total_value)

    if total == 0:
        return Decimal('0')

    ratio = invested / total
    return quantize_price(ratio)


def calculate_total_return(
    current_value: Decimal,
    initial_value: Decimal
) -> Tuple[Decimal, Decimal]:
    """
    Calculate total return (dollar amount and percentage).

    Args:
        current_value: Current portfolio value
        initial_value: Initial portfolio value

    Returns:
        Tuple of (dollar_return, percent_return)
    """
    current = to_decimal(current_value)
    initial = to_decimal(initial_value)

    dollar_return = current - initial

    if initial > 0:
        percent_return = (dollar_return / initial) * Decimal('100')
    else:
        percent_return = Decimal('0')

    return quantize_currency(dollar_return), quantize_price(percent_return)


def calculate_position_value(quantity: float, price: float) -> Decimal:
    """Calculate value of a position."""
    return quantize_currency(to_decimal(quantity) * to_decimal(price))


def calculate_position_weight(
    position_value: Decimal,
    total_portfolio_value: Decimal
) -> Decimal:
    """
    Calculate position weight as percentage of portfolio.

    Args:
        position_value: Value of the position
        total_portfolio_value: Total portfolio value

    Returns:
        Weight as percentage (e.g., 15.5 for 15.5%)
    """
    if total_portfolio_value == 0:
        return Decimal('0')

    weight = (to_decimal(position_value) / to_decimal(total_portfolio_value)) * Decimal('100')
    return quantize_price(weight)


def calculate_sector_allocation(
    holdings: List[Dict],
    current_prices: Dict[str, float]
) -> Dict[str, Decimal]:
    """
    Calculate portfolio allocation by sector.

    Args:
        holdings: List of holdings with 'symbol', 'sector', 'quantity'
        current_prices: Dict of {symbol: price}

    Returns:
        Dict of {sector: total_value}
    """
    sector_values = {}

    for holding in holdings:
        symbol = holding['symbol']
        sector = holding.get('sector', 'Unknown')
        quantity = to_decimal(holding['quantity'])

        if symbol in current_prices:
            value = quantity * to_decimal(current_prices[symbol])
            sector_values[sector] = sector_values.get(sector, Decimal('0')) + value

    return {k: quantize_currency(v) for k, v in sector_values.items()}


def get_portfolio_summary(
    portfolio_state: Dict,
    holdings: List[Dict],
    current_prices: Dict[str, float]
) -> Dict:
    """
    Generate comprehensive portfolio summary.

    Args:
        portfolio_state: Dict with initial_value, current_cash, realized_gains
        holdings: List of holdings
        current_prices: Current market prices

    Returns:
        Dict with all portfolio metrics
    """
    initial_value = to_decimal(portfolio_state['initial_value'])
    current_cash = to_decimal(portfolio_state['current_cash'])
    realized_gains = to_decimal(portfolio_state.get('realized_gains', 0))

    invested_value = calculate_invested_value(holdings, current_prices)
    total_value = current_cash + invested_value
    unrealized_gains = calculate_total_unrealized_gains(holdings, current_prices)

    dollar_return, percent_return = calculate_total_return(total_value, initial_value)
    investment_ratio = calculate_investment_ratio(invested_value, total_value)
    estimated_tax = calculate_estimated_tax(realized_gains)

    return {
        'initial_value': float(initial_value),
        'current_cash': float(current_cash),
        'invested_value': float(invested_value),
        'total_value': float(total_value),
        'unrealized_gains': float(unrealized_gains),
        'realized_gains': float(realized_gains),
        'total_return_dollar': float(dollar_return),
        'total_return_percent': float(percent_return),
        'investment_ratio': float(investment_ratio),
        'estimated_tax': float(estimated_tax),
        'num_positions': len(holdings),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
