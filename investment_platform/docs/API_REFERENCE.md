# Investment Platform API Reference

## Overview

The Investment Platform REST API provides endpoints for portfolio management, trading, market data, and strategy customization.

**Base URL:** `/api`

**Content-Type:** `application/json`

---

## Table of Contents

1. [Health & Status](#health--status)
2. [Portfolio Endpoints](#portfolio-endpoints)
3. [Holdings Endpoints](#holdings-endpoints)
4. [Trade Endpoints](#trade-endpoints)
5. [Strategy Endpoints](#strategy-endpoints)
6. [Market Data Endpoints](#market-data-endpoints)
7. [Trading Endpoints](#trading-endpoints)
8. [Error Handling](#error-handling)

---

## Health & Status

### GET /api/health

Check API health and service status.

**Response:**
```json
{
    "status": "ok",
    "timestamp": "2024-01-15T10:30:00Z",
    "database": "connected",
    "market_status": "open"
}
```

---

## Portfolio Endpoints

### GET /api/portfolio/settings

Get current portfolio configuration and state.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| user_id   | string | No       | User ID (default: "default") |

**Response:**
```json
{
    "user_id": "default",
    "initial_value": 100000.00,
    "current_cash": 45000.00,
    "current_strategy": "balanced",
    "is_initialized": true,
    "realized_gains": 1250.00,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### PUT /api/portfolio/settings

Update portfolio settings.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| user_id   | string | No       | User ID (default: "default") |

**Request Body:**
```json
{
    "current_strategy": "growth",
    "is_initialized": true
}
```

**Updatable Fields:**
- `current_strategy` - One of: conservative, growth, value, balanced, aggressive
- `is_initialized` - Boolean
- `realized_gains` - Decimal (usually updated by trades)

**Response:** Updated portfolio object

### PUT /api/portfolio/cash

Update cash balance.

**Request Body:**
```json
{
    "current_cash": 75000.00
}
```

**Response:** Updated portfolio object

### POST /api/portfolio/reset

Reset portfolio to initial state. Clears all holdings and trade history.

**Response:**
```json
{
    "message": "Portfolio reset successfully",
    "initial_value": 100000.00,
    "current_cash": 100000.00
}
```

---

## Holdings Endpoints

### GET /api/holdings

Get all current holdings.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| user_id   | string | No       | User ID (default: "default") |

**Response:**
```json
[
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "quantity": 100,
        "avg_cost": 150.00,
        "current_price": 175.00,
        "current_value": 17500.00,
        "unrealized_gain": 2500.00,
        "unrealized_gain_percent": 16.67
    }
]
```

### PUT /api/holdings

Bulk replace all holdings.

**Request Body:**
```json
[
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "quantity": 100,
        "avg_cost": 150.00
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "quantity": 50,
        "avg_cost": 300.00
    }
]
```

**Response:** Array of updated holdings

---

## Trade Endpoints

### POST /api/trades

Record a new trade.

**Request Body:**
```json
{
    "trade_id": "trade-2024-001",
    "timestamp": "2024-01-15T10:30:00Z",
    "type": "buy",
    "symbol": "AAPL",
    "stock_name": "Apple Inc.",
    "sector": "Technology",
    "quantity": 10,
    "price": 175.00,
    "total": 1750.00,
    "fees": 1.75,
    "strategy": "growth"
}
```

**Required Fields:**
- `trade_id` - Unique identifier
- `type` - "buy" or "sell"
- `symbol` - Stock ticker
- `quantity` - Number of shares (positive integer)
- `price` - Price per share
- `total` - Total transaction amount

**Response:** `201 Created`
```json
{
    "trade_id": "trade-2024-001",
    "type": "buy",
    "symbol": "AAPL",
    "quantity": 10,
    "price": 175.00,
    "total": 1750.00,
    "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /api/trades

Get trade history.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| user_id   | string | No       | User ID (default: "default") |
| limit     | int    | No       | Max trades to return (default: 100) |
| type      | string | No       | Filter by type: "buy" or "sell" |

**Response:**
```json
[
    {
        "trade_id": "trade-2024-001",
        "timestamp": "2024-01-15T10:30:00Z",
        "type": "buy",
        "symbol": "AAPL",
        "stock_name": "Apple Inc.",
        "sector": "Technology",
        "quantity": 10,
        "price": 175.00,
        "total": 1750.00,
        "fees": 1.75,
        "strategy": "growth"
    }
]
```

---

## Strategy Endpoints

### GET /api/strategies/customizations

Get all strategy customizations for user.

**Response:**
```json
{
    "conservative": {
        "confidence_level": 50,
        "trade_frequency": "low",
        "max_position_size": 10,
        "stop_loss_percent": 5,
        "take_profit_percent": 15,
        "auto_rebalance": true,
        "reinvest_dividends": true
    },
    "growth": {
        "confidence_level": 75,
        "trade_frequency": "high",
        "max_position_size": 20
    }
}
```

### PUT /api/strategies/customizations/{strategy_id}

Update or create a strategy customization.

**Path Parameters:**
- `strategy_id` - One of: conservative, growth, value, balanced, aggressive

**Request Body:**
```json
{
    "confidence_level": 80,
    "trade_frequency": "high",
    "max_position_size": 25,
    "stop_loss_percent": 8,
    "take_profit_percent": 30,
    "auto_rebalance": true,
    "reinvest_dividends": true
}
```

**Field Validation:**
| Field | Type | Range/Values |
|-------|------|--------------|
| confidence_level | int | 10-100 |
| trade_frequency | string | low, medium, high |
| max_position_size | int | 5-50 |
| stop_loss_percent | int | 5-30 |
| take_profit_percent | int | 10-100 |
| auto_rebalance | bool | true/false |
| reinvest_dividends | bool | true/false |

**Response:** Updated customization object

---

## Market Data Endpoints

### GET /api/market/price/{symbol}

Get current price for a symbol.

**Path Parameters:**
- `symbol` - Stock ticker (e.g., AAPL)

**Response:**
```json
{
    "symbol": "AAPL",
    "price": 175.25,
    "change": 2.50,
    "change_percent": 1.45,
    "volume": 45000000,
    "timestamp": "2024-01-15T16:00:00Z",
    "source": "yahoo"
}
```

**Source Values:**
- `yahoo` - Real data from Yahoo Finance
- `simulated` - Fallback simulated data (GBM)
- `cache` - Data from DB2 cache

### GET /api/market/prices

Get prices for multiple symbols.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| symbols   | string | Yes      | Comma-separated symbols |

**Example:** `/api/market/prices?symbols=AAPL,MSFT,GOOGL`

**Response:**
```json
{
    "AAPL": {
        "price": 175.25,
        "change": 2.50,
        "change_percent": 1.45
    },
    "MSFT": {
        "price": 380.00,
        "change": -1.25,
        "change_percent": -0.33
    }
}
```

### GET /api/market/history/{symbol}

Get historical OHLCV data.

**Query Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| start_date | date  | No       | Start date (ISO format) |
| end_date   | date  | No       | End date (ISO format) |
| interval   | string| No       | daily, weekly, monthly |

**Response:**
```json
[
    {
        "date": "2024-01-15",
        "open": 173.00,
        "high": 176.50,
        "low": 172.50,
        "close": 175.25,
        "adj_close": 175.25,
        "volume": 45000000
    }
]
```

### GET /api/market/cache/status

Get cache statistics.

**Response:**
```json
{
    "AAPL": {
        "earliest_date": "2019-01-15",
        "latest_date": "2024-01-15",
        "total_records": 1260,
        "last_updated": "2024-01-15T10:00:00Z",
        "status": "complete"
    }
}
```

### POST /api/market/cache/refresh

Force refresh cache for symbols.

**Request Body:**
```json
{
    "symbols": ["AAPL", "MSFT"]
}
```

**Response:**
```json
{
    "message": "Cache refresh initiated",
    "symbols": ["AAPL", "MSFT"],
    "status": "processing"
}
```

**Rate Limit:** 5 requests per minute

### DELETE /api/market/cache/{symbol}

Clear cache for a symbol.

**Response:**
```json
{
    "message": "Cache cleared for AAPL"
}
```

---

## Trading Endpoints

### POST /api/trading/auto

Execute automatic trade based on strategy.

**Request Body:**
```json
{
    "prices": {
        "AAPL": 175.25,
        "MSFT": 380.00,
        "GOOGL": 140.50
    }
}
```

**Response:**
```json
{
    "trade": {
        "trade_id": "auto-2024-001",
        "type": "buy",
        "symbol": "AAPL",
        "quantity": 5,
        "price": 175.35,
        "total": 876.75
    },
    "strategy": "balanced",
    "reason": "Investment ratio below target"
}
```

### GET /api/trading/status

Get trading engine status.

**Response:**
```json
{
    "auto_trading_enabled": true,
    "current_strategy": "balanced",
    "last_trade_time": "2024-01-15T10:30:00Z",
    "trades_today": 3,
    "investment_ratio": 0.65,
    "target_ratio": 0.70
}
```

---

## Error Handling

### Error Response Format

All errors return a consistent JSON format:

```json
{
    "error": "Error type",
    "message": "Detailed error description",
    "field": "field_name"  // For validation errors
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200  | Success |
| 201  | Created |
| 400  | Bad Request - Invalid input |
| 404  | Not Found - Resource doesn't exist |
| 409  | Conflict - Duplicate resource |
| 415  | Unsupported Media Type - Wrong Content-Type |
| 422  | Unprocessable Entity - Validation failed |
| 429  | Too Many Requests - Rate limited |
| 500  | Internal Server Error |

### Validation Errors

```json
{
    "error": "Validation Error",
    "message": "Invalid input data",
    "errors": {
        "confidence_level": ["Must be between 10 and 100"],
        "trade_frequency": ["Must be one of: low, medium, high"]
    }
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Default | 200/day, 50/hour |
| /api/market/cache/refresh | 5/minute |
| /api/trading/auto | 60/hour |

---

## Authentication

Currently, the API uses a simple `user_id` query parameter for user identification.

For production deployments, implement proper authentication:
- JWT tokens
- API keys
- OAuth 2.0

---

## Examples

### cURL Examples

**Get Portfolio:**
```bash
curl -X GET "http://localhost:5000/api/portfolio/settings?user_id=default"
```

**Execute Trade:**
```bash
curl -X POST "http://localhost:5000/api/trades" \
  -H "Content-Type: application/json" \
  -d '{
    "trade_id": "manual-001",
    "type": "buy",
    "symbol": "AAPL",
    "quantity": 10,
    "price": 175.00,
    "total": 1750.00
  }'
```

**Get Market Prices:**
```bash
curl -X GET "http://localhost:5000/api/market/prices?symbols=AAPL,MSFT,GOOGL"
```

### Python Examples

```python
import requests

BASE_URL = 'http://localhost:5000/api'

# Get portfolio
response = requests.get(f'{BASE_URL}/portfolio/settings')
portfolio = response.json()
print(f"Cash: ${portfolio['current_cash']:,.2f}")

# Get market prices
response = requests.get(f'{BASE_URL}/market/prices',
                       params={'symbols': 'AAPL,MSFT,GOOGL'})
prices = response.json()
for symbol, data in prices.items():
    print(f"{symbol}: ${data['price']:.2f}")
```
