"""
Symbol Universe - Sector/Subsector Classifications

Defines all tradeable symbols organized by sector and subsector.
The system dynamically selects symbols from this universe based on
strategy constraints and availability in local data.
"""

# Symbol Universe organized by sector -> subsector -> symbols
SYMBOL_UNIVERSE = {
    # FINANCIALS
    'financials': {
        'banks': ['JPM', 'BAC', 'GS', 'MS', 'C', 'WFC', 'BK'],
        'insurance': ['AIG', 'MET', 'PRU', 'AFL', 'ALL', 'CB', 'HIG', 'PGR'],
        'asset_managers': ['BLK', 'BX', 'KKR', 'APO', 'BEN', 'IVZ'],
        'exchanges': ['CME', 'ICE', 'CBOE', 'NDAQ'],
        'payments': ['V', 'MA', 'AXP', 'COF', 'PYPL', 'FI']
    },

    # ENERGY
    'energy': {
        'integrated': ['XOM', 'CVX', 'COP'],
        'exploration': ['EOG', 'DVN', 'OXY', 'APA', 'FANG', 'EQT'],
        'services': ['SLB', 'BKR', 'HAL'],
        'refining': ['MPC', 'PSX', 'VLO'],
        'midstream': ['KMI', 'OKE', 'WMB']
    },

    # MATERIALS
    'materials': {
        'mining': ['FCX', 'NEM', 'NUE'],
        'chemicals': ['APD', 'LIN', 'DD', 'EMN', 'ECL', 'PPG'],
        'agriculture': ['CF', 'MOS'],
        'containers': ['BALL', 'AVY', 'PKG', 'IP']
    },

    # TECHNOLOGY
    'technology': {
        'semiconductors': ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'NXPI', 'ON', 'ADI'],
        'software': ['MSFT', 'CRM', 'ADBE', 'NOW', 'ORCL', 'INTU', 'CDNS', 'ADSK', 'PANW', 'CRWD', 'DDOG'],
        'hardware': ['AAPL', 'DELL', 'HPQ', 'HPE'],
        'internet': ['GOOGL', 'META', 'AMZN', 'NFLX'],
        'it_services': ['ACN', 'IBM', 'CSCO', 'CTSH', 'IT']
    },

    # UTILITIES
    'utilities': {
        'electric': ['NEE', 'DUK', 'AEP', 'SO', 'D', 'EXC', 'XEL', 'WEC', 'ED', 'ES', 'EIX', 'DTE', 'PPL', 'FE', 'CEG', 'ETR'],
        'gas': ['NI', 'ATO', 'OKE', 'CNP'],
        'water': ['AWK'],
        'multi': ['CMS', 'LNT', 'EVRG', 'PNW', 'NRG', 'AES', 'AEE', 'PEG']
    },

    # HEALTHCARE
    'healthcare': {
        'pharma': ['JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'BMY', 'AMGN', 'GILD', 'REGN', 'BIIB', 'MRNA'],
        'devices': ['MDT', 'ABT', 'BSX', 'ISRG', 'EW', 'DXCM', 'HOLX', 'RMD'],
        'services': ['UNH', 'HUM', 'CI', 'CVS', 'MCK', 'CAH', 'HCA', 'CNC', 'MOH'],
        'diagnostics': ['DHR', 'IQV', 'DGX', 'LH', 'IDXX']
    },

    # CONSUMER STAPLES
    'consumer_staples': {
        'food': ['PG', 'KO', 'PEP', 'GIS', 'K', 'CPB', 'KHC', 'MDLZ', 'HSY', 'SJM', 'CAG', 'HRL', 'MKC'],
        'household': ['CL', 'KMB', 'CHD', 'CLX'],
        'retail': ['WMT', 'COST', 'KR', 'DG', 'DLTR'],
        'tobacco': ['PM', 'MO'],
        'beverage': ['KDP', 'MNST', 'BF.B']
    },

    # CONSUMER DISCRETIONARY
    'consumer_discretionary': {
        'retail': ['HD', 'LOW', 'TGT', 'COST', 'ORLY', 'AZO', 'BBY', 'ROST', 'DECK'],
        'restaurants': ['MCD', 'SBUX', 'DPZ', 'CMG', 'DRI'],
        'apparel': ['NKE', 'LULU', 'RL'],
        'autos': ['GM', 'F'],
        'leisure': ['LVS', 'MGM', 'RCL', 'CCL', 'MAR', 'HLT', 'NCLH'],
        'ecommerce': ['AMZN', 'EBAY', 'ETSY']
    },

    # INDUSTRIALS
    'industrials': {
        'machinery': ['CAT', 'DE', 'CMI', 'EMR', 'ETN', 'PH', 'ROK', 'IR'],
        'aerospace': ['BA', 'LMT', 'RTX', 'GD', 'NOC', 'HII', 'LHX'],
        'transport': ['UNP', 'NSC', 'FDX', 'UPS', 'CSX', 'JBHT', 'ODFL', 'DAL', 'LUV'],
        'conglomerates': ['HON', 'MMM', 'GE'],
        'building': ['JCI', 'CARR', 'OTIS', 'MLM', 'VMC'],
        'services': ['WM', 'RSG', 'CTAS', 'FAST', 'GWW']
    },

    # REAL ESTATE
    'real_estate': {
        'data_centers': ['EQIX', 'DLR', 'AMT', 'CCI'],
        'industrial': ['PLD'],
        'residential': ['AVB', 'EQR', 'MAA', 'ESS', 'INVH', 'CPT'],
        'office': ['BXP', 'ARE'],
        'retail_reit': ['O', 'REG', 'KIM', 'FRT'],
        'storage': ['PSA', 'EXR', 'IRM'],
        'healthcare_reit': ['DOC', 'PEAK']
    },

    # COMMUNICATION SERVICES
    'communication': {
        'telecom': ['T', 'VZ', 'TMUS'],
        'media': ['DIS', 'CMCSA', 'NFLX', 'WBD', 'PARA', 'FOX', 'FOXA', 'NWS', 'NWSA'],
        'interactive': ['GOOGL', 'META', 'MTCH', 'EA', 'TTWO']
    },

    # FUTURES (Available in local data)
    'futures': {
        'energy': ['CL_F', 'NG_F'],  # Crude Oil, Natural Gas
        'metals': ['GC_F', 'PL_F'],  # Gold, Platinum
        'treasury': ['2YY_F'],       # 2-Year Treasury Yield
        'agriculture': ['KC_F', 'CT_F', 'LBR_F']  # Coffee, Cotton, Lumber
    },

    # CURRENCY (Available in local data)
    'currency': {
        'pairs': ['AUDUSD_X']  # AUD/USD
    },

    # CRYPTO PROXY (Via listed equities)
    'crypto': {
        'major': ['COIN']  # Coinbase as crypto proxy
    }
}


