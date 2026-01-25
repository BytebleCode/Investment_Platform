"""
CSV Storage Backend

Provides file-based storage using CSV files as a fallback
when SQLite/DB2 are not available.
"""
import csv
import os
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock


class CSVStorage:
    """
    CSV-based storage backend for the investment platform.

    Each model type is stored in a separate CSV file in the data directory.
    Thread-safe with file locking for concurrent access.
    """

    # CSV file names for each model
    FILES = {
        'portfolio_state': 'portfolio_state.csv',
        'holdings': 'holdings.csv',
        'trades_history': 'trades_history.csv',
        'strategy_customizations': 'strategy_customizations.csv',
        'market_data_cache': 'market_data_cache.csv',
        'market_data_metadata': 'market_data_metadata.csv',
        'user_strategies': 'user_strategies.csv',
        'user_strategy_stocks': 'user_strategy_stocks.csv',
    }

    # Column definitions for each model (order matters for CSV)
    COLUMNS = {
        'portfolio_state': [
            'id', 'user_id', 'initial_value', 'current_cash', 'current_strategy',
            'is_initialized', 'realized_gains', 'created_at', 'updated_at'
        ],
        'holdings': [
            'id', 'user_id', 'symbol', 'name', 'sector', 'quantity', 'avg_cost',
            'created_at', 'updated_at'
        ],
        'trades_history': [
            'id', 'user_id', 'trade_id', 'timestamp', 'type', 'symbol', 'stock_name',
            'sector', 'quantity', 'price', 'total', 'fees', 'strategy', 'created_at'
        ],
        'strategy_customizations': [
            'id', 'user_id', 'strategy_id', 'confidence_level', 'trade_frequency',
            'max_position_size', 'stop_loss_percent', 'take_profit_percent',
            'auto_rebalance', 'reinvest_dividends', 'created_at', 'updated_at'
        ],
        'market_data_cache': [
            'id', 'symbol', 'date', 'open', 'high', 'low', 'close', 'adj_close',
            'volume', 'fetched_at'
        ],
        'market_data_metadata': [
            'id', 'symbol', 'last_fetch_date', 'earliest_date', 'latest_date',
            'total_records', 'last_updated', 'fetch_status'
        ],
        'user_strategies': [
            'id', 'user_id', 'strategy_id', 'name', 'description', 'color', 'is_active',
            'risk_level', 'expected_return_min', 'expected_return_max',
            'volatility', 'daily_drift', 'trade_frequency_seconds',
            'target_investment_ratio', 'max_position_pct',
            'stop_loss_percent', 'take_profit_percent', 'auto_rebalance',
            'based_on_template', 'created_at', 'updated_at'
        ],
        'user_strategy_stocks': [
            'id', 'user_strategy_id', 'strategy_id', 'symbol', 'weight', 'created_at'
        ],
    }

    def __init__(self, data_dir='data'):
        """
        Initialize CSV storage.

        Args:
            data_dir: Directory path for CSV files (relative to app root or absolute)
        """
        # Resolve data directory path
        if os.path.isabs(data_dir):
            self.data_dir = Path(data_dir)
        else:
            # Relative to the investment_platform directory
            base_dir = Path(__file__).parent.parent.parent
            self.data_dir = base_dir / data_dir

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize CSV files with headers if they don't exist
        self._init_files()

        # Locks for thread-safe file access
        self._locks = {name: Lock() for name in self.FILES}

        # Auto-increment counters
        self._id_counters = {}
        self._load_id_counters()

    def _init_files(self):
        """Create CSV files with headers if they don't exist."""
        for name, filename in self.FILES.items():
            filepath = self.data_dir / filename
            if not filepath.exists():
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.COLUMNS[name])

    def _load_id_counters(self):
        """Load current max IDs from existing data."""
        for name in self.FILES:
            self._id_counters[name] = self._get_max_id(name)

    def _get_max_id(self, table_name):
        """Get the maximum ID from a table."""
        rows = self._read_all(table_name)
        if not rows:
            return 0
        return max(int(row.get('id', 0)) for row in rows)

    def _next_id(self, table_name):
        """Get the next auto-increment ID."""
        self._id_counters[table_name] += 1
        return self._id_counters[table_name]

    def _get_filepath(self, table_name):
        """Get the full file path for a table."""
        return self.data_dir / self.FILES[table_name]

    def _read_all(self, table_name):
        """Read all rows from a CSV file."""
        filepath = self._get_filepath(table_name)
        if not filepath.exists():
            return []

        with self._locks[table_name]:
            with open(filepath, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)

    def _write_all(self, table_name, rows):
        """Write all rows to a CSV file (replaces existing content)."""
        filepath = self._get_filepath(table_name)
        columns = self.COLUMNS[table_name]

        with self._locks[table_name]:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, '') for k in columns})

    def _serialize_value(self, value):
        """Convert Python value to CSV string."""
        if value is None:
            return ''
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, bool):
            return '1' if value else '0'
        return str(value)

    def _deserialize_value(self, value, field_name, table_name):
        """Convert CSV string to appropriate Python type."""
        if value == '' or value is None:
            return None

        # Determine type based on field name patterns
        if field_name == 'id' or field_name.endswith('_id'):
            if field_name in ('trade_id', 'user_id', 'strategy_id'):
                return value  # These are strings
            try:
                return int(value)
            except ValueError:
                return value

        if field_name in ('quantity', 'price', 'total', 'fees', 'avg_cost',
                          'initial_value', 'current_cash', 'realized_gains',
                          'open', 'high', 'low', 'close', 'adj_close'):
            try:
                return Decimal(value)
            except:
                return value

        if field_name == 'volume' or field_name == 'total_records':
            try:
                return int(value)
            except ValueError:
                return None

        if field_name in ('is_initialized', 'auto_rebalance', 'reinvest_dividends', 'is_active'):
            return int(value) if value else 0

        if field_name in ('confidence_level', 'max_position_size',
                          'stop_loss_percent', 'take_profit_percent',
                          'risk_level', 'expected_return_min', 'expected_return_max',
                          'trade_frequency_seconds', 'user_strategy_id'):
            try:
                return int(value)
            except ValueError:
                return value

        if field_name in ('volatility', 'daily_drift', 'target_investment_ratio',
                          'max_position_pct', 'weight'):
            try:
                return float(value)
            except ValueError:
                return value

        if field_name in ('created_at', 'updated_at', 'timestamp',
                          'fetched_at', 'last_updated'):
            try:
                return datetime.fromisoformat(value)
            except:
                return value

        if field_name in ('date', 'last_fetch_date', 'earliest_date', 'latest_date'):
            try:
                return date.fromisoformat(value)
            except:
                return value

        return value

    def _deserialize_row(self, row, table_name):
        """Convert a CSV row dict to properly typed dict."""
        return {
            k: self._deserialize_value(v, k, table_name)
            for k, v in row.items()
        }

    # =====================
    # Portfolio State CRUD
    # =====================

    def get_portfolio(self, user_id='default'):
        """Get portfolio state for a user."""
        rows = self._read_all('portfolio_state')
        for row in rows:
            if row.get('user_id') == user_id:
                return self._deserialize_row(row, 'portfolio_state')
        return None

    def create_portfolio(self, user_id='default', **kwargs):
        """Create a new portfolio state."""
        now = datetime.now(timezone.utc)
        row = {
            'id': self._next_id('portfolio_state'),
            'user_id': user_id,
            'initial_value': kwargs.get('initial_value', Decimal('100000.00')),
            'current_cash': kwargs.get('current_cash', Decimal('100000.00')),
            'current_strategy': kwargs.get('current_strategy', 'balanced'),
            'is_initialized': kwargs.get('is_initialized', 0),
            'realized_gains': kwargs.get('realized_gains', Decimal('0.00')),
            'created_at': now,
            'updated_at': now,
        }

        rows = self._read_all('portfolio_state')
        serialized = {k: self._serialize_value(v) for k, v in row.items()}
        rows.append(serialized)
        self._write_all('portfolio_state', rows)
        return row

    def update_portfolio(self, user_id='default', **kwargs):
        """Update portfolio state for a user."""
        rows = self._read_all('portfolio_state')
        updated = False

        for i, row in enumerate(rows):
            if row.get('user_id') == user_id:
                for key, value in kwargs.items():
                    if key in self.COLUMNS['portfolio_state']:
                        rows[i][key] = self._serialize_value(value)
                rows[i]['updated_at'] = self._serialize_value(datetime.now(timezone.utc))
                updated = True
                break

        if updated:
            self._write_all('portfolio_state', rows)
        return updated

    def get_or_create_portfolio(self, user_id='default'):
        """Get existing portfolio or create a new one."""
        portfolio = self.get_portfolio(user_id)
        if portfolio is None:
            portfolio = self.create_portfolio(user_id)
        return portfolio

    # =====================
    # Holdings CRUD
    # =====================

    def get_holdings(self, user_id='default'):
        """Get all holdings for a user."""
        rows = self._read_all('holdings')
        return [
            self._deserialize_row(row, 'holdings')
            for row in rows
            if row.get('user_id') == user_id
        ]

    def get_holding(self, user_id, symbol):
        """Get a specific holding."""
        rows = self._read_all('holdings')
        for row in rows:
            if row.get('user_id') == user_id and row.get('symbol') == symbol:
                return self._deserialize_row(row, 'holdings')
        return None

    def create_holding(self, user_id, symbol, **kwargs):
        """Create a new holding."""
        now = datetime.now(timezone.utc)
        row = {
            'id': self._next_id('holdings'),
            'user_id': user_id,
            'symbol': symbol,
            'name': kwargs.get('name', ''),
            'sector': kwargs.get('sector', ''),
            'quantity': kwargs.get('quantity', Decimal('0')),
            'avg_cost': kwargs.get('avg_cost', Decimal('0')),
            'created_at': now,
            'updated_at': now,
        }

        rows = self._read_all('holdings')
        serialized = {k: self._serialize_value(v) for k, v in row.items()}
        rows.append(serialized)
        self._write_all('holdings', rows)
        return row

    def update_holding(self, user_id, symbol, **kwargs):
        """Update a holding."""
        rows = self._read_all('holdings')
        updated = False

        for i, row in enumerate(rows):
            if row.get('user_id') == user_id and row.get('symbol') == symbol:
                for key, value in kwargs.items():
                    if key in self.COLUMNS['holdings']:
                        rows[i][key] = self._serialize_value(value)
                rows[i]['updated_at'] = self._serialize_value(datetime.now(timezone.utc))
                updated = True
                break

        if updated:
            self._write_all('holdings', rows)
        return updated

    def delete_holding(self, user_id, symbol):
        """Delete a holding."""
        rows = self._read_all('holdings')
        original_len = len(rows)
        rows = [r for r in rows if not (r.get('user_id') == user_id and r.get('symbol') == symbol)]

        if len(rows) < original_len:
            self._write_all('holdings', rows)
            return True
        return False

    def delete_user_holdings(self, user_id='default'):
        """Delete all holdings for a user."""
        rows = self._read_all('holdings')
        rows = [r for r in rows if r.get('user_id') != user_id]
        self._write_all('holdings', rows)

    # =====================
    # Trades History CRUD
    # =====================

    def get_trades(self, user_id='default', limit=100, trade_type=None):
        """Get trades for a user."""
        rows = self._read_all('trades_history')
        trades = [
            self._deserialize_row(row, 'trades_history')
            for row in rows
            if row.get('user_id') == user_id and (trade_type is None or row.get('type') == trade_type)
        ]
        # Sort by timestamp descending
        trades.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
        return trades[:limit]

    def create_trade(self, **kwargs):
        """Create a new trade record."""
        now = datetime.now(timezone.utc)
        row = {
            'id': self._next_id('trades_history'),
            'user_id': kwargs.get('user_id', 'default'),
            'trade_id': kwargs.get('trade_id'),
            'timestamp': kwargs.get('timestamp', now),
            'type': kwargs.get('type'),
            'symbol': kwargs.get('symbol'),
            'stock_name': kwargs.get('stock_name', ''),
            'sector': kwargs.get('sector', ''),
            'quantity': kwargs.get('quantity'),
            'price': kwargs.get('price'),
            'total': kwargs.get('total'),
            'fees': kwargs.get('fees', Decimal('0.00')),
            'strategy': kwargs.get('strategy', ''),
            'created_at': now,
        }

        rows = self._read_all('trades_history')
        serialized = {k: self._serialize_value(v) for k, v in row.items()}
        rows.append(serialized)
        self._write_all('trades_history', rows)
        return row

    def delete_user_trades(self, user_id='default'):
        """Delete all trades for a user."""
        rows = self._read_all('trades_history')
        rows = [r for r in rows if r.get('user_id') != user_id]
        self._write_all('trades_history', rows)

    def get_trade_count(self, user_id='default'):
        """Get total number of trades for a user."""
        rows = self._read_all('trades_history')
        return sum(1 for r in rows if r.get('user_id') == user_id)

    # =====================
    # Strategy Customizations CRUD
    # =====================

    def get_strategy_customizations(self, user_id='default'):
        """Get all strategy customizations for a user."""
        rows = self._read_all('strategy_customizations')
        return [
            self._deserialize_row(row, 'strategy_customizations')
            for row in rows
            if row.get('user_id') == user_id
        ]

    def get_strategy_customization(self, user_id, strategy_id):
        """Get a specific strategy customization."""
        rows = self._read_all('strategy_customizations')
        for row in rows:
            if row.get('user_id') == user_id and row.get('strategy_id') == strategy_id:
                return self._deserialize_row(row, 'strategy_customizations')
        return None

    def upsert_strategy_customization(self, user_id, strategy_id, **kwargs):
        """Create or update a strategy customization."""
        existing = self.get_strategy_customization(user_id, strategy_id)

        if existing:
            # Update
            rows = self._read_all('strategy_customizations')
            for i, row in enumerate(rows):
                if row.get('user_id') == user_id and row.get('strategy_id') == strategy_id:
                    for key, value in kwargs.items():
                        if key in self.COLUMNS['strategy_customizations']:
                            rows[i][key] = self._serialize_value(value)
                    rows[i]['updated_at'] = self._serialize_value(datetime.now(timezone.utc))
                    break
            self._write_all('strategy_customizations', rows)
        else:
            # Create
            now = datetime.now(timezone.utc)
            row = {
                'id': self._next_id('strategy_customizations'),
                'user_id': user_id,
                'strategy_id': strategy_id,
                'confidence_level': kwargs.get('confidence_level', 50),
                'trade_frequency': kwargs.get('trade_frequency', 'medium'),
                'max_position_size': kwargs.get('max_position_size', 15),
                'stop_loss_percent': kwargs.get('stop_loss_percent', 10),
                'take_profit_percent': kwargs.get('take_profit_percent', 20),
                'auto_rebalance': kwargs.get('auto_rebalance', 1),
                'reinvest_dividends': kwargs.get('reinvest_dividends', 1),
                'created_at': now,
                'updated_at': now,
            }

            rows = self._read_all('strategy_customizations')
            serialized = {k: self._serialize_value(v) for k, v in row.items()}
            rows.append(serialized)
            self._write_all('strategy_customizations', rows)

    # =====================
    # Market Data Cache CRUD
    # =====================

    def get_market_data(self, symbol, start_date=None, end_date=None):
        """Get cached market data for a symbol."""
        rows = self._read_all('market_data_cache')
        data = [
            self._deserialize_row(row, 'market_data_cache')
            for row in rows
            if row.get('symbol') == symbol
        ]

        # Filter by date range if provided
        if start_date:
            data = [d for d in data if d.get('date') and d['date'] >= start_date]
        if end_date:
            data = [d for d in data if d.get('date') and d['date'] <= end_date]

        # Sort by date
        data.sort(key=lambda x: x.get('date') or date.min)
        return data

    def get_latest_market_data(self, symbol):
        """Get the most recent market data for a symbol."""
        data = self.get_market_data(symbol)
        return data[-1] if data else None

    def bulk_insert_market_data(self, records):
        """Insert multiple market data records."""
        rows = self._read_all('market_data_cache')
        existing = {(r.get('symbol'), r.get('date')) for r in rows}

        for record in records:
            key = (record['symbol'], self._serialize_value(record['date']))
            if key in existing:
                # Update existing
                for i, row in enumerate(rows):
                    if row.get('symbol') == record['symbol'] and row.get('date') == self._serialize_value(record['date']):
                        for k, v in record.items():
                            rows[i][k] = self._serialize_value(v)
                        rows[i]['fetched_at'] = self._serialize_value(datetime.now(timezone.utc))
                        break
            else:
                # Insert new
                new_row = {
                    'id': self._next_id('market_data_cache'),
                    'symbol': record['symbol'],
                    'date': self._serialize_value(record['date']),
                    'open': self._serialize_value(record.get('open')),
                    'high': self._serialize_value(record.get('high')),
                    'low': self._serialize_value(record.get('low')),
                    'close': self._serialize_value(record['close']),
                    'adj_close': self._serialize_value(record['adj_close']),
                    'volume': self._serialize_value(record.get('volume')),
                    'fetched_at': self._serialize_value(datetime.now(timezone.utc)),
                }
                rows.append(new_row)
                existing.add(key)

        self._write_all('market_data_cache', rows)

    def delete_market_data(self, symbol=None):
        """Delete market data for a symbol or all data."""
        rows = self._read_all('market_data_cache')
        if symbol:
            rows = [r for r in rows if r.get('symbol') != symbol]
        else:
            rows = []
        self._write_all('market_data_cache', rows)

    # =====================
    # Market Data Metadata CRUD
    # =====================

    def get_market_metadata(self, symbol):
        """Get metadata for a symbol."""
        rows = self._read_all('market_data_metadata')
        for row in rows:
            if row.get('symbol') == symbol:
                return self._deserialize_row(row, 'market_data_metadata')
        return None

    def get_or_create_market_metadata(self, symbol):
        """Get or create metadata for a symbol."""
        metadata = self.get_market_metadata(symbol)
        if metadata is None:
            now = datetime.now(timezone.utc)
            row = {
                'id': self._next_id('market_data_metadata'),
                'symbol': symbol,
                'last_fetch_date': '',
                'earliest_date': '',
                'latest_date': '',
                'total_records': 0,
                'last_updated': self._serialize_value(now),
                'fetch_status': 'pending',
            }

            rows = self._read_all('market_data_metadata')
            rows.append(row)
            self._write_all('market_data_metadata', rows)
            metadata = self._deserialize_row(row, 'market_data_metadata')
        return metadata

    def update_market_metadata(self, symbol, **kwargs):
        """Update metadata for a symbol."""
        rows = self._read_all('market_data_metadata')
        updated = False

        for i, row in enumerate(rows):
            if row.get('symbol') == symbol:
                for key, value in kwargs.items():
                    if key in self.COLUMNS['market_data_metadata']:
                        rows[i][key] = self._serialize_value(value)
                rows[i]['last_updated'] = self._serialize_value(datetime.now(timezone.utc))
                updated = True
                break

        if updated:
            self._write_all('market_data_metadata', rows)
        return updated

    def get_all_symbols(self):
        """Get list of all symbols with metadata."""
        rows = self._read_all('market_data_metadata')
        return [row.get('symbol') for row in rows if row.get('symbol')]

    def get_stale_symbols(self, before_date=None):
        """Get symbols that need refreshing."""
        if before_date is None:
            before_date = date.today()

        rows = self._read_all('market_data_metadata')
        stale = []
        for row in rows:
            latest = row.get('latest_date')
            if not latest or date.fromisoformat(latest) < before_date:
                stale.append(row.get('symbol'))
        return stale

    # =====================
    # User Strategies CRUD
    # =====================

    def get_user_strategies(self, user_id='default', include_inactive=False):
        """Get all user strategies for a user."""
        rows = self._read_all('user_strategies')
        strategies = []
        for row in rows:
            if row.get('user_id') == user_id:
                if include_inactive or row.get('is_active', '1') == '1':
                    strategies.append(self._deserialize_row(row, 'user_strategies'))
        return strategies

    def get_user_strategy(self, strategy_id, user_id='default'):
        """Get a specific user strategy."""
        rows = self._read_all('user_strategies')
        for row in rows:
            if row.get('strategy_id') == strategy_id and row.get('user_id') == user_id:
                return self._deserialize_row(row, 'user_strategies')
        return None

    def create_user_strategy(self, user_id, strategy_id, **kwargs):
        """Create a new user strategy."""
        now = datetime.now(timezone.utc)
        row = {
            'id': self._next_id('user_strategies'),
            'user_id': user_id,
            'strategy_id': strategy_id,
            'name': kwargs.get('name', strategy_id.title()),
            'description': kwargs.get('description', ''),
            'color': kwargs.get('color', '#3b82f6'),
            'is_active': kwargs.get('is_active', 1),
            'risk_level': kwargs.get('risk_level', 3),
            'expected_return_min': kwargs.get('expected_return_min', 5),
            'expected_return_max': kwargs.get('expected_return_max', 15),
            'volatility': kwargs.get('volatility', 0.01),
            'daily_drift': kwargs.get('daily_drift', 0.00035),
            'trade_frequency_seconds': kwargs.get('trade_frequency_seconds', 75),
            'target_investment_ratio': kwargs.get('target_investment_ratio', 0.7),
            'max_position_pct': kwargs.get('max_position_pct', 0.15),
            'stop_loss_percent': kwargs.get('stop_loss_percent', 10),
            'take_profit_percent': kwargs.get('take_profit_percent', 20),
            'auto_rebalance': kwargs.get('auto_rebalance', 1),
            'based_on_template': kwargs.get('based_on_template', ''),
            'created_at': now,
            'updated_at': now,
        }

        rows = self._read_all('user_strategies')
        serialized = {k: self._serialize_value(v) for k, v in row.items()}
        rows.append(serialized)
        self._write_all('user_strategies', rows)
        return self._deserialize_row(row, 'user_strategies')

    def update_user_strategy(self, strategy_id, user_id='default', **kwargs):
        """Update an existing user strategy."""
        rows = self._read_all('user_strategies')
        updated = False
        updated_row = None

        for i, row in enumerate(rows):
            if row.get('strategy_id') == strategy_id and row.get('user_id') == user_id:
                for key, value in kwargs.items():
                    if key in self.COLUMNS['user_strategies']:
                        rows[i][key] = self._serialize_value(value)
                rows[i]['updated_at'] = self._serialize_value(datetime.now(timezone.utc))
                updated = True
                updated_row = rows[i]
                break

        if updated:
            self._write_all('user_strategies', rows)
            return self._deserialize_row(updated_row, 'user_strategies')
        return None

    def delete_user_strategy(self, strategy_id, user_id='default', hard_delete=False):
        """Delete (archive) a user strategy."""
        if hard_delete:
            rows = self._read_all('user_strategies')
            original_len = len(rows)
            rows = [r for r in rows if not (r.get('strategy_id') == strategy_id and r.get('user_id') == user_id)]
            if len(rows) < original_len:
                self._write_all('user_strategies', rows)
                # Also delete associated stocks
                self.delete_all_strategy_stocks(strategy_id)
                return True
            return False
        else:
            return self.update_user_strategy(strategy_id, user_id, is_active=0) is not None

    # =====================
    # User Strategy Stocks CRUD
    # =====================

    def get_strategy_stocks(self, strategy_id):
        """Get all stocks for a strategy."""
        rows = self._read_all('user_strategy_stocks')
        return [
            self._deserialize_row(row, 'user_strategy_stocks')
            for row in rows
            if row.get('strategy_id') == strategy_id
        ]

    def set_strategy_stocks(self, strategy_id, symbols, user_strategy_id=None):
        """Replace all stocks for a strategy with new list."""
        # Delete existing stocks for this strategy
        rows = self._read_all('user_strategy_stocks')
        rows = [r for r in rows if r.get('strategy_id') != strategy_id]

        now = datetime.now(timezone.utc)
        for symbol in symbols:
            row = {
                'id': self._next_id('user_strategy_stocks'),
                'user_strategy_id': user_strategy_id or '',
                'strategy_id': strategy_id,
                'symbol': symbol.upper(),
                'weight': 1.0,
                'created_at': now,
            }
            serialized = {k: self._serialize_value(v) for k, v in row.items()}
            rows.append(serialized)

        self._write_all('user_strategy_stocks', rows)
        return True

    def add_strategy_stock(self, strategy_id, symbol, weight=1.0, user_strategy_id=None):
        """Add a single stock to a strategy."""
        rows = self._read_all('user_strategy_stocks')

        # Check if already exists
        for row in rows:
            if row.get('strategy_id') == strategy_id and row.get('symbol') == symbol.upper():
                # Update weight
                row['weight'] = self._serialize_value(weight)
                self._write_all('user_strategy_stocks', rows)
                return self._deserialize_row(row, 'user_strategy_stocks')

        # Add new stock
        now = datetime.now(timezone.utc)
        new_row = {
            'id': self._next_id('user_strategy_stocks'),
            'user_strategy_id': user_strategy_id or '',
            'strategy_id': strategy_id,
            'symbol': symbol.upper(),
            'weight': weight,
            'created_at': now,
        }
        serialized = {k: self._serialize_value(v) for k, v in new_row.items()}
        rows.append(serialized)
        self._write_all('user_strategy_stocks', rows)
        return self._deserialize_row(new_row, 'user_strategy_stocks')

    def remove_strategy_stock(self, strategy_id, symbol):
        """Remove a stock from a strategy."""
        rows = self._read_all('user_strategy_stocks')
        original_len = len(rows)
        rows = [r for r in rows if not (r.get('strategy_id') == strategy_id and r.get('symbol') == symbol.upper())]

        if len(rows) < original_len:
            self._write_all('user_strategy_stocks', rows)
            return True
        return False

    def delete_all_strategy_stocks(self, strategy_id):
        """Delete all stocks for a strategy."""
        rows = self._read_all('user_strategy_stocks')
        rows = [r for r in rows if r.get('strategy_id') != strategy_id]
        self._write_all('user_strategy_stocks', rows)
        return True


# Global CSV storage instance
_csv_storage = None


def get_csv_storage(data_dir='data'):
    """Get or create the global CSV storage instance."""
    global _csv_storage
    if _csv_storage is None:
        _csv_storage = CSVStorage(data_dir)
    return _csv_storage
