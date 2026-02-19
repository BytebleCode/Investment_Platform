"""
Yahoo Finance Data Scraper

Fetches OHLCV market data from Yahoo Finance using requests + BeautifulSoup
and saves it as CSV files in data/tickercsv/ (one file per symbol).

Designed to run on z/OS mainframe without yfinance dependency.

Usage:
    python scripts/fetch_yahoo_data.py [options]

Options:
    --symbols       Comma-separated list of symbols (default: all in symbols_filtered.csv)
    --days          Days of history to fetch (default: smart fill from last date)
    --full-refresh  Re-download all data from scratch (5 years)
    --delay         Delay between requests in seconds (default: 1.5)

Examples:
    # Smart fill: fetch only missing dates for all symbols
    python scripts/fetch_yahoo_data.py

    # Fetch specific symbols
    python scripts/fetch_yahoo_data.py --symbols AAPL,MSFT,GOOGL

    # Fetch last 30 days for all symbols
    python scripts/fetch_yahoo_data.py --days 30

    # Full 5-year refresh for one symbol
    python scripts/fetch_yahoo_data.py --symbols AAPL --full-refresh
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / 'data' / 'tickercsv'
SYMBOLS_FILE = DATA_DIR / 'symbols_filtered.csv'

# CSV columns
CSV_COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']


def load_symbols() -> list:
    """Load symbols from symbols_filtered.csv."""
    if not SYMBOLS_FILE.exists():
        print(f"ERROR: Symbols file not found: {SYMBOLS_FILE}")
        return []

    symbols = []
    with open(SYMBOLS_FILE, 'r') as f:
        for line in f:
            sym = line.strip()
            if sym:
                symbols.append(sym)
    return symbols


def _extract_crumb_from_html(text: str) -> str:
    """Try to extract crumb token from HTML page content using multiple patterns."""
    import re

    # Pattern 1: "crumb":"value"
    match = re.search(r'"crumb"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1)

    # Pattern 2: crumb=value in URL-like strings
    match = re.search(r'crumb=([A-Za-z0-9_.~/-]+)', text)
    if match:
        return match.group(1)

    # Pattern 3: CrsrfToken or similar
    match = re.search(r'"CrumbStore"\s*:\s*\{\s*"crumb"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1)

    return None


def get_yahoo_session() -> tuple:
    """
    Get a requests session with Yahoo Finance cookies and crumb token.

    Tries multiple strategies:
    1. Visit finance.yahoo.com to collect cookies, then use crumb API
    2. Extract crumb from page HTML via regex
    3. Use consent flow if Yahoo redirects to consent page

    Returns:
        (session, crumb) tuple, or (None, None) on failure
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })

    try:
        # Step 1: Visit Yahoo Finance to get cookies
        # Use a simple page that's unlikely to be blocked
        resp = session.get('https://finance.yahoo.com/quote/AAPL/history/', timeout=15, allow_redirects=True)

        # Handle EU/consent redirect
        if 'consent' in resp.url or 'guce.yahoo' in resp.url:
            print("  (handling consent redirect...)")
            # Try to accept consent by posting to the consent form
            if BS4_AVAILABLE:
                soup = BeautifulSoup(resp.text, 'html.parser')
                form = soup.find('form', {'method': 'post'}) or soup.find('form')
                if form:
                    action = form.get('action', resp.url)
                    inputs = {}
                    for inp in form.find_all('input'):
                        name = inp.get('name')
                        if name:
                            inputs[name] = inp.get('value', '')
                    # Submit consent
                    resp = session.post(action, data=inputs, timeout=15, allow_redirects=True)

            # Revisit after consent
            resp = session.get('https://finance.yahoo.com/quote/AAPL/history/', timeout=15)

        # Step 2: Try the crumb API endpoint (most reliable method)
        crumb = None
        crumb_resp = session.get(
            'https://query2.finance.yahoo.com/v1/test/getcrumb',
            timeout=10
        )
        if crumb_resp.status_code == 200 and crumb_resp.text.strip():
            crumb = crumb_resp.text.strip()
            # Unescape unicode sequences like \u002F -> /
            crumb = crumb.encode().decode('unicode_escape') if '\\u' in crumb else crumb

        # Step 3: Fallback - extract crumb from page HTML
        if not crumb:
            crumb = _extract_crumb_from_html(resp.text)

        # Step 4: Try alternative - fetch a download page and extract crumb from redirect
        if not crumb:
            try:
                dl_resp = session.get(
                    'https://query1.finance.yahoo.com/v7/finance/download/AAPL'
                    '?period1=0&period2=9999999999&interval=1d&events=history',
                    timeout=10,
                    allow_redirects=False
                )
                if dl_resp.status_code == 302:
                    location = dl_resp.headers.get('Location', '')
                    import re
                    match = re.search(r'crumb=([^&]+)', location)
                    if match:
                        crumb = match.group(1)
            except Exception:
                pass

        if crumb:
            print(f"Session ready (crumb: yes)")
        else:
            print("WARNING: Could not extract crumb token. Trying downloads without crumb...")

        return session, crumb

    except Exception as e:
        print(f"ERROR: Failed to initialize Yahoo session: {e}")
        return None, None


