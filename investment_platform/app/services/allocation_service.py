"""
Allocation Service

Manages hierarchical allocations for strategies at sector, subsector, or symbol level.
Handles weight computation and effective symbol resolution.
"""
import logging
from typing import List, Dict, Optional, Tuple

from app.models.strategy_allocation import StrategyAllocation
from app.data.symbol_universe import (
    SYMBOL_UNIVERSE,
    SECTOR_METADATA,
    get_sector_symbols,
    get_subsectors,
    get_all_sectors,
    get_symbols_by_path
)

logger = logging.getLogger(__name__)


class AllocationService:
    """
    Service for managing strategy allocations with hierarchical weight computation.

    Allocations can be at three levels:
    - Sector: e.g., 'financials' (all subsectors and symbols)
    - Subsector: e.g., 'financials.banks' (all symbols in subsector)
    - Symbol: e.g., 'JPM' (individual stock)

    Weights are computed hierarchically:
    - Sector weight * Subsector weight * Symbol weight = Effective weight
    """

    def __init__(self, strategy_id: str):
        """
        Initialize allocation service for a strategy.

        Args:
            strategy_id: Strategy identifier
        """
        self.strategy_id = strategy_id

    def get_allocations(self, include_inactive: bool = False) -> List[dict]:
        """
        Get all allocations for this strategy.

        Args:
            include_inactive: Include deactivated allocations

        Returns:
            List of allocation dictionaries
        """
        allocations = StrategyAllocation.get_allocations(
            self.strategy_id,
            include_inactive
        )
        return [a.to_dict() if hasattr(a, 'to_dict') else a for a in allocations]

    def add_allocation(self, path: str, weight: float = 1.0,
                       allocation_type: Optional[str] = None) -> dict:
        """
        Add an allocation to the strategy.

        Args:
            path: Allocation path (sector, sector.subsector, or symbol)
            weight: Weight for this allocation (0.0 to 1.0)
            allocation_type: Type (auto-detected if not provided)

        Returns:
            Created allocation dictionary
        """
        # Auto-detect allocation type
        if allocation_type is None:
            allocation_type = self._detect_allocation_type(path)

        # Determine parent path
        parent_path = self._get_parent_path(path, allocation_type)

        # Check if allocation already exists
        existing = StrategyAllocation.get_by_path(self.strategy_id, path)
        if existing:
            # Update existing allocation
            allocation = StrategyAllocation.update(existing.id, weight=weight)
        else:
            # Create new allocation
            allocation = StrategyAllocation.create(
                strategy_id=self.strategy_id,
                allocation_type=allocation_type,
                path=path,
                weight=weight,
                parent_path=parent_path
            )

        return allocation.to_dict() if hasattr(allocation, 'to_dict') else allocation

    def update_allocation(self, allocation_id: int, weight: float) -> Optional[dict]:
        """
        Update an allocation's weight.

        Args:
            allocation_id: Allocation ID
            weight: New weight value

        Returns:
            Updated allocation or None if not found
        """
        allocation = StrategyAllocation.update(allocation_id, weight=weight)
        if allocation:
            return allocation.to_dict() if hasattr(allocation, 'to_dict') else allocation
        return None

    def remove_allocation(self, allocation_id: int, hard_delete: bool = False) -> bool:
        """
        Remove an allocation.

        Args:
            allocation_id: Allocation ID
            hard_delete: If True, permanently delete

        Returns:
            True if removed successfully
        """
        return StrategyAllocation.delete(allocation_id, hard_delete)

    def set_allocations(self, allocations: List[dict]) -> List[dict]:
        """
        Replace all allocations for this strategy.

        Args:
            allocations: List of allocation dicts with 'path' and 'weight'

        Returns:
            List of created allocations
        """
        # Delete existing allocations
        StrategyAllocation.delete_all_for_strategy(self.strategy_id, hard_delete=True)

        # Create new allocations
        created = []
        for alloc in allocations:
            path = alloc.get('path')
            weight = float(alloc.get('weight', 1.0))
            allocation_type = alloc.get('allocation_type')

            if path:
                result = self.add_allocation(path, weight, allocation_type)
                created.append(result)

        return created

    def compute_effective_symbols(self) -> Dict[str, float]:
        """
        Resolve all allocations to a final weighted symbol list.

        Returns:
            Dictionary of symbol -> effective weight
        """
        allocations = self.get_allocations()
        if not allocations:
            return {}

        # Build allocation tree
        sectors = {}  # sector -> {'weight': w, 'subsectors': {...}, 'symbols': {...}}
        standalone_symbols = {}  # Direct symbol allocations

        for alloc in allocations:
            path = alloc['path']
            weight = alloc['weight']
            alloc_type = alloc['allocation_type']

            if alloc_type == 'sector':
                if path not in sectors:
                    sectors[path] = {'weight': weight, 'subsectors': {}, 'symbols': {}}
                else:
                    sectors[path]['weight'] = weight

            elif alloc_type == 'subsector':
                parts = path.split('.')
                if len(parts) == 2:
                    sector, subsector = parts
                    if sector not in sectors:
                        sectors[sector] = {'weight': 1.0, 'subsectors': {}, 'symbols': {}}
                    sectors[sector]['subsectors'][subsector] = weight

            elif alloc_type == 'symbol':
                # Check if symbol has a parent in allocations
                parent_path = alloc.get('parent_path')
                if parent_path and '.' in parent_path:
                    parts = parent_path.split('.')
                    sector = parts[0]
                    if sector not in sectors:
                        sectors[sector] = {'weight': 1.0, 'subsectors': {}, 'symbols': {}}
                    if len(parts) == 2:
                        subsector = parts[1]
                        if subsector not in sectors[sector]['subsectors']:
                            sectors[sector]['subsectors'][subsector] = 1.0
                        if 'symbol_weights' not in sectors[sector]:
                            sectors[sector]['symbol_weights'] = {}
                        sectors[sector]['symbol_weights'][path] = weight
                else:
                    standalone_symbols[path] = weight

        # Calculate effective weights
        effective_weights = {}
        total_weight = 0.0

        # Process sector allocations
        for sector, sector_data in sectors.items():
            sector_weight = sector_data['weight']
            subsectors = sector_data['subsectors']
            symbol_weights = sector_data.get('symbol_weights', {})

            if subsectors:
                # Use specified subsectors
                for subsector, sub_weight in subsectors.items():
                    symbols = get_sector_symbols(sector, subsector)
                    if symbols:
                        # Check for individual symbol weights
                        for symbol in symbols:
                            if symbol in symbol_weights:
                                eff_weight = sector_weight * sub_weight * symbol_weights[symbol]
                            else:
                                eff_weight = sector_weight * sub_weight / len(symbols)
                            effective_weights[symbol] = effective_weights.get(symbol, 0) + eff_weight
                            total_weight += eff_weight
            else:
                # No subsectors specified, use all symbols in sector equally
                all_symbols = get_sector_symbols(sector)
                if all_symbols:
                    for symbol in all_symbols:
                        eff_weight = sector_weight / len(all_symbols)
                        effective_weights[symbol] = effective_weights.get(symbol, 0) + eff_weight
                        total_weight += eff_weight

        # Add standalone symbols
        for symbol, weight in standalone_symbols.items():
            effective_weights[symbol] = effective_weights.get(symbol, 0) + weight
            total_weight += weight

        # Normalize if total > 0
        if total_weight > 0:
            effective_weights = {
                symbol: weight / total_weight
                for symbol, weight in effective_weights.items()
            }

        return effective_weights

    def get_effective_symbol_list(self) -> List[str]:
        """
        Get the list of symbols from allocations (without weights).

        Returns:
            List of symbol strings
        """
        return list(self.compute_effective_symbols().keys())

    def validate_allocations(self) -> Tuple[bool, List[str]]:
        """
        Validate that allocations are properly configured.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        allocations = self.get_allocations()

        if not allocations:
            errors.append("No allocations defined")
            return False, errors

        # Check for valid paths
        for alloc in allocations:
            path = alloc['path']
            alloc_type = alloc['allocation_type']

            if alloc_type == 'sector':
                if path not in SYMBOL_UNIVERSE:
                    errors.append(f"Invalid sector: {path}")

            elif alloc_type == 'subsector':
                parts = path.split('.')
                if len(parts) != 2:
                    errors.append(f"Invalid subsector path: {path}")
                else:
                    sector, subsector = parts
                    if sector not in SYMBOL_UNIVERSE:
                        errors.append(f"Invalid sector in path: {sector}")
                    elif subsector not in SYMBOL_UNIVERSE.get(sector, {}):
                        errors.append(f"Invalid subsector: {subsector} in {sector}")

            elif alloc_type == 'symbol':
                # Symbol should exist in universe (we don't strictly enforce this)
                pass

        # Check weight ranges
        for alloc in allocations:
            weight = alloc['weight']
            if not 0.0 <= weight <= 1.0:
                errors.append(f"Weight out of range for {alloc['path']}: {weight}")

        # Compute effective symbols
        effective = self.compute_effective_symbols()
        if not effective:
            errors.append("No effective symbols resolved from allocations")

        return len(errors) == 0, errors

    def get_allocation_summary(self) -> dict:
        """
        Get a summary of allocations for display.

        Returns:
            Summary dictionary with counts and totals
        """
        allocations = self.get_allocations()
        effective_symbols = self.compute_effective_symbols()

        sector_count = sum(1 for a in allocations if a['allocation_type'] == 'sector')
        subsector_count = sum(1 for a in allocations if a['allocation_type'] == 'subsector')
        symbol_count = sum(1 for a in allocations if a['allocation_type'] == 'symbol')

        return {
            'allocation_count': len(allocations),
            'sector_allocations': sector_count,
            'subsector_allocations': subsector_count,
            'symbol_allocations': symbol_count,
            'effective_symbol_count': len(effective_symbols),
            'total_weight': sum(effective_symbols.values()) if effective_symbols else 0
        }

    def _detect_allocation_type(self, path: str) -> str:
        """Detect allocation type from path."""
        if '.' in path:
            parts = path.split('.')
            if len(parts) == 2:
                # Check if it's a valid subsector
                sector, subsector = parts
                if sector in SYMBOL_UNIVERSE and subsector in SYMBOL_UNIVERSE.get(sector, {}):
                    return 'subsector'
            # Could be a symbol with a dot (like BF.B)
            return 'symbol'
        elif path.lower() in SYMBOL_UNIVERSE:
            return 'sector'
        else:
            return 'symbol'

    def _get_parent_path(self, path: str, allocation_type: str) -> Optional[str]:
        """Get parent path for an allocation."""
        if allocation_type == 'sector':
            return None
        elif allocation_type == 'subsector':
            parts = path.split('.')
            return parts[0] if parts else None
        elif allocation_type == 'symbol':
            # Find which sector/subsector this symbol belongs to
            for sector, subsectors in SYMBOL_UNIVERSE.items():
                for subsector, symbols in subsectors.items():
                    if path.upper() in [s.upper() for s in symbols]:
                        return f"{sector}.{subsector}"
            return None
        return None


def get_industry_tree() -> List[dict]:
    """
    Get the full industry hierarchy tree for the browser.

    Returns:
        List of sector dictionaries with subsectors and symbols
    """
    tree = []

    for sector in get_all_sectors():
        metadata = SECTOR_METADATA.get(sector, {})
        sector_data = {
            'id': sector,
            'name': metadata.get('name', sector.replace('_', ' ').title()),
            'description': metadata.get('description', ''),
            'color': metadata.get('color', '#6b7280'),
            'type': 'sector',
            'subsectors': []
        }

        for subsector in get_subsectors(sector):
            symbols = get_sector_symbols(sector, subsector)
            subsector_data = {
                'id': f"{sector}.{subsector}",
                'name': subsector.replace('_', ' ').title(),
                'type': 'subsector',
                'symbols': symbols,
                'symbol_count': len(symbols)
            }
            sector_data['subsectors'].append(subsector_data)

        sector_data['total_symbols'] = sum(
            s['symbol_count'] for s in sector_data['subsectors']
        )
        tree.append(sector_data)

    return tree


def search_industries(query: str) -> List[dict]:
    """
    Search across sectors, subsectors, and symbols.

    Args:
        query: Search query string

    Returns:
        List of matching items with type and path
    """
    query = query.lower().strip()
    results = []

    for sector, subsectors in SYMBOL_UNIVERSE.items():
        sector_meta = SECTOR_METADATA.get(sector, {})
        sector_name = sector_meta.get('name', sector)

        # Check sector match
        if query in sector.lower() or query in sector_name.lower():
            results.append({
                'type': 'sector',
                'path': sector,
                'name': sector_name,
                'description': sector_meta.get('description', '')
            })

        for subsector, symbols in subsectors.items():
            subsector_name = subsector.replace('_', ' ').title()

            # Check subsector match
            if query in subsector.lower() or query in subsector_name.lower():
                results.append({
                    'type': 'subsector',
                    'path': f"{sector}.{subsector}",
                    'name': subsector_name,
                    'parent': sector_name
                })

            # Check symbol match
            for symbol in symbols:
                if query in symbol.lower():
                    results.append({
                        'type': 'symbol',
                        'path': symbol,
                        'name': symbol,
                        'parent': f"{sector_name} > {subsector_name}"
                    })

    return results[:50]  # Limit results
