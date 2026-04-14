# IBKR Flex Query Setup for LAFMM

Configure Interactive Brokers' Flex Query to export trade data
for the sync-trades skill.

## Create the query

Account Management → Reports → Flex Queries → Create Activity Flex Query

**Query Name:** `LAFMM`

## Sections

Select these **three** sections:

1. **Trades**: trade fills
2. **Cash Transactions**: deposits, withdrawals, dividends
3. **Net Asset Value (NAV) in Base**: total account value for `Capital:`

Leave everything else unchecked.

Do not use Statement of Funds. It tracks cash movements only,
not total account value.

## Trades configuration

### Options

Select only: **Execution**

Leave unchecked: Symbol Summary, Asset Class, Order, Closed Lots, Wash Sales.

### Fields

Select these 13 fields:

- Trade Date
- Date/Time
- Symbol
- Buy/Sell
- Quantity
- TradePrice
- IB Commission
- Order Type
- Realized P/L
- Open/Close Indicator
- Asset Class
- Currency
- Net Cash

## Cash Transactions configuration

### Types

Select these:

- **Deposits & Withdrawals**
- **Dividends**
- **Payment in Lieu of Dividends**
- **Withholding Tax**
- **Broker Interest Received**
- **Broker Interest Paid**
- **Other Fees**

Leave everything else unchecked.

### Detail level

Select: **Detail**

### Fields

Select these 5 fields:

- Date/Time
- Type
- Amount
- Currency
- Symbol

## Net Asset Value (NAV) in Base configuration

### Options

Check: **Include Starting and Ending Balances**

Leave unchecked: Exclude prior report date, Exclude long and short breakout.

### Fields

Select these 2 fields:

- Report Date
- Total

One row per day. `Total` is the daily ending account value
(cash + all positions), written as `Capital:` in journal files.

## Delivery Configuration

```
Accounts:                        (your account ID)
Models:                          (leave empty)
Format:                          CSV
Include header and trailer:      No
Include column headers:          Yes
Display single column header:    (leave default)
Include section code:            Yes
Period:                          Last 90 Calendar Days
```

90-day rolling window. The import skips dates that already have
journal entries, so every run only writes new data. Run anytime.
Catches up automatically after gaps.

## General Configuration

```
Date Format:                     yyyyMMdd
Time Format:                     HHmmss
Date/Time Separator:             ; (semi-colon)
Profit and Loss:                 Default
Include Canceled Trades:         No
Include Currency Rates:          No
Include Audit Trail Fields:      No
Display Account Alias:           No
Breakout by Day:                 No
```

## Usage

### Manual

1. Run the LAFMM query in IBKR, download CSV
2. Tell the agent: "Sync my trades from /path/to/LAFMM.csv"
3. Existing dates are skipped. Safe to run anytime.

### Auto

Configure API credentials in `account.toml`:

```toml
[broker.api]
type = "ibkr-flex"
token = "your-flex-web-service-token"
query_id = "your-query-id"
```

Tell the agent: "Sync my trades." The skill fetches via IBKR's
Flex Web Service API, parses, and writes journal entries.

The 90-day rolling window means the API always returns recent
data. Dedup skips existing entries. No date management needed.

## Field mapping

| IBKR field | Journal column |
|-----------|---------------|
| Trade Date | date (file name) |
| Date/Time | time |
| Symbol | symbol |
| Buy/Sell | side |
| Quantity | qty |
| TradePrice | price |
| IB Commission | fees |
| Order Type | order |
| Realized P/L | pnl |
| Open/Close Indicator | open_close |

Cash Transactions become `Deposit:`, `Withdrawal:`, `Dividend:`,
`Tax:`, `Interest:`, `Fee:` lines. NAV in Base becomes `Capital:`.

## IBKR-specific behavior

- **Forex rows**: `AssetClass=CASH` (e.g., USD.HKD). Filtered out.
- **Extended hours**: DateTime and TradeDate may differ. The journal
  uses TradeDate for the filename.
- **Partial fills**: IBKR splits one order into multiple rows with
  different commission allocations. The skill merges where appropriate.
- **Signed quantities**: IBKR uses negative for sells. Absolute value taken.
- **Signed commissions**: IBKR reports as negative. Absolute value taken.
- **Capital**: from NAV in Base `Total` field. Cash + all positions.
- **Cash flow currency**: uses `CurrencyPrimary` from the export.
  May differ from base currency (e.g., HKD deposit into USD account).