def get_existing_last_date(symbol: str) -> date:
    """
    Check existing CSV file for the last date of data.

    Returns:
        The last date in the CSV, or None if no file/data exists.
    """
    csv_path = DATA_DIR / f'{symbol}.csv'
    if not csv_path.exists():
        return None

    try:
        last_date = None
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # skip header
            if not header:
                return None
            for row in reader:
                if row and row[0]:
                    # Parse date (handle both "2021-01-25" and "2021-01-25 00:00:00-05:00")
                    date_str = row[0].split(' ')[0].split('T')[0]
                    try:
                        last_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        continue
        return last_date
    except Exception:
        return None


def download_symbol(session: requests.Session, crumb: str, symbol: str,
                    start_date: date, end_date: date) -> list:
    """
    Download OHLCV data for a single symbol from Yahoo Finance.

    Args:
        session: Authenticated requests session
        crumb: Yahoo Finance crumb token
        symbol: Stock ticker symbol
        start_date: Start date for data
        end_date: End date for data

    Returns:
        List of rows [Date, Open, High, Low, Close, Volume], or empty list on failure
    """
    # Convert dates to Unix timestamps
    period1 = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    period2 = int(datetime.combine(end_date, datetime.min.time()).timestamp()) + 86400  # include end date

    params = {
        'period1': period1,
        'period2': period2,
        'interval': '1d',
        'events': 'history',
        'includeAdjustedClose': 'true',
    }
    if crumb:
        params['crumb'] = crumb

    # Try both query1 and query2 endpoints
    urls = [
        f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}',
        f'https://query2.finance.yahoo.com/v7/finance/download/{symbol}',
    ]

    resp = None
    for url in urls:
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 200 and resp.text.startswith('Date'):
                break  # Got valid CSV data
            if resp.status_code == 401 or resp.status_code == 403:
                # Try next endpoint before giving up
                continue
        except requests.exceptions.Timeout:
            continue
        except Exception:
            continue

    if resp is None:
        print(f"  {symbol}: All endpoints failed")
        return []

    try:
        if resp.status_code == 401 or resp.status_code == 403:
            # All endpoints returned auth error - need session refresh
            return None  # Signal to caller to refresh session

        if resp.status_code == 404:
            print(f"  {symbol}: Not found on Yahoo Finance")
            return []

        if resp.status_code == 429:
            print(f"  {symbol}: Rate limited (429). Waiting...")
            return None  # Signal to retry

        resp.raise_for_status()

        # Verify we got CSV, not an HTML error page
        if resp.text.strip().startswith('<') or resp.text.strip().startswith('{'):
            print(f"  {symbol}: Got non-CSV response")
            return None

        # Parse CSV response
        lines = resp.text.strip().split('\n')
        if len(lines) < 2:
            return []

        header = lines[0].split(',')
        rows = []

        # Find column indices
        col_map = {}
        for i, col in enumerate(header):
            col_lower = col.strip().lower()
            if col_lower == 'date':
                col_map['date'] = i
            elif col_lower == 'open':
                col_map['open'] = i
            elif col_lower == 'high':
                col_map['high'] = i
            elif col_lower == 'low':
                col_map['low'] = i
            elif col_lower == 'close':
                col_map['close'] = i
            elif col_lower == 'adj close':
                col_map['adj_close'] = i
            elif col_lower == 'volume':
                col_map['volume'] = i

        required = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(k in col_map for k in required):
            print(f"  {symbol}: Unexpected CSV format: {header}")
            return []

        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) < len(header):
                continue

            date_val = parts[col_map['date']].strip()
            open_val = parts[col_map['open']].strip()
            high_val = parts[col_map['high']].strip()
            low_val = parts[col_map['low']].strip()
            close_val = parts[col_map['close']].strip()
            volume_val = parts[col_map['volume']].strip()

            # Skip rows with null values
            if 'null' in (open_val, high_val, low_val, close_val, volume_val):
                continue

            rows.append([date_val, open_val, high_val, low_val, close_val, volume_val])

        return rows

    except requests.exceptions.Timeout:
        print(f"  {symbol}: Request timed out")
        return []
    except Exception as e:
        print(f"  {symbol}: ERROR - {e}")
        return []


