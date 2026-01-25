"""
FRED Data Fetcher Script

Fetches macroeconomic data from the FRED API and saves to CSV files
for offline use in the macro trading strategy system.

Usage:
    python scripts/fetch_fred_data.py

Environment:
    FRED_API_KEY - Your FRED API key (get from https://fred.stlouisfed.org/docs/api/api_key.html)
"""
import os
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FRED API Configuration
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'

# All FRED series used by macro strategies
FRED_SERIES = {
    # Interest Rates
    'FEDFUNDS': 'Federal Funds Effective Rate',
    'T10Y2Y': '10-Year Treasury Minus 2-Year Treasury',
    'DFII10': '10-Year Treasury Inflation-Indexed Security',

    # Inflation
    'CPIAUCSL': 'Consumer Price Index for All Urban Consumers',
    'PCEPILFE': 'Personal Consumption Expenditures Excluding Food and Energy',
    'T10YIE': '10-Year Breakeven Inflation Rate',
    'PPIACO': 'Producer Price Index for All Commodities',

    # Growth and Activity
    'INDPRO': 'Industrial Production Index',
    'RSAFS': 'Advance Retail Sales',
    'USSLIND': 'Leading Index for the United States',

    # Credit and Financial Conditions
    'BAMLH0A0HYM2': 'ICE BofA US High Yield Index Option-Adjusted Spread',
    'NFCI': 'Chicago Fed National Financial Conditions Index',
    'M2SL': 'M2 Money Stock',
    'DRTSCILM': 'Net Percentage of Domestic Banks Tightening Standards for C&I Loans',

    # Labor
    'ICSA': 'Initial Claims',
    'UNRATE': 'Unemployment Rate',
}

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'fred_data'


def fetch_series(series_id, start_date=None, end_date=None):
    """
    Fetch a single FRED series.

    Args:
        series_id: FRED series identifier
        start_date: Start date (default: 5 years ago)
        end_date: End date (default: today)

    Returns:
        list: List of (date, value) tuples
    """
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY environment variable not set")
        return []

    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=5*365)

    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'observation_start': start_date.strftime('%Y-%m-%d'),
        'observation_end': end_date.strftime('%Y-%m-%d'),
        'sort_order': 'asc'
    }

    try:
        response = requests.get(FRED_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        observations = data.get('observations', [])
        result = []

        for obs in observations:
            date_str = obs.get('date')
            value_str = obs.get('value')

            if value_str and value_str != '.':
                try:
                    result.append((date_str, float(value_str)))
                except ValueError:
                    pass

        logger.info(f"Fetched {len(result)} observations for {series_id}")
        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching {series_id}: {e}")
        return []


def save_to_csv(series_id, data, description=''):
    """
    Save series data to CSV file.

    Args:
        series_id: FRED series identifier
        data: List of (date, value) tuples
        description: Series description for header comment
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filepath = OUTPUT_DIR / f"{series_id}.csv"

    with open(filepath, 'w', newline='', encoding='ascii') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'value'])

        for date_str, value in data:
            writer.writerow([date_str, value])

    logger.info(f"Saved {len(data)} rows to {filepath}")


def fetch_all_series():
    """Fetch all FRED series and save to CSV files."""
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY not set. Set it with:")
        logger.error("  export FRED_API_KEY='your_api_key_here'")
        logger.error("Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return False

    logger.info(f"Fetching {len(FRED_SERIES)} FRED series...")

    success_count = 0
    for series_id, description in FRED_SERIES.items():
        logger.info(f"Fetching {series_id}: {description}")

        data = fetch_series(series_id)
        if data:
            save_to_csv(series_id, data, description)
            success_count += 1
        else:
            logger.warning(f"No data for {series_id}")

    logger.info(f"Successfully fetched {success_count}/{len(FRED_SERIES)} series")
    return success_count == len(FRED_SERIES)


def get_latest_values():
    """Read latest values from all CSV files."""
    latest = {}

    if not OUTPUT_DIR.exists():
        logger.warning(f"FRED data directory not found: {OUTPUT_DIR}")
        return latest

    for csv_file in OUTPUT_DIR.glob('*.csv'):
        series_id = csv_file.stem

        try:
            with open(csv_file, 'r', encoding='ascii') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if rows:
                    last_row = rows[-1]
                    latest[series_id] = {
                        'date': last_row['date'],
                        'value': float(last_row['value'])
                    }
        except Exception as e:
            logger.error(f"Error reading {csv_file}: {e}")

    return latest


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch FRED macroeconomic data')
    parser.add_argument('--show-latest', action='store_true',
                        help='Show latest values from cached CSV files')
    parser.add_argument('--series', type=str,
                        help='Fetch specific series only (comma-separated)')
    args = parser.parse_args()

    if args.show_latest:
        latest = get_latest_values()
        if latest:
            print("\nLatest FRED Values:")
            print("-" * 60)
            for series_id, data in sorted(latest.items()):
                desc = FRED_SERIES.get(series_id, '')
                print(f"{series_id:15} {data['value']:>12.4f}  ({data['date']})")
                if desc:
                    print(f"{'':15} {desc}")
        else:
            print("No cached data found. Run without --show-latest to fetch data.")
        return

    if args.series:
        series_list = [s.strip().upper() for s in args.series.split(',')]
        for series_id in series_list:
            if series_id in FRED_SERIES:
                data = fetch_series(series_id)
                if data:
                    save_to_csv(series_id, data, FRED_SERIES[series_id])
            else:
                logger.warning(f"Unknown series: {series_id}")
    else:
        fetch_all_series()


if __name__ == '__main__':
    main()
