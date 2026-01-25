# Investment Platform User Guide

## Overview

The Investment Platform is a portfolio management and trading simulation system that allows you to:

- Track your investment portfolio
- Execute trades (buy/sell stocks)
- Choose from 5 different investment strategies
- Monitor real-time market data
- View trade history and performance

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Portfolio Management](#portfolio-management)
4. [Trading](#trading)
5. [Strategies](#strategies)
6. [Market Data](#market-data)
7. [FAQ](#faq)

---

## Getting Started

### Accessing the Platform

Open your web browser and navigate to:
- **Dashboard:** `http://your-server:5000/dashboard/`
- **API:** `http://your-server:5000/api/`

### Initial Portfolio

When you first access the platform, you'll start with:
- **$100,000** in cash
- **No holdings** (empty portfolio)
- **Balanced** strategy selected

---

## Dashboard Overview

The dashboard is divided into several sections:

```
┌─────────────────────────────────────────────────────────┐
│                    HEADER / NAVBAR                       │
│  [Strategy: Balanced ▼]              [Auto-Trade: OFF]  │
├───────────────────────────────┬─────────────────────────┤
│                               │                         │
│    PORTFOLIO CHART            │   PORTFOLIO SUMMARY     │
│    (Performance over time)    │   - Cash: $45,000       │
│                               │   - Invested: $55,000   │
│                               │   - Return: +5.5%       │
│                               │   - Est. Tax: $1,850    │
├───────────────────────────────┼─────────────────────────┤
│                               │                         │
│    STRATEGY SELECTOR          │   ALLOCATION PIE        │
│    [Conservative] [Growth]    │   (By Stock/Sector)     │
│    [Value] [Balanced]         │                         │
│    [Aggressive]               │                         │
├───────────────────────────────┴─────────────────────────┤
│                                                          │
│    HOLDINGS TABLE                                        │
│    Symbol | Name | Qty | Avg Cost | Price | Gain/Loss   │
│    AAPL   | Apple| 100 | $150.00  | $175  | +$2,500     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    TRADE HISTORY                                         │
│    [All] [Buy] [Sell]                                   │
│    - Jan 15: BUY 100 AAPL @ $150.00                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Portfolio Summary Cards

| Card | Description |
|------|-------------|
| **Available Cash** | Money available for buying stocks |
| **Invested Value** | Total value of your stock holdings |
| **Total Return** | Profit/loss from initial investment |
| **Estimated Tax** | Tax liability on realized gains (37%) |

### Portfolio Chart

- Shows portfolio value over time
- Select time range: 1W, 1M, 3M, 6M, 1Y
- Green line = portfolio value trending up
- Red line = portfolio value trending down

---

## Portfolio Management

### Viewing Your Portfolio

The Holdings Table shows all your current positions:

| Column | Description |
|--------|-------------|
| Symbol | Stock ticker (e.g., AAPL) |
| Name | Company name |
| Sector | Industry sector |
| Quantity | Number of shares owned |
| Avg Cost | Average purchase price per share |
| Current Price | Latest market price |
| Value | Total position value (Qty × Price) |
| Gain/Loss $ | Dollar profit/loss |
| Gain/Loss % | Percentage profit/loss |

**Color Coding:**
- 🟢 Green = Profit (current price > avg cost)
- 🔴 Red = Loss (current price < avg cost)

### Allocation Chart

The pie chart shows how your portfolio is allocated:

- **By Stock:** Each slice = one stock position
- **By Sector:** Slices grouped by industry sector
- **Cash** is shown as a separate slice

Toggle between views using the dropdown above the chart.

### Resetting Your Portfolio

To start fresh:

1. Click the **Reset Portfolio** button
2. Confirm the action
3. Your portfolio returns to $100,000 cash with no holdings

**Warning:** This clears all holdings and trade history!

---

## Trading

### Manual Trading

Currently, trades are executed through the API or auto-trading.

To place a manual trade via API:

```bash
# Buy 10 shares of AAPL
curl -X POST "http://server:5000/api/trades" \
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

### Auto-Trading

Enable automatic trading based on your selected strategy:

1. Toggle **Auto-Trade** to ON in the header
2. The system will automatically:
   - Analyze your portfolio allocation
   - Execute trades to match target ratios
   - Follow strategy rules

**Auto-Trade Behavior:**
- Buys when you're under-invested
- Sells when you're over-invested
- Selects stocks from strategy's pool
- Respects position size limits

### Trade History

View past trades in the Trade History section:

- Filter by: **All**, **Buy**, or **Sell**
- Each trade shows:
  - Date/time
  - Type (BUY/SELL badge)
  - Symbol and company name
  - Quantity and price
  - Total amount
  - Fees paid
  - Strategy used

---

## Strategies

### Available Strategies

| Strategy | Risk Level | Expected Return | Description |
|----------|------------|-----------------|-------------|
| **Conservative** | 1/5 ⭐ | 2-6% | Low-risk, stable dividend stocks |
| **Growth** | 4/5 ⭐⭐⭐⭐ | 10-25% | High-growth tech stocks |
| **Value** | 2/5 ⭐⭐ | 6-12% | Undervalued blue-chip stocks |
| **Balanced** | 3/5 ⭐⭐⭐ | 5-12% | Mix of growth and stability |
| **Aggressive** | 5/5 ⭐⭐⭐⭐⭐ | -20% to +50% | High-risk, high-reward |

### Selecting a Strategy

1. Click on a strategy card in the Strategy Selector
2. The selected strategy is highlighted
3. Your portfolio settings update automatically

### Customizing a Strategy

Click **Customize** on any strategy card to adjust:

| Setting | Description | Range |
|---------|-------------|-------|
| Confidence Level | How aggressively to follow signals | 10-100% |
| Trade Frequency | How often to trade | Low / Medium / High |
| Max Position Size | Maximum % of portfolio per stock | 5-50% |
| Stop Loss | Sell if stock drops by this % | 5-30% |
| Take Profit | Sell if stock gains this % | 10-100% |
| Auto Rebalance | Automatically rebalance portfolio | On/Off |
| Reinvest Dividends | Automatically reinvest dividends | On/Off |

Click **Save** to apply your customizations.

---

## Market Data

### Price Updates

- Prices update automatically every few seconds
- Data source: Yahoo Finance (real market data)
- Fallback: Simulated prices if Yahoo unavailable

### Price Indicators

| Indicator | Meaning |
|-----------|---------|
| 🟢 +$X.XX (+X.XX%) | Price increased |
| 🔴 -$X.XX (-X.XX%) | Price decreased |
| ⚪ $X.XX (0.00%) | Price unchanged |

### Market Hours

- **Open:** 9:30 AM - 4:00 PM Eastern (Mon-Fri)
- **Closed:** Weekends and US market holidays

During closed hours, last closing prices are displayed.

---

## Understanding Returns

### Unrealized vs Realized Gains

| Type | Description |
|------|-------------|
| **Unrealized** | Profit/loss on stocks you still own |
| **Realized** | Profit/loss from stocks you've sold |

Only **realized gains** are taxable.

### Tax Calculation

The platform calculates estimated tax at **37%** (short-term capital gains rate):

```
Estimated Tax = Realized Gains × 0.37
```

Example:
- Realized Gains: $5,000
- Estimated Tax: $5,000 × 0.37 = $1,850

### Return Calculation

```
Total Return = (Current Portfolio Value - Initial Value) / Initial Value × 100%

Where:
Current Portfolio Value = Cash + Sum(Holdings Value)
Initial Value = $100,000 (default)
```

---

## FAQ

### Q: Why isn't my portfolio updating?

**A:** Check that:
1. Your browser has internet connectivity
2. The server is running
3. Auto-refresh is enabled (default: yes)
4. Try refreshing the page

### Q: Why can't I buy more stock?

**A:** Possible reasons:
- Insufficient cash balance
- Position would exceed max size limit
- Trade would use >95% of available cash

### Q: How do I add money to my portfolio?

**A:** Currently, the initial value is fixed at $100,000. Use **Reset Portfolio** to start fresh.

### Q: Is this real money?

**A:** No! This is a **simulation** platform for learning and testing strategies. No real money is involved.

### Q: Where does the market data come from?

**A:** Real market data is fetched from Yahoo Finance. When unavailable, simulated prices are used (marked as "simulated").

### Q: How are average costs calculated?

**A:** Using weighted average:

```
New Avg Cost = (Old Cost × Old Qty + New Price × New Qty) / Total Qty
```

Example:
- Own 100 shares at $150 avg cost
- Buy 50 more at $180
- New avg = (150×100 + 180×50) / 150 = $160

### Q: What happens when I sell?

**A:** When you sell:
1. Shares are removed from holdings
2. Cash increases by sale amount (minus fees)
3. Realized gain/loss is calculated and recorded
4. Tax liability is updated

### Q: Can I export my data?

**A:** Yes, via the API:
- Portfolio: `GET /api/portfolio/settings`
- Holdings: `GET /api/holdings`
- Trades: `GET /api/trades`

---

## Tips for Success

1. **Start with Balanced** - Good for learning the platform
2. **Watch the Allocation** - Don't put too much in one stock
3. **Monitor Your Ratios** - Stay close to target investment ratio
4. **Review Trade History** - Learn from past decisions
5. **Try Different Strategies** - See how each performs over time

---

## Support

For technical issues:
1. Check this guide
2. Review the API documentation
3. Contact your system administrator
4. Check application logs

Happy Investing! 📈
