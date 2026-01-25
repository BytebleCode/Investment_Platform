"""
Available Symbols Service

Loads and provides access to the list of available stock symbols
from the local CSV data.
"""
import csv
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

# Global cache for symbols
_symbols_cache = None


def _get_symbols_file_path():
    """Get the path to the symbols CSV file."""
    base_dir = Path(__file__).parent.parent.parent
    return base_dir / 'data' / 'tickercsv' / 'symbols_filtered.csv'


def load_symbols():
    """
    Load all available symbols from the CSV file.

    Returns:
        set: Set of available stock symbols
    """
    global _symbols_cache

    if _symbols_cache is not None:
        return _symbols_cache

    symbols_file = _get_symbols_file_path()

    if not symbols_file.exists():
        logger.warning(f"Symbols file not found: {symbols_file}")
        return set()

    try:
        symbols = set()
        with open(symbols_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    symbol = row[0].strip().upper()
                    # Skip header if present
                    if symbol != 'SYMBOL':
                        symbols.add(symbol)

        _symbols_cache = symbols
        logger.info(f"Loaded {len(symbols)} symbols from {symbols_file}")
        return symbols

    except Exception as e:
        logger.error(f"Error loading symbols: {e}")
        return set()


def get_all_symbols():
    """
    Get all available symbols as a sorted list.

    Returns:
        list: Sorted list of available stock symbols
    """
    return sorted(load_symbols())


def is_valid_symbol(symbol):
    """
    Check if a symbol is valid (exists in available symbols).

    Args:
        symbol: Stock ticker symbol

    Returns:
        bool: True if symbol is valid
    """
    if not symbol:
        return False
    return symbol.upper() in load_symbols()


def validate_symbols(symbols):
    """
    Validate a list of symbols and return valid/invalid lists.

    Args:
        symbols: List of stock symbols to validate

    Returns:
        tuple: (valid_symbols, invalid_symbols)
    """
    if not symbols:
        return [], []

    available = load_symbols()
    valid = []
    invalid = []

    for symbol in symbols:
        if symbol.upper() in available:
            valid.append(symbol.upper())
        else:
            invalid.append(symbol.upper())

    return valid, invalid


def search_symbols(query, limit=20):
    """
    Search for symbols matching a query.

    Args:
        query: Search string (matches start of symbol)
        limit: Maximum results to return

    Returns:
        list: List of matching symbols
    """
    if not query:
        return []

    query = query.upper()
    symbols = load_symbols()

    # First, find exact matches
    exact = [s for s in symbols if s == query]

    # Then, find symbols starting with query
    starts_with = [s for s in symbols if s.startswith(query) and s != query]

    # Then, find symbols containing query
    contains = [s for s in symbols if query in s and not s.startswith(query)]

    # Combine results
    results = exact + sorted(starts_with) + sorted(contains)

    return results[:limit]


def get_symbol_count():
    """
    Get the total number of available symbols.

    Returns:
        int: Number of available symbols
    """
    return len(load_symbols())


def refresh_symbols():
    """
    Force reload of symbols from file.

    Returns:
        int: Number of symbols loaded
    """
    global _symbols_cache
    _symbols_cache = None
    symbols = load_symbols()
    return len(symbols)
