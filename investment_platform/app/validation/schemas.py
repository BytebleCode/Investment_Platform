"""
Marshmallow Validation Schemas

Provides input validation for all API endpoints to ensure
data integrity and prevent injection attacks.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from decimal import Decimal
from datetime import datetime, timezone

from app.data.strategies import STRATEGIES
from app.data.stock_universe import STOCK_UNIVERSE


class PortfolioSettingsSchema(Schema):
    """Schema for portfolio settings updates."""

    initial_value = fields.Decimal(
        places=2,
        validate=validate.Range(min=Decimal('1000'), max=Decimal('100000000')),
        load_default=None
    )
    current_cash = fields.Decimal(
        places=2,
        validate=validate.Range(min=Decimal('0')),
        load_default=None
    )
    current_strategy = fields.Str(
        validate=validate.OneOf(list(STRATEGIES.keys())),
        load_default=None
    )
    is_initialized = fields.Bool(load_default=None)
    realized_gains = fields.Decimal(
        places=2,
        load_default=None
    )

    @validates('current_cash')
    def validate_cash(self, value):
        """Cash cannot be negative."""
        if value is not None and value < 0:
            raise ValidationError('Cash balance cannot be negative')


class CashUpdateSchema(Schema):
    """Schema for cash balance updates."""

    current_cash = fields.Decimal(
        required=True,
        places=2,
        validate=validate.Range(min=Decimal('0'))
    )


class StrategyCustomizationSchema(Schema):
    """Schema for strategy customization updates."""

    confidence_level = fields.Int(
        validate=validate.Range(min=10, max=100),
        load_default=None
    )
    trade_frequency = fields.Str(
        validate=validate.OneOf(['low', 'medium', 'high']),
        load_default=None
    )
    max_position_size = fields.Int(
        validate=validate.Range(min=5, max=50),
        load_default=None
    )
    stop_loss_percent = fields.Int(
        validate=validate.Range(min=5, max=30),
        load_default=None
    )
    take_profit_percent = fields.Int(
        validate=validate.Range(min=10, max=100),
        load_default=None
    )
    auto_rebalance = fields.Bool(load_default=None)
    reinvest_dividends = fields.Bool(load_default=None)


class TradeSchema(Schema):
    """Schema for trade creation."""

    trade_id = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    timestamp = fields.DateTime(
        required=False,
        load_default=None
    )
    type = fields.Str(
        required=True,
        validate=validate.OneOf(['buy', 'sell'])
    )
    symbol = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10)
    )
    stock_name = fields.Str(
        validate=validate.Length(max=100),
        load_default=None
    )
    sector = fields.Str(
        validate=validate.Length(max=50),
        load_default=None
    )
    quantity = fields.Int(
        required=True,
        validate=validate.Range(min=1)
    )
    price = fields.Decimal(
        required=True,
        places=4,
        validate=validate.Range(min=Decimal('0.0001'))
    )
    total = fields.Decimal(
        required=True,
        places=2,
        validate=validate.Range(min=Decimal('0.01'))
    )
    fees = fields.Decimal(
        places=2,
        validate=validate.Range(min=Decimal('0')),
        load_default=Decimal('0')
    )
    strategy = fields.Str(
        validate=validate.OneOf(list(STRATEGIES.keys())),
        load_default=None
    )

    @validates('symbol')
    def validate_symbol(self, value):
        """Symbol should be uppercase alphanumeric."""
        if not value.replace('.', '').isalnum():
            raise ValidationError('Symbol must be alphanumeric')
        if value != value.upper():
            raise ValidationError('Symbol must be uppercase')

    @validates('total')
    def validate_total(self, value):
        """Total should be roughly quantity * price."""
        # Validation is approximate due to fees
        pass

    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now(timezone.utc)

        # Look up stock info if not provided
        symbol = data.get('symbol')
        if symbol and symbol in STOCK_UNIVERSE:
            stock = STOCK_UNIVERSE[symbol]
            if not data.get('stock_name'):
                data['stock_name'] = stock.get('name')
            if not data.get('sector'):
                data['sector'] = stock.get('sector')

        return data


class HoldingSchema(Schema):
    """Schema for holding data."""

    symbol = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10)
    )
    name = fields.Str(
        validate=validate.Length(max=100),
        load_default=None
    )
    sector = fields.Str(
        validate=validate.Length(max=50),
        load_default=None
    )
    quantity = fields.Decimal(
        required=True,
        places=4,
        validate=validate.Range(min=Decimal('0'))
    )
    avg_cost = fields.Decimal(
        required=True,
        places=4,
        validate=validate.Range(min=Decimal('0'))
    )

    @validates('symbol')
    def validate_symbol(self, value):
        """Symbol should be uppercase."""
        if value != value.upper():
            raise ValidationError('Symbol must be uppercase')


class HoldingsListSchema(Schema):
    """Schema for bulk holdings update."""

    holdings = fields.List(
        fields.Nested(HoldingSchema),
        required=True
    )


class MarketDataRequestSchema(Schema):
    """Schema for market data requests."""

    symbol = fields.Str(
        validate=validate.Length(min=1, max=10)
    )
    symbols = fields.List(
        fields.Str(validate=validate.Length(min=1, max=10)),
        validate=validate.Length(max=50)  # Max 50 symbols per request
    )
    start_date = fields.Date()
    end_date = fields.Date()
    interval = fields.Str(
        validate=validate.OneOf(['daily', 'weekly', 'monthly']),
        load_default='daily'
    )

    @validates('symbols')
    def validate_symbols(self, value):
        """All symbols should be uppercase."""
        if value:
            for symbol in value:
                if symbol != symbol.upper():
                    raise ValidationError(f'Symbol {symbol} must be uppercase')


class CacheRefreshSchema(Schema):
    """Schema for cache refresh requests."""

    symbols = fields.List(
        fields.Str(validate=validate.Length(min=1, max=10)),
        required=True,
        validate=validate.Length(min=1, max=20)  # Max 20 symbols per refresh
    )


class AutoTradeRequestSchema(Schema):
    """Schema for auto-trade execution."""

    prices = fields.Dict(
        keys=fields.Str(),
        values=fields.Decimal(places=4),
        required=True
    )


def validate_request(schema_class, data: dict) -> tuple:
    """
    Validate request data against a schema.

    Args:
        schema_class: Marshmallow schema class
        data: Dictionary to validate

    Returns:
        Tuple of (validated_data, errors)
    """
    schema = schema_class()
    try:
        result = schema.load(data)
        return result, None
    except ValidationError as err:
        return None, err.messages


def get_validation_errors(errors: dict) -> list:
    """
    Convert Marshmallow errors to a flat list of error messages.

    Args:
        errors: Marshmallow error dictionary

    Returns:
        List of error message strings
    """
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
