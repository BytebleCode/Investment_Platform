"""
Simple Validation Functions

Provides input validation for all API endpoints to ensure
data integrity and prevent injection attacks.
No external dependencies required.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, date

from app.data.strategies import STRATEGIES
from app.data.stock_universe import STOCK_UNIVERSE


class ValidationError(Exception):
    """Raised when validation fails."""
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, dict) else {'_error': errors}
        super().__init__(str(errors))


def validate_decimal(value, field_name, min_val=None, max_val=None, required=True):
    """Validate a decimal value."""
    if value is None:
        if required:
            return None, f"{field_name} is required"
        return None, None

    try:
        dec_val = Decimal(str(value))
        if min_val is not None and dec_val < Decimal(str(min_val)):
            return None, f"{field_name} must be at least {min_val}"
        if max_val is not None and dec_val > Decimal(str(max_val)):
            return None, f"{field_name} must be at most {max_val}"
        return dec_val, None
    except (InvalidOperation, ValueError):
        return None, f"{field_name} must be a valid number"


def validate_int(value, field_name, min_val=None, max_val=None, required=True):
    """Validate an integer value."""
    if value is None:
        if required:
            return None, f"{field_name} is required"
        return None, None

    try:
        int_val = int(value)
        if min_val is not None and int_val < min_val:
            return None, f"{field_name} must be at least {min_val}"
        if max_val is not None and int_val > max_val:
            return None, f"{field_name} must be at most {max_val}"
        return int_val, None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a valid integer"


def validate_string(value, field_name, min_len=None, max_len=None, choices=None, required=True):
    """Validate a string value."""
    if value is None or value == '':
        if required:
            return None, f"{field_name} is required"
        return None, None

    str_val = str(value)
    if min_len is not None and len(str_val) < min_len:
        return None, f"{field_name} must be at least {min_len} characters"
    if max_len is not None and len(str_val) > max_len:
        return None, f"{field_name} must be at most {max_len} characters"
    if choices is not None and str_val not in choices:
        return None, f"{field_name} must be one of: {', '.join(choices)}"
    return str_val, None


def validate_bool(value, field_name, required=True):
    """Validate a boolean value."""
    if value is None:
        if required:
            return None, f"{field_name} is required"
        return None, None

    if isinstance(value, bool):
        return value, None
    if str(value).lower() in ('true', '1', 'yes'):
        return True, None
    if str(value).lower() in ('false', '0', 'no'):
        return False, None
    return None, f"{field_name} must be a boolean"


def validate_datetime(value, field_name, required=True):
    """Validate a datetime value."""
    if value is None:
        if required:
            return None, f"{field_name} is required"
        return None, None

    if isinstance(value, datetime):
        return value, None

    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')), None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a valid datetime"


def validate_date(value, field_name, required=True):
    """Validate a date value."""
    if value is None:
        if required:
            return None, f"{field_name} is required"
        return None, None

    if isinstance(value, date):
        return value, None

    try:
        return date.fromisoformat(str(value)), None
    except (ValueError, TypeError):
        return None, f"{field_name} must be a valid date (YYYY-MM-DD)"


def validate_symbol(value, field_name='symbol', required=True):
    """Validate a stock symbol."""
    val, err = validate_string(value, field_name, min_len=1, max_len=10, required=required)
    if err:
        return None, err
    if val is None:
        return None, None

    # Symbol should be uppercase alphanumeric (allowing dots for BRK.A etc)
    if not val.replace('.', '').isalnum():
        return None, f"{field_name} must be alphanumeric"
    if val != val.upper():
        return None, f"{field_name} must be uppercase"
    return val, None


def validate_portfolio_settings(data):
    """Validate portfolio settings update."""
    errors = {}
    validated = {}

    if 'initial_value' in data:
        val, err = validate_decimal(data['initial_value'], 'initial_value',
                                    min_val=1000, max_val=100000000, required=False)
        if err:
            errors['initial_value'] = err
        elif val is not None:
            validated['initial_value'] = val

    if 'current_cash' in data:
        val, err = validate_decimal(data['current_cash'], 'current_cash',
                                    min_val=0, required=False)
        if err:
            errors['current_cash'] = err
        elif val is not None:
            validated['current_cash'] = val

    if 'current_strategy' in data:
        val, err = validate_string(data['current_strategy'], 'current_strategy',
                                   choices=list(STRATEGIES.keys()), required=False)
        if err:
            errors['current_strategy'] = err
        elif val is not None:
            validated['current_strategy'] = val

    if 'is_initialized' in data:
        val, err = validate_bool(data['is_initialized'], 'is_initialized', required=False)
        if err:
            errors['is_initialized'] = err
        elif val is not None:
            validated['is_initialized'] = val

    if 'realized_gains' in data:
        val, err = validate_decimal(data['realized_gains'], 'realized_gains', required=False)
        if err:
            errors['realized_gains'] = err
        elif val is not None:
            validated['realized_gains'] = val

    return validated, errors if errors else None


def validate_cash_update(data):
    """Validate cash balance update."""
    errors = {}
    validated = {}

    val, err = validate_decimal(data.get('current_cash'), 'current_cash', min_val=0)
    if err:
        errors['current_cash'] = err
    else:
        validated['current_cash'] = val

    return validated, errors if errors else None


def validate_strategy_customization(data):
    """Validate strategy customization update."""
    errors = {}
    validated = {}

    if 'confidence_level' in data:
        val, err = validate_int(data['confidence_level'], 'confidence_level',
                               min_val=10, max_val=100, required=False)
        if err:
            errors['confidence_level'] = err
        elif val is not None:
            validated['confidence_level'] = val

    if 'trade_frequency' in data:
        val, err = validate_string(data['trade_frequency'], 'trade_frequency',
                                   choices=['low', 'medium', 'high'], required=False)
        if err:
            errors['trade_frequency'] = err
        elif val is not None:
            validated['trade_frequency'] = val

    if 'max_position_size' in data:
        val, err = validate_int(data['max_position_size'], 'max_position_size',
                               min_val=5, max_val=50, required=False)
        if err:
            errors['max_position_size'] = err
        elif val is not None:
            validated['max_position_size'] = val

    if 'stop_loss_percent' in data:
        val, err = validate_int(data['stop_loss_percent'], 'stop_loss_percent',
                               min_val=5, max_val=30, required=False)
        if err:
            errors['stop_loss_percent'] = err
        elif val is not None:
            validated['stop_loss_percent'] = val

    if 'take_profit_percent' in data:
        val, err = validate_int(data['take_profit_percent'], 'take_profit_percent',
                               min_val=10, max_val=100, required=False)
        if err:
            errors['take_profit_percent'] = err
        elif val is not None:
            validated['take_profit_percent'] = val

    if 'auto_rebalance' in data:
        val, err = validate_bool(data['auto_rebalance'], 'auto_rebalance', required=False)
        if err:
            errors['auto_rebalance'] = err
        elif val is not None:
            validated['auto_rebalance'] = val

    if 'reinvest_dividends' in data:
        val, err = validate_bool(data['reinvest_dividends'], 'reinvest_dividends', required=False)
        if err:
            errors['reinvest_dividends'] = err
        elif val is not None:
            validated['reinvest_dividends'] = val

    return validated, errors if errors else None


def validate_trade(data):
    """Validate trade creation."""
    errors = {}
    validated = {}

    # Required fields
    val, err = validate_string(data.get('trade_id'), 'trade_id', min_len=1, max_len=100)
    if err:
        errors['trade_id'] = err
    else:
        validated['trade_id'] = val

    val, err = validate_string(data.get('type'), 'type', choices=['buy', 'sell'])
    if err:
        errors['type'] = err
    else:
        validated['type'] = val

    val, err = validate_symbol(data.get('symbol'), 'symbol')
    if err:
        errors['symbol'] = err
    else:
        validated['symbol'] = val

    val, err = validate_int(data.get('quantity'), 'quantity', min_val=1)
    if err:
        errors['quantity'] = err
    else:
        validated['quantity'] = val

    val, err = validate_decimal(data.get('price'), 'price', min_val=Decimal('0.0001'))
    if err:
        errors['price'] = err
    else:
        validated['price'] = val

    val, err = validate_decimal(data.get('total'), 'total', min_val=Decimal('0.01'))
    if err:
        errors['total'] = err
    else:
        validated['total'] = val

    # Optional fields
    val, err = validate_datetime(data.get('timestamp'), 'timestamp', required=False)
    if err:
        errors['timestamp'] = err
    else:
        validated['timestamp'] = val if val else datetime.now(timezone.utc)

    val, err = validate_string(data.get('stock_name'), 'stock_name', max_len=100, required=False)
    if not err and val:
        validated['stock_name'] = val

    val, err = validate_string(data.get('sector'), 'sector', max_len=50, required=False)
    if not err and val:
        validated['sector'] = val

    val, err = validate_decimal(data.get('fees'), 'fees', min_val=0, required=False)
    if err:
        errors['fees'] = err
    else:
        validated['fees'] = val if val is not None else Decimal('0')

    val, err = validate_string(data.get('strategy'), 'strategy',
                              choices=list(STRATEGIES.keys()), required=False)
    if not err and val:
        validated['strategy'] = val

    # Look up stock info if not provided
    symbol = validated.get('symbol')
    if symbol and symbol in STOCK_UNIVERSE:
        stock = STOCK_UNIVERSE[symbol]
        if 'stock_name' not in validated:
            validated['stock_name'] = stock.get('name')
        if 'sector' not in validated:
            validated['sector'] = stock.get('sector')

    return validated, errors if errors else None


def validate_holding(data):
    """Validate holding data."""
    errors = {}
    validated = {}

    val, err = validate_symbol(data.get('symbol'), 'symbol')
    if err:
        errors['symbol'] = err
    else:
        validated['symbol'] = val

    val, err = validate_string(data.get('name'), 'name', max_len=100, required=False)
    if not err and val:
        validated['name'] = val

    val, err = validate_string(data.get('sector'), 'sector', max_len=50, required=False)
    if not err and val:
        validated['sector'] = val

    val, err = validate_decimal(data.get('quantity'), 'quantity', min_val=0)
    if err:
        errors['quantity'] = err
    else:
        validated['quantity'] = val

    val, err = validate_decimal(data.get('avg_cost'), 'avg_cost', min_val=0)
    if err:
        errors['avg_cost'] = err
    else:
        validated['avg_cost'] = val

    return validated, errors if errors else None


def validate_holdings_list(data):
    """Validate bulk holdings update."""
    if not isinstance(data, dict) or 'holdings' not in data:
        return None, {'holdings': 'holdings list is required'}

    holdings_list = data['holdings']
    if not isinstance(holdings_list, list):
        return None, {'holdings': 'holdings must be a list'}

    validated_holdings = []
    all_errors = {}

    for i, holding in enumerate(holdings_list):
        validated, errors = validate_holding(holding)
        if errors:
            all_errors[f'holdings[{i}]'] = errors
        else:
            validated_holdings.append(validated)

    if all_errors:
        return None, all_errors

    return {'holdings': validated_holdings}, None


def validate_market_data_request(data):
    """Validate market data request."""
    errors = {}
    validated = {}

    if 'symbol' in data:
        val, err = validate_symbol(data['symbol'], 'symbol', required=False)
        if err:
            errors['symbol'] = err
        elif val:
            validated['symbol'] = val

    if 'symbols' in data:
        symbols = data['symbols']
        if not isinstance(symbols, list):
            errors['symbols'] = 'symbols must be a list'
        elif len(symbols) > 50:
            errors['symbols'] = 'maximum 50 symbols per request'
        else:
            validated_symbols = []
            for i, sym in enumerate(symbols):
                val, err = validate_symbol(sym, f'symbols[{i}]')
                if err:
                    errors[f'symbols[{i}]'] = err
                else:
                    validated_symbols.append(val)
            if not errors.get('symbols'):
                validated['symbols'] = validated_symbols

    if 'start_date' in data:
        val, err = validate_date(data['start_date'], 'start_date', required=False)
        if err:
            errors['start_date'] = err
        elif val:
            validated['start_date'] = val

    if 'end_date' in data:
        val, err = validate_date(data['end_date'], 'end_date', required=False)
        if err:
            errors['end_date'] = err
        elif val:
            validated['end_date'] = val

    if 'interval' in data:
        val, err = validate_string(data['interval'], 'interval',
                                   choices=['daily', 'weekly', 'monthly'], required=False)
        if err:
            errors['interval'] = err
        elif val:
            validated['interval'] = val
    else:
        validated['interval'] = 'daily'

    return validated, errors if errors else None


def validate_cache_refresh(data):
    """Validate cache refresh request."""
    errors = {}

    symbols = data.get('symbols')
    if not symbols:
        return None, {'symbols': 'symbols list is required'}

    if not isinstance(symbols, list):
        return None, {'symbols': 'symbols must be a list'}

    if len(symbols) < 1 or len(symbols) > 20:
        return None, {'symbols': 'must provide 1-20 symbols'}

    validated_symbols = []
    for i, sym in enumerate(symbols):
        val, err = validate_symbol(sym, f'symbols[{i}]')
        if err:
            errors[f'symbols[{i}]'] = err
        else:
            validated_symbols.append(val)

    if errors:
        return None, errors

    return {'symbols': validated_symbols}, None


def validate_auto_trade_request(data):
    """Validate auto-trade execution request."""
    prices = data.get('prices')
    if not prices:
        return None, {'prices': 'prices dictionary is required'}

    if not isinstance(prices, dict):
        return None, {'prices': 'prices must be a dictionary'}

    validated_prices = {}
    errors = {}

    for symbol, price in prices.items():
        sym_val, sym_err = validate_symbol(symbol, f'prices.{symbol}')
        if sym_err:
            errors[f'prices.{symbol}'] = sym_err
            continue

        price_val, price_err = validate_decimal(price, f'prices.{symbol}', min_val=0)
        if price_err:
            errors[f'prices.{symbol}'] = price_err
        else:
            validated_prices[sym_val] = price_val

    if errors:
        return None, errors

    return {'prices': validated_prices}, None


def validate_request(validator_func, data):
    """
    Validate request data using a validator function.

    Args:
        validator_func: Validation function to use
        data: Dictionary to validate

    Returns:
        Tuple of (validated_data, errors)
    """
    return validator_func(data)


def get_validation_errors(errors):
    """
    Convert error dictionary to a flat list of error messages.

    Args:
        errors: Error dictionary

    Returns:
        List of error message strings
    """
    if errors is None:
        return []

    messages = []

    def flatten_errors(err_dict, prefix=''):
        for field, field_errors in err_dict.items():
            field_name = f"{prefix}{field}" if prefix else field
            if isinstance(field_errors, dict):
                flatten_errors(field_errors, f"{field_name}.")
            elif isinstance(field_errors, list):
                for error in field_errors:
                    messages.append(f"{field_name}: {error}")
            else:
                messages.append(f"{field_name}: {field_errors}")

    flatten_errors(errors)
    return messages
