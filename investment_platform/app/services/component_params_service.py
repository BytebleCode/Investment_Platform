"""
Component Parameters Service

Manages component-level trading parameter overrides with inheritance.
Parameters cascade from strategy defaults → sector → subsector → symbol.
"""
import logging
from typing import Dict, Optional, Any

from app.models.strategy_component_params import StrategyComponentParams
from app.data.symbol_universe import get_sector_for_symbol

logger = logging.getLogger(__name__)


# Default trading parameters (from UserStrategy defaults)
DEFAULT_PARAMS = {
    'max_position_pct': 0.15,
    'stop_loss_percent': 10,
    'take_profit_percent': 20,
    'trade_frequency_multiplier': 1.0,
    'entry_signal': 'sma_crossover',
    'exit_signal': 'sma_crossover'
}


class ComponentParamsService:
    """
    Service for managing component-level trading parameter overrides.

    Inheritance model:
    Symbol params → Subsector params → Sector params → Strategy defaults

    Any null value falls through to the parent level.
    """

    def __init__(self, strategy_id: str, strategy_defaults: Optional[dict] = None):
        """
        Initialize component params service for a strategy.

        Args:
            strategy_id: Strategy identifier
            strategy_defaults: Strategy-level default parameters
        """
        self.strategy_id = strategy_id
        self.strategy_defaults = strategy_defaults or {}

    def get_params(self, component_path: str) -> Optional[dict]:
        """
        Get raw params for a specific component (no inheritance).

        Args:
            component_path: Component path (sector, subsector, or symbol)

        Returns:
            Params dict or None if not set
        """
        params = StrategyComponentParams.get_params(self.strategy_id, component_path)
        if params:
            return params.to_dict() if hasattr(params, 'to_dict') else params
        return None

    def get_all_params(self) -> list:
        """
        Get all component params for this strategy.

        Returns:
            List of param dictionaries
        """
        params = StrategyComponentParams.get_all_params(self.strategy_id)
        return [p.to_dict() if hasattr(p, 'to_dict') else p for p in params]

    def set_params(self, component_path: str, **params) -> dict:
        """
        Set params for a component.

        Args:
            component_path: Component path
            **params: Parameter values to set

        Returns:
            Updated params dict
        """
        # Filter to valid params
        valid_params = {}
        for key in ['max_position_pct', 'stop_loss_percent', 'take_profit_percent',
                    'trade_frequency_multiplier', 'entry_signal', 'exit_signal']:
            if key in params:
                valid_params[key] = params[key]

        result = StrategyComponentParams.set_params(
            self.strategy_id,
            component_path,
            **valid_params
        )
        return result.to_dict() if hasattr(result, 'to_dict') else result

    def delete_params(self, component_path: str) -> bool:
        """
        Delete params for a component.

        Args:
            component_path: Component path

        Returns:
            True if deleted
        """
        return StrategyComponentParams.delete_params(self.strategy_id, component_path)

    def get_effective_params(self, symbol: str) -> dict:
        """
        Get effective parameters for a symbol with full inheritance chain.

        Looks up params in order:
        1. Symbol-level override
        2. Subsector-level override
        3. Sector-level override
        4. Strategy defaults
        5. System defaults

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of effective parameters
        """
        # Start with system defaults
        effective = DEFAULT_PARAMS.copy()

        # Apply strategy defaults
        for key in effective:
            if key in self.strategy_defaults and self.strategy_defaults[key] is not None:
                effective[key] = self.strategy_defaults[key]

        # Get sector and subsector for symbol
        sector, subsector = get_sector_for_symbol(symbol)

        # Build inheritance chain
        paths_to_check = []
        if sector:
            paths_to_check.append(sector)
            if subsector:
                paths_to_check.append(f"{sector}.{subsector}")
        paths_to_check.append(symbol.upper())

        # Apply overrides from most general to most specific
        for path in paths_to_check:
            params = self.get_params(path)
            if params:
                for key in effective:
                    if key in params and params[key] is not None:
                        effective[key] = params[key]

        return effective

    def get_params_with_inheritance(self, component_path: str) -> dict:
        """
        Get params for a component showing inherited values.

        Args:
            component_path: Component path

        Returns:
            Dict with 'effective', 'overridden', and 'inherited' keys
        """
        # Determine component type
        if '.' in component_path:
            # Subsector
            sector = component_path.split('.')[0]
            parent_paths = [sector]
        elif component_path.upper() == component_path:
            # Symbol
            sector, subsector = get_sector_for_symbol(component_path)
            parent_paths = []
            if sector:
                parent_paths.append(sector)
                if subsector:
                    parent_paths.append(f"{sector}.{subsector}")
        else:
            # Sector
            parent_paths = []

        # Get component's own params
        own_params = self.get_params(component_path) or {}

        # Calculate effective and track inheritance
        effective = DEFAULT_PARAMS.copy()
        inherited_from = {}

        # Apply strategy defaults
        for key in effective:
            if key in self.strategy_defaults and self.strategy_defaults[key] is not None:
                effective[key] = self.strategy_defaults[key]
                inherited_from[key] = 'strategy'
            else:
                inherited_from[key] = 'default'

        # Apply parent overrides
        for path in parent_paths:
            params = self.get_params(path)
            if params:
                for key in effective:
                    if key in params and params[key] is not None:
                        effective[key] = params[key]
                        inherited_from[key] = path

        # Apply own overrides
        overridden = {}
        for key in effective:
            if key in own_params and own_params[key] is not None:
                effective[key] = own_params[key]
                overridden[key] = own_params[key]
                inherited_from[key] = 'self'

        return {
            'effective': effective,
            'overridden': overridden,
            'inherited_from': inherited_from,
            'own_params': own_params
        }

    def get_inheritance_chain(self, symbol: str) -> list:
        """
        Get the full inheritance chain for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            List of dicts showing each level's params
        """
        chain = []

        # System defaults
        chain.append({
            'level': 'default',
            'path': None,
            'params': DEFAULT_PARAMS.copy()
        })

        # Strategy defaults
        strategy_params = {}
        for key in DEFAULT_PARAMS:
            if key in self.strategy_defaults and self.strategy_defaults[key] is not None:
                strategy_params[key] = self.strategy_defaults[key]
        if strategy_params:
            chain.append({
                'level': 'strategy',
                'path': self.strategy_id,
                'params': strategy_params
            })

        # Sector
        sector, subsector = get_sector_for_symbol(symbol)
        if sector:
            sector_params = self.get_params(sector)
            if sector_params:
                chain.append({
                    'level': 'sector',
                    'path': sector,
                    'params': {k: v for k, v in sector_params.items()
                              if k in DEFAULT_PARAMS and v is not None}
                })

            # Subsector
            if subsector:
                subsector_path = f"{sector}.{subsector}"
                subsector_params = self.get_params(subsector_path)
                if subsector_params:
                    chain.append({
                        'level': 'subsector',
                        'path': subsector_path,
                        'params': {k: v for k, v in subsector_params.items()
                                  if k in DEFAULT_PARAMS and v is not None}
                    })

        # Symbol
        symbol_params = self.get_params(symbol.upper())
        if symbol_params:
            chain.append({
                'level': 'symbol',
                'path': symbol.upper(),
                'params': {k: v for k, v in symbol_params.items()
                          if k in DEFAULT_PARAMS and v is not None}
            })

        return chain

    def bulk_set_params(self, params_list: list) -> list:
        """
        Set params for multiple components at once.

        Args:
            params_list: List of dicts with 'component_path' and param values

        Returns:
            List of created/updated params
        """
        results = []
        for item in params_list:
            component_path = item.get('component_path')
            if component_path:
                params = {k: v for k, v in item.items() if k != 'component_path'}
                result = self.set_params(component_path, **params)
                results.append(result)
        return results

    def clear_all_params(self) -> bool:
        """
        Clear all component params for this strategy.

        Returns:
            True if successful
        """
        return StrategyComponentParams.delete_all_for_strategy(self.strategy_id)
