"""
Trading Engine

Implements auto-trading logic including trade type decisions, stock selection,
quantity calculation, execution with spread/slippage, and validation.
"""
import random
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db
from app.models import PortfolioState, Holdings, TradesHistory
from app.data import (
    get_strategy, get_strategy_stocks, get_strategy_risk_level,
    get_target_investment_ratio, get_stock_info, is_valid_symbol
)
from app.services.portfolio_service import (
    calculate_investment_ratio, calculate_invested_value,
    calculate_realized_gain, calculate_new_avg_cost, to_decimal,
    quantize_currency, quantize_price
)

logger = logging.getLogger(__name__)


# Trading constants
MAX_CASH_USAGE_PERCENT = 0.95  # Don't spend more than 95% of cash in one trade
TRADE_FEE_RATE = Decimal('0.001')  # 0.1% trading fee


def generate_trade_id() -> str:
    """Generate unique trade identifier."""
    return str(uuid.uuid4())


def determine_trade_type(
    investment_ratio: float,
    target_ratio: float,
    bias_toward_buy: float = 0.4
) -> str:
    """
    Determine whether to buy or sell based on current vs target allocation.

    Logic:
    - If significantly underinvested (< 70% of target): BUY
    - If significantly overinvested (> 110% of target): SELL
    - Otherwise: random with slight buy bias

    Args:
        investment_ratio: Current investment ratio (0-1)
        target_ratio: Target investment ratio (0-1)
        bias_toward_buy: Probability of buying when in neutral zone

    Returns:
        'buy' or 'sell'
    """
    if investment_ratio < target_ratio * 0.7:
        return 'buy'
    elif investment_ratio > target_ratio * 1.1:
        return 'sell'
    else:
        return 'buy' if random.random() < bias_toward_buy else 'sell'


def select_stock_for_trade(
    trade_type: str,
    strategy_id: str,
    current_holdings: List[Dict],
    exclude_symbols: List[str] = None
) -> Optional[str]:
    """
    Select a stock for trading based on strategy and trade type.

    For BUY: Select from strategy's stock pool
    For SELL: Select from current holdings in strategy's pool

    Args:
        trade_type: 'buy' or 'sell'
        strategy_id: Strategy identifier
        current_holdings: List of current holdings
        exclude_symbols: Symbols to exclude from selection

    Returns:
        Selected stock symbol or None if no valid options
    """
    strategy_stocks = set(get_strategy_stocks(strategy_id))
    exclude = set(exclude_symbols or [])

    if trade_type == 'buy':
        # Select from strategy pool
        available = list(strategy_stocks - exclude)
        if not available:
            return None
        return random.choice(available)

    else:  # sell
        # Select from holdings that are in strategy pool
        holding_symbols = {h['symbol'] for h in current_holdings if h.get('quantity', 0) > 0}
        sellable = list(holding_symbols.intersection(strategy_stocks) - exclude)
        if not sellable:
            # If no holdings in strategy pool, sell any holding
            sellable = list(holding_symbols - exclude)
        if not sellable:
            return None
        return random.choice(sellable)


def calculate_buy_quantity(
    available_cash: float,
    stock_price: float,
    portfolio_value: float,
    risk_level: int,
    max_position_percent: float = 0.15
) -> int:
    """
    Calculate number of shares to buy.

    Logic: Buy 2-8% of portfolio, scaled by risk level

    Args:
        available_cash: Cash available for purchase
        stock_price: Current stock price
        portfolio_value: Total portfolio value
        risk_level: Strategy risk level (1-5)
        max_position_percent: Maximum position size as % of portfolio

    Returns:
        Number of shares to buy (integer)
    """
    if stock_price <= 0 or available_cash <= 0:
        return 0

    # Base percentage: 2-8% of portfolio, scaled by risk
    base_percent = 0.02 + (0.06 * (risk_level / 5))
    target_value = portfolio_value * base_percent

    # Apply max position limit
    max_value = portfolio_value * max_position_percent

    # Apply cash limit (don't spend more than 95% of available)
    cash_limit = available_cash * MAX_CASH_USAGE_PERCENT

    # Take minimum of all limits
    trade_value = min(target_value, max_value, cash_limit)

    # Calculate shares (round down to whole shares)
    shares = int(trade_value / stock_price)

    return max(shares, 0)


