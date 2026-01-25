"""
Strategy Service

Unified interface for accessing both system strategies and user-created strategies.
Provides CRUD operations for user strategies and merges results for backtest/trading.

Supports:
- System macro strategies with dynamic symbol selection
- User-created custom strategies
- FRED API macro signal integration for regime detection
"""
import re
import logging
from datetime import datetime, timezone

from app.data.strategies import STRATEGIES, STRATEGY_IDS
from app.models.user_strategy import UserStrategy
from app.models.user_strategy_stocks import UserStrategyStock
from app.services.available_symbols import validate_symbols
from app.services.symbol_selector import get_symbols_for_strategy
from app.services.macro_signals import get_regime_for_strategy, get_macro_service

logger = logging.getLogger(__name__)


class StrategyService:
    """
    Unified strategy service for system and user strategies.
    """

    # Validation constants
    MIN_STOCKS = 1
    MAX_STOCKS = 50

    def __init__(self, user_id='default'):
        """
        Initialize strategy service for a user.

        Args:
            user_id: User identifier
        """
        self.user_id = user_id

    def _format_system_strategy(self, strategy_id):
        """Format a system strategy as a unified dict."""
        strategy = STRATEGIES.get(strategy_id)
        if not strategy:
            return None

        # Use dynamic symbol selection if sector_allocation exists
        if strategy.get('sector_allocation'):
            stocks = get_symbols_for_strategy(strategy)
        else:
            stocks = strategy.get('stocks', [])

        return {
            'id': strategy['id'],
            'strategy_id': strategy['id'],
            'user_id': self.user_id,
            'name': strategy['name'],
            'description': strategy['description'],
            'color': strategy.get('color', '#3b82f6'),
            'is_active': True,
            'risk_level': strategy['risk_level'],
            'expected_return_min': strategy['expected_return'][0],
            'expected_return_max': strategy['expected_return'][1],
            'expected_return': strategy['expected_return'],
            'volatility': strategy['volatility'],
            'daily_drift': strategy['daily_drift'],
            'trade_frequency_seconds': strategy['trade_frequency_seconds'],
            'target_investment_ratio': strategy['target_investment_ratio'],
            'max_position_pct': strategy['max_position_pct'],
            'stocks': stocks,
            'is_system': True,
            'based_on_template': None,
            'created_at': None,
            'updated_at': None,
            # Macro strategy fields
            'sector_allocation': strategy.get('sector_allocation', {}),
            'signals': strategy.get('signals', {}),
            'max_symbols': strategy.get('max_symbols', 20),
            'min_symbols': strategy.get('min_symbols', 10)
        }

    def _format_user_strategy(self, strategy):
        """Format a user strategy as a unified dict."""
        if isinstance(strategy, dict):
            data = strategy.copy()
        else:
            data = strategy.to_dict()

        # Get stocks for this strategy
        stocks = UserStrategyStock.get_symbols_for_strategy(data['strategy_id'])
        data['stocks'] = stocks
        data['is_system'] = False

        # Ensure expected_return tuple exists
        if 'expected_return' not in data:
            data['expected_return'] = (
                data.get('expected_return_min', 5),
                data.get('expected_return_max', 15)
            )

        return data

    def get_strategy(self, strategy_id):
        """
        Get a strategy by ID (user strategy first, then system).

        Args:
            strategy_id: Strategy identifier

        Returns:
            dict: Strategy data or None if not found
        """
        # Check user strategies first
        user_strategy = UserStrategy.get_strategy(strategy_id, self.user_id)
        if user_strategy:
            return self._format_user_strategy(user_strategy)

        # Fall back to system strategies
        return self._format_system_strategy(strategy_id)

    def get_all_strategies(self, include_inactive=False):
        """
        Get all strategies (system + user) for the user.

        Args:
            include_inactive: Include archived user strategies

        Returns:
            list: List of strategy dicts
        """
        strategies = []

        # Add system strategies
        for strategy_id in STRATEGY_IDS:
            formatted = self._format_system_strategy(strategy_id)
            if formatted:
                strategies.append(formatted)

        # Add user strategies
        user_strategies = UserStrategy.get_user_strategies(self.user_id, include_inactive)
        for us in user_strategies:
            strategies.append(self._format_user_strategy(us))

        return strategies

    def get_system_strategies(self):
        """Get only system strategies."""
        return [self._format_system_strategy(sid) for sid in STRATEGY_IDS]

    def get_user_strategies(self, include_inactive=False):
        """Get only user strategies."""
        user_strategies = UserStrategy.get_user_strategies(self.user_id, include_inactive)
        return [self._format_user_strategy(us) for us in user_strategies]

    def create_strategy(self, data):
        """
        Create a new user strategy.

        Args:
            data: Strategy data dict with:
                - name: Display name (required)
                - description: Strategy description
                - color: Hex color
                - risk_level: 1-5
                - expected_return_min/max: Return range
                - volatility, daily_drift, etc.
                - stocks: List of symbols

        Returns:
            dict: Created strategy data

        Raises:
            ValueError: If validation fails
        """
        # Generate strategy_id from name
        name = data.get('name', '').strip()
        if not name:
            raise ValueError("Strategy name is required")

        strategy_id = self._generate_strategy_id(name)

        # Check if ID already exists
        if self.get_strategy(strategy_id):
            # Add number suffix
            counter = 1
            while self.get_strategy(f"{strategy_id}_{counter}"):
                counter += 1
            strategy_id = f"{strategy_id}_{counter}"

        # Validate and filter stocks
        stocks = data.get('stocks', [])
        if stocks:
            valid_stocks, invalid_stocks = validate_symbols(stocks)
            if invalid_stocks:
                logger.warning(f"Invalid symbols ignored: {invalid_stocks}")
            stocks = valid_stocks

        if len(stocks) < self.MIN_STOCKS:
            raise ValueError(f"At least {self.MIN_STOCKS} stock is required")
        if len(stocks) > self.MAX_STOCKS:
            raise ValueError(f"Maximum {self.MAX_STOCKS} stocks allowed")

        # Create strategy
        strategy_data = {
            'name': name,
            'description': data.get('description', ''),
            'color': data.get('color', '#3b82f6'),
            'risk_level': int(data.get('risk_level', 3)),
            'expected_return_min': int(data.get('expected_return_min', 5)),
            'expected_return_max': int(data.get('expected_return_max', 15)),
            'volatility': float(data.get('volatility', 0.01)),
            'daily_drift': float(data.get('daily_drift', 0.00035)),
            'trade_frequency_seconds': int(data.get('trade_frequency_seconds', 75)),
            'target_investment_ratio': float(data.get('target_investment_ratio', 0.7)),
            'max_position_pct': float(data.get('max_position_pct', 0.15)),
            'stop_loss_percent': int(data.get('stop_loss_percent', 10)),
            'take_profit_percent': int(data.get('take_profit_percent', 20)),
            'auto_rebalance': 1 if data.get('auto_rebalance', True) else 0,
            'based_on_template': data.get('based_on_template', ''),
        }

        strategy = UserStrategy.create(self.user_id, strategy_id, **strategy_data)

        # Get the ID for the created strategy
        if isinstance(strategy, dict):
            user_strategy_id = strategy.get('id')
        else:
            user_strategy_id = strategy.id

        # Add stocks
        UserStrategyStock.set_stocks_for_strategy(strategy_id, stocks, user_strategy_id)

        return self.get_strategy(strategy_id)

    def update_strategy(self, strategy_id, data):
        """
        Update an existing user strategy.

        Args:
            strategy_id: Strategy identifier
            data: Updated strategy data

        Returns:
            dict: Updated strategy data

        Raises:
            ValueError: If strategy is system or validation fails
        """
        # Check if it's a system strategy
        if strategy_id in STRATEGY_IDS:
            raise ValueError("Cannot modify system strategies. Clone it instead.")

        # Check if strategy exists
        existing = UserStrategy.get_strategy(strategy_id, self.user_id)
        if not existing:
            raise ValueError(f"Strategy '{strategy_id}' not found")

        # Prepare update data
        update_data = {}

        # Basic info
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'description' in data:
            update_data['description'] = data['description']
        if 'color' in data:
            update_data['color'] = data['color']

        # Parameters
        param_fields = [
            'risk_level', 'expected_return_min', 'expected_return_max',
            'volatility', 'daily_drift', 'trade_frequency_seconds',
            'target_investment_ratio', 'max_position_pct',
            'stop_loss_percent', 'take_profit_percent'
        ]
        for field in param_fields:
            if field in data:
                if field in ['volatility', 'daily_drift', 'target_investment_ratio', 'max_position_pct']:
                    update_data[field] = float(data[field])
                else:
                    update_data[field] = int(data[field])

        if 'auto_rebalance' in data:
            update_data['auto_rebalance'] = 1 if data['auto_rebalance'] else 0

        # Update strategy
        if update_data:
            UserStrategy.update(strategy_id, self.user_id, **update_data)

        # Update stocks if provided
        if 'stocks' in data:
            stocks = data['stocks']
            valid_stocks, invalid_stocks = validate_symbols(stocks)
            if invalid_stocks:
                logger.warning(f"Invalid symbols ignored: {invalid_stocks}")

            if len(valid_stocks) < self.MIN_STOCKS:
                raise ValueError(f"At least {self.MIN_STOCKS} stock is required")
            if len(valid_stocks) > self.MAX_STOCKS:
                raise ValueError(f"Maximum {self.MAX_STOCKS} stocks allowed")

            # Get strategy ID
            if isinstance(existing, dict):
                user_strategy_id = existing.get('id')
            else:
                user_strategy_id = existing.id

            UserStrategyStock.set_stocks_for_strategy(strategy_id, valid_stocks, user_strategy_id)

        return self.get_strategy(strategy_id)

    def delete_strategy(self, strategy_id, hard_delete=False):
        """
        Delete (archive) a user strategy.

        Args:
            strategy_id: Strategy identifier
            hard_delete: If True, permanently delete

        Returns:
            bool: True if deleted

        Raises:
            ValueError: If strategy is system or not found
        """
        if strategy_id in STRATEGY_IDS:
            raise ValueError("Cannot delete system strategies")

        result = UserStrategy.delete(strategy_id, self.user_id, hard_delete)
        if not result:
            raise ValueError(f"Strategy '{strategy_id}' not found")

        return True

    def clone_strategy(self, source_id, new_name):
        """
        Clone a strategy (system or user) to a new user strategy.

        Args:
            source_id: Source strategy identifier
            new_name: Name for the new strategy

        Returns:
            dict: Cloned strategy data

        Raises:
            ValueError: If source not found or validation fails
        """
        source = self.get_strategy(source_id)
        if not source:
            raise ValueError(f"Source strategy '{source_id}' not found")

        # Create clone data
        clone_data = {
            'name': new_name,
            'description': source.get('description', ''),
            'color': source.get('color', '#3b82f6'),
            'risk_level': source.get('risk_level', 3),
            'expected_return_min': source.get('expected_return_min', 5),
            'expected_return_max': source.get('expected_return_max', 15),
            'volatility': source.get('volatility', 0.01),
            'daily_drift': source.get('daily_drift', 0.00035),
            'trade_frequency_seconds': source.get('trade_frequency_seconds', 75),
            'target_investment_ratio': source.get('target_investment_ratio', 0.7),
            'max_position_pct': source.get('max_position_pct', 0.15),
            'stop_loss_percent': source.get('stop_loss_percent', 10),
            'take_profit_percent': source.get('take_profit_percent', 20),
            'auto_rebalance': source.get('auto_rebalance', True),
            'stocks': source.get('stocks', []),
            'based_on_template': source_id
        }

        return self.create_strategy(clone_data)

    def _generate_strategy_id(self, name):
        """Generate a URL-safe strategy ID from name."""
        # Convert to lowercase, replace spaces with underscores
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        slug = re.sub(r'_+', '_', slug)
        slug = slug.strip('_')

        # Limit length
        if len(slug) > 40:
            slug = slug[:40].rstrip('_')

        # Ensure it doesn't start with a number
        if slug and slug[0].isdigit():
            slug = 'strategy_' + slug

        return slug or 'custom_strategy'

    def is_system_strategy(self, strategy_id):
        """Check if a strategy is a system strategy."""
        return strategy_id in STRATEGY_IDS

    def get_strategy_stocks(self, strategy_id):
        """Get the stock list for a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            return strategy.get('stocks', [])
        return []

    def get_macro_regime(self, strategy_id):
        """
        Get the current macro regime for a strategy.

        Args:
            strategy_id: Strategy identifier

        Returns:
            dict: Regime info with score, label, and signal details
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return {'score': 0.0, 'regime': 'neutral', 'enabled': False, 'signals': {}}

        return get_regime_for_strategy(strategy)

    def get_all_regimes(self):
        """
        Get macro regime info for all system strategies.

        Returns:
            dict: Strategy ID -> regime info
        """
        regimes = {}
        for strategy_id in STRATEGY_IDS:
            strategy = STRATEGIES.get(strategy_id)
            if strategy and strategy.get('signals'):
                regimes[strategy_id] = get_regime_for_strategy(strategy)
        return regimes

    def is_macro_enabled(self):
        """Check if FRED API is configured for macro signals."""
        service = get_macro_service()
        return service.is_enabled()

    def get_strategy_with_regime(self, strategy_id):
        """
        Get a strategy with its current macro regime included.

        Args:
            strategy_id: Strategy identifier

        Returns:
            dict: Strategy data with 'macro_regime' field added
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            return None

        # Add regime info if strategy has signals
        if strategy.get('signals'):
            strategy['macro_regime'] = get_regime_for_strategy(strategy)
        else:
            strategy['macro_regime'] = {'score': 0.0, 'regime': 'neutral', 'enabled': False}

        return strategy
