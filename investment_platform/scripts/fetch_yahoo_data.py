"""
Yahoo Finance Data Scraper

Fetches OHLCV market data from Yahoo Finance v8 chart API using requests
and saves it as CSV files in data/tickercsv/ (one file per symbol).

Designed to run on z/OS mainframe without yfinance dependency.

Usage:
    python scripts/fetch_yahoo_data.py [options]

Options:
    --symbols       Comma-separated list of symbols (default: all in symbols_filtered.csv)
    --days          Days of history to fetch (default: smart fill from last date)
    --full-refresh  Re-download all data from scratch (5 years)
    --delay         Delay between requests in seconds (default: 1.5)
    --debug         Print detailed debug output for troubleshooting

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
import threading
from datetime import datetime, date, timedelta, timezone
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

# Banner ticker symbols (always fetched in addition to the symbols list)
BANNER_SYMBOLS = ['BTC-USD', 'ETH-USD', '^GSPC', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']


def symbol_to_filename(symbol: str) -> str:
    """Convert a ticker symbol to a safe CSV filename (without .csv extension)."""
    if symbol.startswith('^'):
        return '_' + symbol[1:]  # ^GSPC -> _GSPC
    return symbol.replace('=', '_')  # CL=F -> CL_F


def filename_to_yahoo_symbol(symbol: str) -> str:
    """Convert a symbol from the symbols list to a Yahoo Finance query symbol.
    Symbols in the CSV use underscores for characters unsafe in filenames."""
    if symbol.endswith('_F'):
        return symbol[:-2] + '=F'  # CL_F -> CL=F (futures)
    return symbol


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


def get_yahoo_session() -> tuple:
    """
    Get a requests session with Yahoo Finance cookies and crumb token.

    Visits fc.yahoo.com to get the A3 auth cookie, then fetches the crumb
    from the crumb API endpoint.

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
        # Step 1: Visit fc.yahoo.com to get the A3 auth cookie
        session.get('https://fc.yahoo.com', timeout=15, allow_redirects=True)

        # Step 2: Get crumb using the session cookies
        crumb = None
        crumb_resp = session.get(
            'https://query2.finance.yahoo.com/v1/test/getcrumb',
            timeout=10
        )
        if crumb_resp.status_code == 200 and crumb_resp.text.strip():
            crumb = crumb_resp.text.strip()
            if '\\u' in crumb:
                crumb = crumb.encode().decode('unicode_escape')

        # Step 3: If that didn't work, try finance.yahoo.com + consent flow
        if not crumb:
            session.get('https://finance.yahoo.com/quote/AAPL/', timeout=15, allow_redirects=True)

            if BS4_AVAILABLE:
                resp = session.get('https://finance.yahoo.com/', timeout=15, allow_redirects=True)
                if 'consent' in resp.url or 'guce.yahoo' in resp.url:
                    print("  (handling consent redirect...)")
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    form = soup.find('form', {'method': 'post'}) or soup.find('form')
                    if form:
                        action = form.get('action', resp.url)
                        inputs = {}
                        for inp in form.find_all('input'):
                            name = inp.get('name')
                            if name:
                                inputs[name] = inp.get('value', '')
                        session.post(action, data=inputs, timeout=15, allow_redirects=True)

            crumb_resp = session.get(
                'https://query2.finance.yahoo.com/v1/test/getcrumb',
                timeout=10
            )
            if crumb_resp.status_code == 200 and crumb_resp.text.strip():
                crumb = crumb_resp.text.strip()
                if '\\u' in crumb:
                    crumb = crumb.encode().decode('unicode_escape')

        if crumb:
            print("Session ready (crumb: yes)")
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
    csv_path = DATA_DIR / f'{symbol_to_filename(symbol)}.csv'
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
                    date_str = row[0].split(' ')[0].split('T')[0]
                    try:
                        last_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        continue
        return last_date
    except Exception:
        return None