def calculate_sell_quantity(
    current_quantity: int,
    min_sell_percent: float = 0.2,
    max_sell_percent: float = 0.8
) -> int:
    """
    Calculate number of shares to sell.

    Sells 20-80% of current position randomly.

    Args:
        current_quantity: Shares currently held
        min_sell_percent: Minimum percentage to sell
        max_sell_percent: Maximum percentage to sell

    Returns:
        Number of shares to sell
    """
    if current_quantity <= 0:
        return 0

    sell_percent = random.uniform(min_sell_percent, max_sell_percent)
    shares = int(current_quantity * sell_percent)

    # Sell at least 1 share if we have any
    return max(shares, 1) if current_quantity > 0 else 0


def calculate_execution_price(
    market_price: float,
    trade_type: str
) -> float:
    """
    Calculate execution price with spread and slippage.

    Simulates realistic execution with:
    - Bid-ask spread: 0.1% - 0.3%
    - Slippage: +/-0.05%

    Args:
        market_price: Current market price
        trade_type: 'buy' or 'sell'

    Returns:
        Execution price
    """
    spread = random.uniform(0.001, 0.003)
    slippage = random.uniform(-0.0005, 0.0005)

    if trade_type == 'buy':
        # Buyer pays more (ask side + slippage)
        execution_price = market_price * (1 + spread/2 + slippage)
    else:
        # Seller receives less (bid side + slippage)
        execution_price = market_price * (1 - spread/2 + slippage)

    return round(execution_price, 4)


def calculate_trade_fees(total_value: float) -> float:
    """
    Calculate trading fees.

    Args:
        total_value: Total trade value

    Returns:
        Fee amount
    """
    return round(float(to_decimal(total_value) * TRADE_FEE_RATE), 2)


def validate_buy_trade(
    symbol: str,
    quantity: int,
    price: float,
    available_cash: float
) -> Tuple[bool, str]:
    """
    Validate a buy trade.

    Checks:
    - Valid symbol
    - Positive quantity
    - Sufficient cash

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not is_valid_symbol(symbol):
        return False, f"Invalid symbol: {symbol}"

    if quantity <= 0:
        return False, "Quantity must be positive"

    if price <= 0:
        return False, "Price must be positive"

    total_cost = quantity * price + calculate_trade_fees(quantity * price)
    if total_cost > available_cash:
        return False, f"Insufficient cash. Need ${total_cost:.2f}, have ${available_cash:.2f}"

    return True, ""


def validate_sell_trade(
    symbol: str,
    quantity: int,
    holdings: List[Dict]
) -> Tuple[bool, str]:
    """
    Validate a sell trade.

    Checks:
    - Valid symbol
    - Positive quantity
    - Sufficient shares held

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not is_valid_symbol(symbol):
        return False, f"Invalid symbol: {symbol}"

    if quantity <= 0:
        return False, "Quantity must be positive"

    # Find holding
    holding = next((h for h in holdings if h['symbol'] == symbol), None)
    if not holding:
        return False, f"No position in {symbol}"

    if quantity > holding.get('quantity', 0):
        return False, f"Cannot sell {quantity} shares, only {holding['quantity']} held"

    return True, ""


