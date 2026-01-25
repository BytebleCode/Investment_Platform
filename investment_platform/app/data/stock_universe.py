"""
Stock Universe Data Definitions

Contains metadata for all 50 stocks available for trading, organized by sector.
Each stock includes symbol, name, sector, base price, and beta (volatility factor).
"""

# Stock Universe - 50 stocks across 8 sectors
STOCK_UNIVERSE = {
    # Technology (10 stocks)
    'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology', 'base_price': 175.00, 'beta': 1.20},
    'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology', 'base_price': 380.00, 'beta': 1.10},
    'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Technology', 'base_price': 140.00, 'beta': 1.15},
    'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Technology', 'base_price': 175.00, 'beta': 1.25},
    'NVDA': {'name': 'NVIDIA Corporation', 'sector': 'Technology', 'base_price': 480.00, 'beta': 1.70},
    'META': {'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'base_price': 350.00, 'beta': 1.35},
    'TSLA': {'name': 'Tesla Inc.', 'sector': 'Technology', 'base_price': 250.00, 'beta': 2.00},
    'AMD': {'name': 'Advanced Micro Devices', 'sector': 'Technology', 'base_price': 120.00, 'beta': 1.80},
    'INTC': {'name': 'Intel Corporation', 'sector': 'Technology', 'base_price': 35.00, 'beta': 1.05},
    'CRM': {'name': 'Salesforce Inc.', 'sector': 'Technology', 'base_price': 270.00, 'beta': 1.25},

    # Healthcare (7 stocks)
    'JNJ': {'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'base_price': 160.00, 'beta': 0.55},
    'UNH': {'name': 'UnitedHealth Group', 'sector': 'Healthcare', 'base_price': 520.00, 'beta': 0.75},
    'PFE': {'name': 'Pfizer Inc.', 'sector': 'Healthcare', 'base_price': 28.00, 'beta': 0.65},
    'ABBV': {'name': 'AbbVie Inc.', 'sector': 'Healthcare', 'base_price': 155.00, 'beta': 0.70},
    'MRK': {'name': 'Merck & Co.', 'sector': 'Healthcare', 'base_price': 115.00, 'beta': 0.50},
    'LLY': {'name': 'Eli Lilly and Company', 'sector': 'Healthcare', 'base_price': 580.00, 'beta': 0.85},
    'TMO': {'name': 'Thermo Fisher Scientific', 'sector': 'Healthcare', 'base_price': 540.00, 'beta': 0.90},

    # Finance (8 stocks)
    'JPM': {'name': 'JPMorgan Chase & Co.', 'sector': 'Finance', 'base_price': 170.00, 'beta': 1.15},
    'BAC': {'name': 'Bank of America Corp', 'sector': 'Finance', 'base_price': 32.00, 'beta': 1.35},
    'WFC': {'name': 'Wells Fargo & Company', 'sector': 'Finance', 'base_price': 45.00, 'beta': 1.20},
    'GS': {'name': 'Goldman Sachs Group', 'sector': 'Finance', 'base_price': 380.00, 'beta': 1.40},
    'MS': {'name': 'Morgan Stanley', 'sector': 'Finance', 'base_price': 85.00, 'beta': 1.45},
    'V': {'name': 'Visa Inc.', 'sector': 'Finance', 'base_price': 275.00, 'beta': 0.95},
    'MA': {'name': 'Mastercard Inc.', 'sector': 'Finance', 'base_price': 420.00, 'beta': 1.00},
    'BRK.B': {'name': 'Berkshire Hathaway', 'sector': 'Finance', 'base_price': 360.00, 'beta': 0.90},

    # Consumer (8 stocks)
    'PG': {'name': 'Procter & Gamble', 'sector': 'Consumer', 'base_price': 155.00, 'beta': 0.45},
    'KO': {'name': 'Coca-Cola Company', 'sector': 'Consumer', 'base_price': 60.00, 'beta': 0.55},
    'PEP': {'name': 'PepsiCo Inc.', 'sector': 'Consumer', 'base_price': 175.00, 'beta': 0.60},
    'WMT': {'name': 'Walmart Inc.', 'sector': 'Consumer', 'base_price': 165.00, 'beta': 0.50},
    'COST': {'name': 'Costco Wholesale', 'sector': 'Consumer', 'base_price': 570.00, 'beta': 0.75},
    'MCD': {'name': "McDonald's Corporation", 'sector': 'Consumer', 'base_price': 290.00, 'beta': 0.65},
    'NKE': {'name': 'Nike Inc.', 'sector': 'Consumer', 'base_price': 105.00, 'beta': 1.10},
    'SBUX': {'name': 'Starbucks Corporation', 'sector': 'Consumer', 'base_price': 95.00, 'beta': 0.95},

    # Energy (5 stocks)
    'XOM': {'name': 'Exxon Mobil Corporation', 'sector': 'Energy', 'base_price': 105.00, 'beta': 1.00},
    'CVX': {'name': 'Chevron Corporation', 'sector': 'Energy', 'base_price': 155.00, 'beta': 1.05},
    'COP': {'name': 'ConocoPhillips', 'sector': 'Energy', 'base_price': 115.00, 'beta': 1.35},
    'SLB': {'name': 'Schlumberger Limited', 'sector': 'Energy', 'base_price': 50.00, 'beta': 1.50},
    'EOG': {'name': 'EOG Resources Inc.', 'sector': 'Energy', 'base_price': 125.00, 'beta': 1.40},

    # Industrial (5 stocks)
    'CAT': {'name': 'Caterpillar Inc.', 'sector': 'Industrial', 'base_price': 280.00, 'beta': 1.10},
    'BA': {'name': 'Boeing Company', 'sector': 'Industrial', 'base_price': 210.00, 'beta': 1.55},
    'HON': {'name': 'Honeywell International', 'sector': 'Industrial', 'base_price': 200.00, 'beta': 1.00},
    'UPS': {'name': 'United Parcel Service', 'sector': 'Industrial', 'base_price': 155.00, 'beta': 1.05},
    'DE': {'name': 'Deere & Company', 'sector': 'Industrial', 'base_price': 400.00, 'beta': 1.15},

    # Utilities (3 stocks)
    'NEE': {'name': 'NextEra Energy Inc.', 'sector': 'Utilities', 'base_price': 70.00, 'beta': 0.50},
    'DUK': {'name': 'Duke Energy Corporation', 'sector': 'Utilities', 'base_price': 100.00, 'beta': 0.40},
    'SO': {'name': 'Southern Company', 'sector': 'Utilities', 'base_price': 72.00, 'beta': 0.45},

    # High Risk / Speculative (4 stocks)
    'COIN': {'name': 'Coinbase Global Inc.', 'sector': 'Speculative', 'base_price': 180.00, 'beta': 2.50},
    'MSTR': {'name': 'MicroStrategy Inc.', 'sector': 'Speculative', 'base_price': 500.00, 'beta': 2.80},
    'RIVN': {'name': 'Rivian Automotive', 'sector': 'Speculative', 'base_price': 18.00, 'beta': 2.20},
    'PLTR': {'name': 'Palantir Technologies', 'sector': 'Speculative', 'base_price': 22.00, 'beta': 2.10},
}

# Available sectors
SECTORS = [
    'Technology',
    'Healthcare',
    'Finance',
    'Consumer',
    'Energy',
    'Industrial',
    'Utilities',
    'Speculative'
]


def get_all_symbols() -> list:
    """Return list of all stock symbols."""
    return list(STOCK_UNIVERSE.keys())


def get_stock_info(symbol: str) -> dict:
    """
    Get metadata for a specific stock.

    Args:
        symbol: Stock ticker symbol (case-insensitive)

    Returns:
        Dict with name, sector, base_price, beta or None if not found
    """
    return STOCK_UNIVERSE.get(symbol.upper())


def get_stocks_by_sector(sector: str) -> list:
    """
    Get all stocks in a specific sector.

    Args:
        sector: Sector name

    Returns:
        List of tuples (symbol, stock_info)
    """
    return [
        (symbol, info)
        for symbol, info in STOCK_UNIVERSE.items()
        if info['sector'] == sector
    ]


def get_sector_symbols(sector: str) -> list:
    """
    Get just the symbols for a sector.

    Args:
        sector: Sector name

    Returns:
        List of symbol strings
    """
    return [
        symbol
        for symbol, info in STOCK_UNIVERSE.items()
        if info['sector'] == sector
    ]


def get_stock_beta(symbol: str) -> float:
    """
    Get beta (volatility factor) for a stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Beta value or 1.0 if not found
    """
    info = get_stock_info(symbol)
    return info['beta'] if info else 1.0


def get_stock_name(symbol: str) -> str:
    """
    Get company name for a stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Company name or symbol if not found
    """
    info = get_stock_info(symbol)
    return info['name'] if info else symbol


def get_stock_sector(symbol: str) -> str:
    """
    Get sector for a stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Sector name or 'Unknown' if not found
    """
    info = get_stock_info(symbol)
    return info['sector'] if info else 'Unknown'


def is_valid_symbol(symbol: str) -> bool:
    """Check if symbol exists in the universe."""
    return symbol.upper() in STOCK_UNIVERSE
