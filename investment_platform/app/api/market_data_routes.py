"""
Market Data API Routes

Endpoints for fetching and managing market price data.
Integrates with Yahoo Finance via MarketDataService with DB2 caching.
"""
from flask import Blueprint, jsonify, request
from datetime import date, datetime, timedelta, timezone

from app.models import MarketDataCache, MarketDataMetadata
from app.services.market_data_service import get_market_data_service
from app.data import get_all_symbols, is_valid_symbol

market_data_bp = Blueprint('market', __name__)


@market_data_bp.route('/price/<symbol>', methods=['GET'])
def get_price(symbol):
    """
    GET /api/market/price/<symbol>
    Returns current price for a symbol.

    Fetches from Yahoo Finance if not cached or cache is stale.
    Falls back to simulation if Yahoo Finance is unavailable.
    """
    symbol = symbol.upper()

    if not is_valid_symbol(symbol):
        return jsonify({
            'error': f'Unknown symbol: {symbol}',
            'message': 'Symbol not in trading universe'
        }), 404

    try:
        service = get_market_data_service()
        result = service.get_current_price(symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'error': 'Failed to get price',
            'message': str(e)
        }), 500


@market_data_bp.route('/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """
    GET /api/market/history/<symbol>
    Returns historical OHLCV data.

    Query params:
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - days: Alternative to start_date - number of days back (default: 30)
    """
    symbol = symbol.upper()

    if not is_valid_symbol(symbol):
        return jsonify({
            'error': f'Unknown symbol: {symbol}',
            'message': 'Symbol not in trading universe'
        }), 404

    # Parse date parameters
    end_date_str = request.args.get('end_date')
    start_date_str = request.args.get('start_date')
    days = request.args.get('days', type=int)

    try:
        if end_date_str:
            end_date = date.fromisoformat(end_date_str)
        else:
            end_date = date.today()

        if start_date_str:
            start_date = date.fromisoformat(start_date_str)
        elif days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = end_date - timedelta(days=30)

        service = get_market_data_service()
        df = service.get_price_data(symbol, start_date, end_date)

        if df.empty:
            return jsonify({
                'symbol': symbol,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'data': [],
                'count': 0,
                'message': 'No data available for this period'
            })

        # Convert DataFrame to list of dicts
        data = []
        for idx, row in df.iterrows():
            data.append({
                'date': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'open': row.get('open'),
                'high': row.get('high'),
                'low': row.get('low'),
                'close': row['close'],
                'adj_close': row['adj_close'],
                'volume': int(row['volume']) if row.get('volume') else None
            })

        return jsonify({
            'symbol': symbol,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data': data,
            'count': len(data)
        })

    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@market_data_bp.route('/prices', methods=['GET'])
def get_prices():
    """
    GET /api/market/prices?symbols=AAPL,MSFT,GOOGL
    Batch endpoint for multiple symbols.

    Returns current prices for all requested symbols.
    """
    symbols_param = request.args.get('symbols', '')
    if not symbols_param:
        return jsonify({'error': 'symbols parameter required'}), 400

    symbols = [s.strip().upper() for s in symbols_param.split(',')]
    service = get_market_data_service()

    results = {}
    for symbol in symbols:
        if not is_valid_symbol(symbol):
            results[symbol] = {'error': 'Unknown symbol'}
            continue

        try:
            price_data = service.get_current_price(symbol)
            results[symbol] = {
                'price': price_data['price'],
                'date': price_data['date'],
                'source': price_data['source']
            }
        except Exception as e:
            results[symbol] = {'error': str(e)}

    return jsonify({
        'prices': results,
        'count': len([r for r in results.values() if 'price' in r]),
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@market_data_bp.route('/ticker', methods=['GET'])
def get_ticker_data():
    """
    GET /api/market/ticker
    Returns ticker data with 5-day moving average comparison.

    Query params:
        - symbols: Comma-separated list of symbols (optional, defaults to major indices/stocks)

    Returns current price and percentage vs 5-day moving average for each symbol.
    """
    default_symbols = ['BTC-USD', 'ETH-USD', '^GSPC', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

    symbols_param = request.args.get('symbols', '')
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(',')]
    else:
        symbols = default_symbols

    service = get_market_data_service()
    end_date = date.today()
    start_date = end_date - timedelta(days=10)  # Fetch extra days to ensure 5 trading days

    results = {}
    for symbol in symbols:
        try:
            # Get current price
            price_data = service.get_current_price(symbol)
            current_price = price_data.get('price')

            if current_price is None:
                results[symbol] = {'error': 'No price data'}
                continue

            # Get historical data for 5-day MA
            df = service.get_price_data(symbol, start_date, end_date)

            if df.empty or len(df) < 2:
                # No historical data - just show price with 0% change
                results[symbol] = {
                    'price': current_price,
                    'change_pct': 0,
                    'ma5': current_price,
                    'source': price_data.get('source', 'unknown')
                }
                continue

            # Calculate 5-day moving average from closing prices
            close_col = 'adj_close' if 'adj_close' in df.columns else 'close'
            closes = df[close_col].dropna().tail(5)  # Last 5 trading days

            if len(closes) > 0:
                ma5 = closes.mean()
                change_pct = ((current_price - ma5) / ma5) * 100
            else:
                ma5 = current_price
                change_pct = 0

            results[symbol] = {
                'price': round(current_price, 2),
                'change_pct': round(change_pct, 2),
                'ma5': round(ma5, 2),
                'source': price_data.get('source', 'unknown')
            }

        except Exception as e:
            results[symbol] = {'error': str(e)}

    return jsonify({
        'ticker': results,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@market_data_bp.route('/symbols', methods=['GET'])
def get_symbols():
    """
    GET /api/market/symbols
    Returns list of all available symbols in the trading universe.
    """
    symbols = get_all_symbols()
    return jsonify({
        'symbols': symbols,
        'count': len(symbols)
    })


@market_data_bp.route('/cache/status', methods=['GET'])
def get_cache_status():
    """
    GET /api/market/cache/status
    Returns cache statistics for all or specific symbols.

    Query params:
        - symbol: Optional specific symbol to check
    """
    symbol = request.args.get('symbol')

    if symbol:
        symbol = symbol.upper()
        service = get_market_data_service()
        status = service.get_cache_status(symbol)
        return jsonify(status)

    # Get all cached symbols
    all_metadata = MarketDataMetadata.query.all()
    status = [m.to_dict() for m in all_metadata]

    return jsonify({
        'cache_entries': status,
        'total_symbols': len(status)
    })


@market_data_bp.route('/cache/refresh', methods=['POST'])
def refresh_cache():
    """
    POST /api/market/cache/refresh
    Force refresh cache for specified symbols.

    Request body:
        {
            "symbols": ["AAPL", "MSFT"]  // Optional, refreshes all if not specified
        }
    """
    data = request.get_json() or {}
    symbols = data.get('symbols', [])

    if not symbols:
        # Get all symbols from universe
        symbols = get_all_symbols()

    service = get_market_data_service()
    results = {}

    for symbol in symbols:
        symbol = symbol.upper()
        try:
            success = service.refresh_cache(symbol)
            results[symbol] = 'refreshed' if success else 'already up to date'
        except Exception as e:
            results[symbol] = f'error: {str(e)}'

    return jsonify({
        'results': results,
        'refreshed_count': len([r for r in results.values() if r == 'refreshed'])
    })


@market_data_bp.route('/cache/<symbol>', methods=['DELETE'])
def clear_cache(symbol):
    """
    DELETE /api/market/cache/<symbol>
    Clear cache for a specific symbol.
    """
    symbol = symbol.upper()

    try:
        service = get_market_data_service()
        deleted = service.clear_cache(symbol)

        return jsonify({
            'message': f'Cache cleared for {symbol}',
            'deleted_records': deleted
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@market_data_bp.route('/cache', methods=['DELETE'])
def clear_all_cache():
    """
    DELETE /api/market/cache
    Clear all cached market data.

    Use with caution - this will require re-fetching all data.
    """
    try:
        service = get_market_data_service()
        deleted = service.clear_cache()

        return jsonify({
            'message': 'All cache cleared',
            'deleted_records': deleted
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