def execute_trade(
    user_id: str,
    trade_type: str,
    symbol: str,
    quantity: int,
    price: float,
    strategy: str
) -> Dict:
    """
    Execute a trade and update all relevant records.

    Args:
        user_id: User identifier
        trade_type: 'buy' or 'sell'
        symbol: Stock symbol
        quantity: Number of shares
        price: Execution price per share
        strategy: Strategy used for this trade

    Returns:
        Dict with trade details and status
    """
    symbol = symbol.upper()
    timestamp = datetime.now(timezone.utc)

    # Get stock info
    stock_info = get_stock_info(symbol)
    stock_name = stock_info['name'] if stock_info else symbol
    sector = stock_info['sector'] if stock_info else 'Unknown'

    # Calculate totals
    total = round(quantity * price, 2)
    fees = calculate_trade_fees(total)

    # Get portfolio state
    portfolio = PortfolioState.get_or_create(user_id)
    holdings = Holdings.get_user_holdings(user_id)
    holdings_list = [h.to_dict() for h in holdings]

    # Validate trade
    if trade_type == 'buy':
        is_valid, error = validate_buy_trade(symbol, quantity, price, float(portfolio.current_cash))
    else:
        is_valid, error = validate_sell_trade(symbol, quantity, holdings_list)

    if not is_valid:
        return {
            'success': False,
            'error': error
        }

    # Execute the trade
    trade_id = generate_trade_id()
    realized_gain = Decimal('0')

    try:
        if trade_type == 'buy':
            # Deduct cash
            portfolio.current_cash -= Decimal(str(total + fees))

            # Update or create holding
            holding = Holdings.get_holding(user_id, symbol)
            if holding:
                holding.update_on_buy(quantity, price)
            else:
                holding = Holdings(
                    user_id=user_id,
                    symbol=symbol,
                    name=stock_name,
                    sector=sector,
                    quantity=quantity,
                    avg_cost=price
                )
                db.session.add(holding)

        else:  # sell
            # Get holding for cost basis
            holding = Holdings.get_holding(user_id, symbol)
            avg_cost = float(holding.avg_cost)

            # Calculate realized gain
            realized_gain = calculate_realized_gain(price, quantity, avg_cost)

            # Update holding
            holding.update_on_sell(quantity)

            # Remove holding if quantity is 0
            if holding.quantity <= 0:
                db.session.delete(holding)

            # Add cash (minus fees)
            portfolio.current_cash += Decimal(str(total - fees))

            # Update realized gains
            portfolio.realized_gains += realized_gain

        # Record trade
        trade = TradesHistory(
            user_id=user_id,
            trade_id=trade_id,
            timestamp=timestamp,
            type=trade_type,
            symbol=symbol,
            stock_name=stock_name,
            sector=sector,
            quantity=quantity,
            price=price,
            total=total,
            fees=fees,
            strategy=strategy
        )
        db.session.add(trade)

        # Mark portfolio as initialized
        if not portfolio.is_initialized:
            portfolio.is_initialized = 1

        db.session.commit()

        logger.info(f"Executed {trade_type} trade: {quantity} {symbol} @ ${price:.2f}")

        return {
            'success': True,
            'trade': trade.to_dict(),
            'realized_gain': float(realized_gain) if trade_type == 'sell' else 0,
            'new_cash_balance': float(portfolio.current_cash)
        }

    except Exception as e:
        db.session.rollback()
        logger.error(f"Trade execution failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def auto_trade(
    user_id: str,
    current_prices: Dict[str, float]
) -> Optional[Dict]:
    """
    Execute an automatic trade based on current portfolio state and strategy.

    Args:
        user_id: User identifier
        current_prices: Dict of {symbol: price}

    Returns:
        Trade result dict or None if no trade executed
    """
    # Get portfolio state
    portfolio = PortfolioState.get_or_create(user_id)
    strategy_id = portfolio.current_strategy

    # Get strategy configuration
    strategy = get_strategy(strategy_id)
    if not strategy:
        logger.error(f"Invalid strategy: {strategy_id}")
        return None

    # Get current holdings
    holdings = Holdings.get_user_holdings(user_id)
    holdings_list = [h.to_dict() for h in holdings]

    # Calculate portfolio metrics
    invested_value = calculate_invested_value(holdings_list, current_prices)
    total_value = float(portfolio.current_cash) + float(invested_value)
    investment_ratio = float(calculate_investment_ratio(invested_value, Decimal(str(total_value))))

    # Determine trade type
    target_ratio = get_target_investment_ratio(strategy_id)
    trade_type = determine_trade_type(investment_ratio, target_ratio)

    # Select stock
    symbol = select_stock_for_trade(trade_type, strategy_id, holdings_list)
    if not symbol:
        logger.info(f"No valid stock found for {trade_type} trade")
        return None

    # Get current price
    if symbol not in current_prices:
        logger.warning(f"No price available for {symbol}")
        return None

    market_price = current_prices[symbol]

    # Calculate quantity
    risk_level = get_strategy_risk_level(strategy_id)

    if trade_type == 'buy':
        quantity = calculate_buy_quantity(
            available_cash=float(portfolio.current_cash),
            stock_price=market_price,
            portfolio_value=total_value,
            risk_level=risk_level,
            max_position_percent=strategy.get('max_position_pct', 0.15)
        )
    else:
        holding = next((h for h in holdings_list if h['symbol'] == symbol), None)
        if not holding:
            return None
        quantity = calculate_sell_quantity(int(holding['quantity']))

    if quantity <= 0:
        logger.info(f"Calculated quantity is 0, skipping trade")
        return None

    # Calculate execution price
    execution_price = calculate_execution_price(market_price, trade_type)

    # Execute trade
    result = execute_trade(
        user_id=user_id,
        trade_type=trade_type,
        symbol=symbol,
        quantity=quantity,
        price=execution_price,
        strategy=strategy_id
    )

    return result


