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
import socket
import subprocess
import sys
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

# Force global socket timeout - catches DNS/SSL hangs that requests timeout misses
socket.setdefaulttimeout(10)

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
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}'

    resp = None
    try:
        if debug:
            print(f"\n  DEBUG: Trying {url}")
        resp = session.get(url, params=params, timeout=(5, 10))
        if debug:
            print(f"  DEBUG: Status={resp.status_code}, Length={len(resp.text)}")
    except Exception as e:
        if debug:
            print(f"  DEBUG: Exception: {e}")
        print(f"  {symbol}: Request failed ({e})")
        return []

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


def download_single_subprocess(symbol, yahoo_symbol, start_date, end_date,
                               full_refresh=False, debug=False, timeout=20):
    """
    Download a single symbol by spawning a subprocess.
    If the subprocess hangs, it gets killed after timeout seconds.

    Returns: (success: bool, rows_count: int)
    """
    script = os.path.abspath(__file__)
    cmd = [
        sys.executable, script, '--single',
        yahoo_symbol,
        symbol,
        str(start_date),
        str(end_date),
    ]
    if full_refresh:
        cmd.append('--full-refresh')
    if debug:
        cmd.append('--debug')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if debug and result.stderr:
            print(f"  DEBUG stderr: {result.stderr[:200]}")
        if result.returncode == 0 and result.stdout.strip():
            # Last line of output is the row count
            last_line = result.stdout.strip().split('\n')[-1].strip()
            try:
                count = int(last_line)
                return True, count
            except ValueError:
                return False, 0
        return False, 0
    except subprocess.TimeoutExpired:
        return False, -1  # -1 signals timeout
    except Exception as e:
        if debug:
            print(f"  DEBUG subprocess error: {e}")
        return False, 0


def run_single_symbol(yahoo_symbol, file_symbol, start_str, end_str,
                      full_refresh=False, debug=False):
    """
    Called when --single mode: download one symbol, save CSV, print row count.
    Exit code 0 = success, 1 = failure.
    """
    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

    session, crumb = get_yahoo_session()
    if session is None:
        sys.exit(1)

    rows = download_symbol(session, crumb, yahoo_symbol, start_date, end_date, debug=debug)

    if not rows:
        sys.exit(1)

    save_symbol_csv(file_symbol, rows, full_refresh=full_refresh)
    print(len(rows))
    sys.exit(0)


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

    BATCH_SIZE = 100

    stats = {
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'rows_added': 0,
    }

    # Process symbols in batches with a fresh session per batch
    for batch_start in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE

        print()
        print(f"--- Batch {batch_num}/{total_batches} (symbols {batch_start + 1}-{batch_start + len(batch)}) ---")
        print("Initializing Yahoo Finance session...")
        session, crumb = get_yahoo_session()
        if session is None:
            print("FATAL: Could not establish Yahoo Finance session")
            print("Waiting 10s before retrying...")
            time.sleep(10)
            session, crumb = get_yahoo_session()
            if session is None:
                print("FATAL: Skipping this batch")
                stats['failed'] += len(batch)
                stats['processed'] += len(batch)
                continue
        print("-" * 60)

        for j, symbol in enumerate(batch):
            i = batch_start + j + 1  # overall index
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

                # Run download in a subprocess with hard 20s kill timeout
                # (z/OS SSL hangs ignore requests timeout and thread timeout)
                ok, count = download_single_subprocess(
                    symbol, yahoo_symbol, start_date, end_date,
                    full_refresh=full_refresh, debug=debug, timeout=20
                )

                if count == -1:
                    print("SKIPPED (timed out)")
                    stats['failed'] += 1
                elif not ok:
                    print("no data")
                    stats['failed'] += 1
                else:
                    stats['success'] += 1
                    stats['rows_added'] += count
                    print(f"{count} rows")

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
    parser.add_argument(
        '--single',
        nargs=4,
        metavar=('YAHOO_SYM', 'FILE_SYM', 'START', 'END'),
        help=argparse.SUPPRESS  # internal: download one symbol and exit
    )

    args = parser.parse_args()

    # Internal single-symbol mode (called by subprocess)
    if args.single:
        run_single_symbol(
            args.single[0], args.single[1], args.single[2], args.single[3],
            full_refresh=args.full_refresh, debug=args.debug
        )
        return

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
