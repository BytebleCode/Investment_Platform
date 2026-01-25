"""
Symbol Selector Service

Dynamically builds symbol lists for strategies based on sector allocation
constraints, filtering to only symbols available in local data.
"""
import logging
from functools import lru_cache

from app.data.symbol_universe import SYMBOL_UNIVERSE, get_symbols_by_path
from app.services.available_symbols import load_symbols

logger = logging.getLogger(__name__)


def get_available_universe_symbols():
    """
    Get all universe symbols that are available in local data.

    Returns:
        set: Intersection of universe symbols and available data
    """
    # Get all symbols from universe
    universe_symbols = set()
    for sector_data in SYMBOL_UNIVERSE.values():
        for subsec_symbols in sector_data.values():
            universe_symbols.update(subsec_symbols)

    # Get available symbols from local data
    available = load_symbols()

    # Return intersection
    return universe_symbols & available


def get_symbols_for_allocation(sector_allocation, max_symbols=25, min_symbols=10):
    """
    Build a symbol list based on sector allocation weights.

    Args:
        sector_allocation: Dict mapping sector paths to weights
            e.g., {'financials.banks': 0.30, 'utilities.electric': 0.20}
        max_symbols: Maximum number of symbols to return
        min_symbols: Minimum number of symbols required

    Returns:
        list: Selected symbols based on allocation

    Example:
        allocation = {
            'financials.banks': 0.35,
            'utilities.electric': 0.25,
            'futures.treasury': 0.15
        }
        symbols = get_symbols_for_allocation(allocation, max_symbols=20)
    """
    available = load_symbols()
    selected = []
    allocation_results = {}

    # Sort allocations by weight (highest first) for priority
    sorted_allocations = sorted(
        sector_allocation.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Calculate target counts based on weights
    total_weight = sum(sector_allocation.values())
    remaining_slots = max_symbols

    for sector_path, weight in sorted_allocations:
        # Get universe symbols for this sector
        sector_symbols = get_symbols_by_path(sector_path)

        # Filter to available symbols
        valid_symbols = [s for s in sector_symbols if s in available]

        if not valid_symbols:
            logger.warning(f"No available symbols for sector: {sector_path}")
            continue

        # Calculate target count based on weight
        normalized_weight = weight / total_weight if total_weight > 0 else 0
        target_count = max(1, int(max_symbols * normalized_weight))
        target_count = min(target_count, remaining_slots, len(valid_symbols))

        # Select symbols (prioritize first in list)
        selected_for_sector = valid_symbols[:target_count]
        selected.extend(selected_for_sector)
        remaining_slots -= len(selected_for_sector)

        allocation_results[sector_path] = {
            'weight': weight,
            'target_count': target_count,
            'selected': selected_for_sector,
            'available': len(valid_symbols)
        }

        if remaining_slots <= 0:
            break

    # Remove duplicates while preserving order
    seen = set()
    unique_selected = []
    for symbol in selected:
        if symbol not in seen:
            seen.add(symbol)
            unique_selected.append(symbol)

    # If below minimum, try to fill from available sectors
    if len(unique_selected) < min_symbols:
        for sector_path, weight in sorted_allocations:
            if len(unique_selected) >= min_symbols:
                break

            sector_symbols = get_symbols_by_path(sector_path)
            valid_symbols = [s for s in sector_symbols if s in available and s not in seen]

            for symbol in valid_symbols:
                if len(unique_selected) >= min_symbols:
                    break
                unique_selected.append(symbol)
                seen.add(symbol)

    logger.info(f"Selected {len(unique_selected)} symbols from {len(sector_allocation)} sectors")
    return unique_selected


def get_symbols_for_strategy(strategy):
    """
    Get the symbol list for a strategy definition.

    Args:
        strategy: Strategy dict with 'sector_allocation', 'max_symbols', 'min_symbols'

    Returns:
        list: Selected symbols for the strategy
    """
    sector_allocation = strategy.get('sector_allocation', {})
    max_symbols = strategy.get('max_symbols', 20)
    min_symbols = strategy.get('min_symbols', 10)

    # If no sector allocation, fall back to static stocks list
    if not sector_allocation:
        return strategy.get('stocks', [])

    return get_symbols_for_allocation(
        sector_allocation,
        max_symbols=max_symbols,
        min_symbols=min_symbols
    )


def validate_strategy_allocation(sector_allocation):
    """
    Validate a sector allocation and return coverage report.

    Args:
        sector_allocation: Dict mapping sector paths to weights

    Returns:
        dict: Validation results with coverage and issues
    """
    available = load_symbols()
    results = {
        'valid': True,
        'total_weight': 0,
        'sectors': {},
        'issues': []
    }

    for sector_path, weight in sector_allocation.items():
        sector_symbols = get_symbols_by_path(sector_path)
        valid_symbols = [s for s in sector_symbols if s in available]

        results['total_weight'] += weight
        results['sectors'][sector_path] = {
            'weight': weight,
            'universe_count': len(sector_symbols),
            'available_count': len(valid_symbols),
            'symbols': valid_symbols
        }

        if not valid_symbols:
            results['valid'] = False
            results['issues'].append(f"No available symbols for {sector_path}")
        elif len(valid_symbols) < 2:
            results['issues'].append(f"Low coverage for {sector_path}: only {len(valid_symbols)} symbols")

    # Check weight totals
    if abs(results['total_weight'] - 1.0) > 0.01:
        results['issues'].append(f"Weights sum to {results['total_weight']:.2f}, not 1.0")

    return results


def get_sector_coverage_report():
    """
    Generate a report showing universe vs available symbols by sector.

    Returns:
        dict: Coverage statistics by sector
    """
    available = load_symbols()
    report = {}

    for sector, subsectors in SYMBOL_UNIVERSE.items():
        sector_total = 0
        sector_available = 0
        subsector_data = {}

        for subsector, symbols in subsectors.items():
            total = len(symbols)
            avail = len([s for s in symbols if s in available])
            sector_total += total
            sector_available += avail

            subsector_data[subsector] = {
                'total': total,
                'available': avail,
                'coverage': avail / total if total > 0 else 0,
                'missing': [s for s in symbols if s not in available]
            }

        report[sector] = {
            'total': sector_total,
            'available': sector_available,
            'coverage': sector_available / sector_total if sector_total > 0 else 0,
            'subsectors': subsector_data
        }

    return report