def download_symbol(session: requests.Session, crumb: str, symbol: str,
                    start_date: date, end_date: date, debug: bool = False) -> list:
    """
    Download OHLCV data for a single symbol from Yahoo Finance v8 chart API.

    Args:
        session: Authenticated requests session
        crumb: Yahoo Finance crumb token
        symbol: Stock ticker symbol
        start_date: Start date for data
        end_date: End date for data
        debug: Print detailed debug output

    Returns:
        List of rows [Date, Open, High, Low, Close, Volume], or empty list on failure.
        Returns None to signal session refresh needed (auth error / rate limit).
    """
    # Convert dates to Unix timestamps
    period1 = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    period2 = int(datetime.combine(end_date, datetime.min.time()).timestamp()) + 86400

    params = {
        'period1': period1,
        'period2': period2,
        'interval': '1d',
    }
    if crumb:
        params['crumb'] = crumb

    if debug:
        print(f"\n  DEBUG: period1={period1} period2={period2}")

    # Use v8 chart API (v7 download endpoint is deprecated)
    urls = [
        f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}',
        f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}',
    ]

    resp = None
    for url in urls:
        try:
            if debug:
                print(f"  DEBUG: Trying {url}")
            resp = session.get(url, params=params, timeout=(5, 10))
            if debug:
                print(f"  DEBUG: Status={resp.status_code}, Length={len(resp.text)}")
            if resp.status_code == 200:
                break
            if resp.status_code in (401, 403):
                if debug:
                    print(f"  DEBUG: Auth error, trying next endpoint")
                continue
        except requests.exceptions.Timeout:
            if debug:
                print(f"  DEBUG: Timeout on {url}")
            continue
        except Exception as e:
            if debug:
                print(f"  DEBUG: Exception: {e}")
            continue

    if resp is None:
        print(f"  {symbol}: All endpoints failed")
        return []

    try:
        if resp.status_code in (401, 403):
            return None  # Signal to refresh session

        if resp.status_code == 404:
            print(f"  {symbol}: Not found on Yahoo Finance")
            return []

        if resp.status_code == 429:
            print(f"  {symbol}: Rate limited (429)")
            return None  # Signal to retry

        resp.raise_for_status()

        # Parse JSON response from v8 chart API
        data = resp.json()
        chart = data.get('chart', {})
        result_list = chart.get('result')

        if not result_list:
            error = chart.get('error', {})
            if debug:
                print(f"  DEBUG: Chart error: {error}")
            return []

        result = result_list[0]
        timestamps = result.get('timestamp', [])
        indicators = result.get('indicators', {})
        quotes = indicators.get('quote', [{}])[0]

        if not timestamps:
            if debug:
                print(f"  DEBUG: No timestamps in response")
            return []

        opens = quotes.get('open', [])
        highs = quotes.get('high', [])
        lows = quotes.get('low', [])
        closes = quotes.get('close', [])
        volumes = quotes.get('volume', [])

        rows = []
        for i, ts in enumerate(timestamps):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            date_str = dt.strftime('%Y-%m-%d')

            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            l = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None

            # Skip rows with null values
            if any(x is None for x in (o, h, l, c, v)):
                continue

            rows.append([
                date_str,
                f'{o:.4f}',
                f'{h:.4f}',
                f'{l:.4f}',
                f'{c:.4f}',
                str(int(v))
            ])

        if debug:
            print(f"  DEBUG: Parsed {len(rows)} rows from {len(timestamps)} timestamps")

        return rows

    except Exception as e:
        print(f"  {symbol}: ERROR - {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return []


def save_symbol_csv(symbol: str, new_rows: list, full_refresh: bool = False):
    """
    Save or append OHLCV data to a symbol's CSV file.

    Args:
        symbol: Stock ticker symbol
        new_rows: List of [Date, Open, High, Low, Close, Volume] rows
        full_refresh: If True, overwrite existing file entirely
    """
    csv_path = DATA_DIR / f'{symbol_to_filename(symbol)}.csv'

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


def run_fetch(symbols, days=None, full_refresh=False, delay=1.5, debug=False):
    """
    Run one fetch cycle for the given symbols.

    Returns:
        stats dict with processed/success/failed/skipped/rows_added counts
    """
    today = date.today()
    default_history_days = 365 * 5  # 5 years

    print()
    print("=" * 60)
    print(f"Yahoo Finance CSV Scraper - {today}")
    print("=" * 60)
    print(f"Symbols: {len(symbols)}")
    print(f"Output:  {DATA_DIR}")
    print(f"Mode:    {'Full refresh' if full_refresh else 'Smart fill'}")
    print(f"Delay:   {delay}s between requests")
    print()

    # Initialize session
    print("Initializing Yahoo Finance session...")
    session, crumb = get_yahoo_session()
    if session is None:
        print("FATAL: Could not establish Yahoo Finance session")
        return None

    print("-" * 60)

    stats = {
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'rows_added': 0,
    }

    consecutive_fails = 0

    for i, symbol in enumerate(symbols, 1):
        stats['processed'] += 1

        try:
            yahoo_symbol = filename_to_yahoo_symbol(symbol)

            # Determine date range for this symbol
            if full_refresh:
                start_date = today - timedelta(days=default_history_days)
                end_date = today
            elif days:
                start_date = today - timedelta(days=days)
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

            # Run download in a thread with hard 15s timeout
            # (catches SSL hangs that ignore requests timeout on z/OS)
            result_box = [None]  # mutable container for thread result

            def _do_download():
                result_box[0] = download_symbol(session, crumb, yahoo_symbol, start_date, end_date, debug=debug)

            t = threading.Thread(target=_do_download, daemon=True)
            t.start()
            t.join(timeout=15)

            if t.is_alive():
                # Thread is still running = hung request. Abandon it and move on.
                print("SKIPPED (timed out)")
                stats['failed'] += 1
                continue

            rows = result_box[0]

            if rows is None:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    print("refreshing session...", end=' ', flush=True)
                    time.sleep(3)
                    session, crumb = get_yahoo_session()
                    consecutive_fails = 0
                    if session is None:
                        print("FAILED (session expired)")
                        stats['failed'] += 1
                        continue
                    result_box[0] = None
                    t2 = threading.Thread(target=_do_download, daemon=True)
                    t2.start()
                    t2.join(timeout=15)
                    if t2.is_alive():
                        print("SKIPPED (timed out)")
                        stats['failed'] += 1
                        continue
                    rows = result_box[0]
                if rows is None:
                    rows = []

            if not rows:
                print("no data")
                stats['failed'] += 1
            else:
                consecutive_fails = 0
                save_symbol_csv(symbol, rows, full_refresh=full_refresh)
                stats['success'] += 1
                stats['rows_added'] += len(rows)
                print(f"{len(rows)} rows")

        except Exception as e:
            print(f"SKIPPED - {e}")
            stats['failed'] += 1

        # Rate limiting delay (except for last symbol)
        if i < len(symbols):
            time.sleep(delay)

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

    return stats


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
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print detailed debug output for troubleshooting'
    )
    parser.add_argument(
        '--loop',
        type=float,
        nargs='?',
        const=24.0,
        default=None,
        metavar='HOURS',
        help='Run continuously, repeating every N hours (default: 24)'
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
        # Always include banner ticker symbols so the UI has data
        existing = set(symbols)
        for bs in BANNER_SYMBOLS:
            if bs not in existing:
                symbols.append(bs)
                existing.add(bs)

    if args.loop:
        interval_hours = args.loop
        interval_secs = interval_hours * 3600
        pid = os.getpid()
        print(f"Running in loop mode: every {interval_hours} hours")
        print(f"PID: {pid}")
        print(f"Stop with: kill {pid}")

        # Write scraper PID file
        pid_file = PROJECT_DIR / 'scraper.pid'
        try:
            pid_file.write_text(
                f"pid={pid}\n"
                f"interval={interval_hours}h\n"
                f"symbols={len(symbols)}\n"
                f"started={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        except Exception:
            pass

        # Also append scraper PID to server.pid if it exists
        server_pid_file = PROJECT_DIR / 'server.pid'
        try:
            if server_pid_file.exists():
                content = server_pid_file.read_text()
                if 'scraper_pid' not in content:
                    with open(server_pid_file, 'a') as f:
                        f.write(f"scraper_pid={pid}\n")
        except Exception:
            pass

        try:
            while True:
                run_fetch(symbols, days=args.days, full_refresh=args.full_refresh,
                          delay=args.delay, debug=args.debug)

                # Only full-refresh on the first run
                args.full_refresh = False

                next_run = datetime.now() + timedelta(seconds=interval_secs)
                print(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Sleeping {interval_hours} hours...")
                print()
                try:
                    time.sleep(interval_secs)
                except KeyboardInterrupt:
                    print("\nStopped.")
                    break
        finally:
            # Clean up PID file
            try:
                if pid_file.exists():
                    pid_file.unlink()
            except Exception:
                pass
    else:
        run_fetch(symbols, days=args.days, full_refresh=args.full_refresh,
                  delay=args.delay, debug=args.debug)
        print("Done!")


if __name__ == '__main__':
    main()