class TradingEngine:
    """
    Trading engine class for managing automated trading sessions.
    """

    def __init__(self, user_id: str = 'default'):
        self.user_id = user_id
        self.is_running = False
        self.trades_executed = 0

    def execute_single_trade(self, current_prices: Dict[str, float]) -> Optional[Dict]:
        """Execute a single auto trade."""
        return auto_trade(self.user_id, current_prices)

    def get_trade_recommendation(self, current_prices: Dict[str, float]) -> Dict:
        """
        Get trade recommendation without executing.

        Returns what trade would be executed.
        """
        portfolio = PortfolioState.get_or_create(self.user_id)
        strategy_id = portfolio.current_strategy
        strategy = get_strategy(strategy_id)

        holdings = Holdings.get_user_holdings(self.user_id)
        holdings_list = [h.to_dict() for h in holdings]

        invested_value = calculate_invested_value(holdings_list, current_prices)
        total_value = float(portfolio.current_cash) + float(invested_value)
        investment_ratio = float(calculate_investment_ratio(invested_value, Decimal(str(total_value))))

        target_ratio = get_target_investment_ratio(strategy_id)
        trade_type = determine_trade_type(investment_ratio, target_ratio)

        symbol = select_stock_for_trade(trade_type, strategy_id, holdings_list)

        if not symbol or symbol not in current_prices:
            return {'recommendation': 'hold', 'reason': 'No valid trade available'}

        market_price = current_prices[symbol]
        risk_level = get_strategy_risk_level(strategy_id)

        if trade_type == 'buy':
            quantity = calculate_buy_quantity(
                float(portfolio.current_cash), market_price, total_value, risk_level
            )
        else:
            holding = next((h for h in holdings_list if h['symbol'] == symbol), None)
            quantity = calculate_sell_quantity(int(holding['quantity'])) if holding else 0

        return {
            'recommendation': trade_type,
            'symbol': symbol,
            'quantity': quantity,
            'estimated_price': calculate_execution_price(market_price, trade_type),
            'market_price': market_price,
            'investment_ratio': investment_ratio,
            'target_ratio': target_ratio
        }