def save_symbol_csv(symbol: str, new_rows: list, full_refresh: bool = False):
    """
    Save or append OHLCV data to a symbol's CSV file.

    Args:
        symbol: Stock ticker symbol
        new_rows: List of [Date, Open, High, Low, Close, Volume] rows
        full_refresh: If True, overwrite existing file entirely
    """
    csv_path = DATA_DIR / f'{symbol}.csv'

    if full_refresh or not csv_path.exists():
        # Write fresh file
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            writer.writerows(new_rows)
        return

    # Append mode: load existing dates to avoid duplicates
    existing_dates = set()
    existing_rows = []

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and row[0]:
                existing_dates.add(row[0].split(' ')[0].split('T')[0])
                existing_rows.append(row)

    # Add only new dates
    added = 0
    for row in new_rows:
        row_date = row[0].split(' ')[0].split('T')[0]
        if row_date not in existing_dates:
            existing_rows.append(row)
            added += 1

    # Sort by date and rewrite
    existing_rows.sort(key=lambda r: r[0])

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(existing_rows)

    return added


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch OHLCV data from Yahoo Finance and save as CSV files'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated list of symbols (default: all from symbols_filtered.csv)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='Days of history to fetch (default: smart fill from last date, or 5 years for new symbols)'
    )
    parser.add_argument(
        '--full-refresh',
        action='store_true',
        help='Re-download all data from scratch (5 years of history)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.5,
        help='Delay between requests in seconds (default: 1.5)'
    )

    args = parser.parse_args()

    # Ensure output directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Determine symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = load_symbols()
        if not symbols:
            print("No symbols to process. Check symbols_filtered.csv")
            return

    today = date.today()
    default_history_days = 365 * 5  # 5 years

    print()
    print("=" * 60)
    print("Yahoo Finance CSV Scraper")
    print("=" * 60)
    print(f"Symbols: {len(symbols)}")
    print(f"Output:  {DATA_DIR}")
    print(f"Mode:    {'Full refresh' if args.full_refresh else 'Smart fill'}")
    print(f"Delay:   {args.delay}s between requests")
    print()

    # Initialize session
    print("Initializing Yahoo Finance session...")
    session, crumb = get_yahoo_session()
    if session is None:
        print("FATAL: Could not establish Yahoo Finance session")
        return

    print("-" * 60)

    # Stats
    stats = {
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'rows_added': 0,
    }

    for i, symbol in enumerate(symbols, 1):
        stats['processed'] += 1

        # Determine date range for this symbol
        if args.full_refresh:
            start_date = today - timedelta(days=default_history_days)
            end_date = today
        elif args.days:
            start_date = today - timedelta(days=args.days)
            end_date = today
        else:
            # Smart fill: check existing CSV
            last_date = get_existing_last_date(symbol)
            if last_date:
                start_date = last_date + timedelta(days=1)
                end_date = today
                if start_date > end_date:
                    print(f"[{i}/{len(symbols)}] {symbol}: Already up to date (last: {last_date})")
                    stats['skipped'] += 1
                    continue
            else:
                # No existing data, fetch 5 years
                start_date = today - timedelta(days=default_history_days)
                end_date = today

        print(f"[{i}/{len(symbols)}] {symbol}: {start_date} to {end_date} ...", end=' ', flush=True)

        # Download data
        rows = download_symbol(session, crumb, symbol, start_date, end_date)

        if rows is None:
            # Session expired or rate limited - refresh and retry once
            print("refreshing session...", end=' ', flush=True)
            time.sleep(3)
            session, crumb = get_yahoo_session()
            if session is None:
                print("FAILED (session expired)")
                stats['failed'] += 1
                continue
            rows = download_symbol(session, crumb, symbol, start_date, end_date)

        if rows is None:
            rows = []

        if not rows:
            print("no data")
            stats['failed'] += 1
        else:
            save_symbol_csv(symbol, rows, full_refresh=args.full_refresh)
            stats['success'] += 1
            stats['rows_added'] += len(rows)
            print(f"{len(rows)} rows")

        # Rate limiting delay (except for last symbol)
        if i < len(symbols):
            time.sleep(args.delay)

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed: {stats['processed']}")
    print(f"Success:   {stats['success']}")
    print(f"Failed:    {stats['failed']}")
    print(f"Skipped:   {stats['skipped']} (already up to date)")
    print(f"Rows:      {stats['rows_added']}")
    print()
    print("Done!")


if __name__ == '__main__':
    main()