# Sector metadata for display
SECTOR_METADATA = {
    'financials': {
        'name': 'Financials',
        'description': 'Banks, insurance, asset managers, and payment processors',
        'color': '#3b82f6'
    },
    'energy': {
        'name': 'Energy',
        'description': 'Oil & gas exploration, production, refining, and services',
        'color': '#f97316'
    },
    'materials': {
        'name': 'Materials',
        'description': 'Mining, chemicals, and agricultural inputs',
        'color': '#84cc16'
    },
    'technology': {
        'name': 'Technology',
        'description': 'Software, semiconductors, hardware, and internet services',
        'color': '#06b6d4'
    },
    'utilities': {
        'name': 'Utilities',
        'description': 'Electric, gas, and water utilities',
        'color': '#eab308'
    },
    'healthcare': {
        'name': 'Healthcare',
        'description': 'Pharmaceuticals, medical devices, and healthcare services',
        'color': '#ec4899'
    },
    'consumer_staples': {
        'name': 'Consumer Staples',
        'description': 'Food, beverages, household products, and retail staples',
        'color': '#8b5cf6'
    },
    'consumer_discretionary': {
        'name': 'Consumer Discretionary',
        'description': 'Retail, restaurants, apparel, autos, and leisure',
        'color': '#f43f5e'
    },
    'industrials': {
        'name': 'Industrials',
        'description': 'Machinery, aerospace, transportation, and industrial services',
        'color': '#64748b'
    },
    'real_estate': {
        'name': 'Real Estate',
        'description': 'REITs across data centers, residential, office, and retail',
        'color': '#0ea5e9'
    },
    'communication': {
        'name': 'Communication Services',
        'description': 'Telecom, media, and interactive entertainment',
        'color': '#a855f7'
    },
    'futures': {
        'name': 'Futures',
        'description': 'Energy, metals, treasury, and agricultural futures',
        'color': '#22c55e'
    },
    'currency': {
        'name': 'Currency',
        'description': 'Foreign exchange pairs',
        'color': '#14b8a6'
    },
    'crypto': {
        'name': 'Crypto Proxy',
        'description': 'Cryptocurrency exposure via listed equities',
        'color': '#f59e0b'
    }
}


def get_all_sectors():
    """Get list of all sector names."""
    return list(SYMBOL_UNIVERSE.keys())


def get_subsectors(sector):
    """Get list of subsectors for a sector."""
    if sector in SYMBOL_UNIVERSE:
        return list(SYMBOL_UNIVERSE[sector].keys())
    return []


def get_sector_symbols(sector, subsector=None):
    """
    Get all symbols for a sector, optionally filtered by subsector.

    Args:
        sector: Sector name (e.g., 'financials')
        subsector: Optional subsector name (e.g., 'banks')

    Returns:
        List of symbols
    """
    if sector not in SYMBOL_UNIVERSE:
        return []

    if subsector:
        return SYMBOL_UNIVERSE[sector].get(subsector, [])

    # Return all symbols in sector
    all_symbols = []
    for subsec_symbols in SYMBOL_UNIVERSE[sector].values():
        all_symbols.extend(subsec_symbols)
    return all_symbols


def get_symbols_by_path(sector_path):
    """
    Get symbols using dot notation path.

    Args:
        sector_path: Path like 'financials.banks' or 'technology.semiconductors'

    Returns:
        List of symbols
    """
    parts = sector_path.split('.')
    if len(parts) == 1:
        return get_sector_symbols(parts[0])
    elif len(parts) == 2:
        return get_sector_symbols(parts[0], parts[1])
    return []


def get_all_symbols():
    """Get all symbols from the entire universe."""
    all_symbols = []
    for sector_data in SYMBOL_UNIVERSE.values():
        for subsec_symbols in sector_data.values():
            all_symbols.extend(subsec_symbols)
    return list(set(all_symbols))


def get_sector_for_symbol(symbol):
    """
    Find the sector and subsector for a given symbol.

    Args:
        symbol: Stock ticker

    Returns:
        tuple: (sector, subsector) or (None, None) if not found
    """
    symbol = symbol.upper()
    for sector, subsectors in SYMBOL_UNIVERSE.items():
        for subsector, symbols in subsectors.items():
            if symbol in symbols:
                return (sector, subsector)
    return (None, None)


def get_sector_metadata(sector):
    """Get display metadata for a sector."""
    return SECTOR_METADATA.get(sector, {
        'name': sector.replace('_', ' ').title(),
        'description': '',
        'color': '#6b7280'
    })
