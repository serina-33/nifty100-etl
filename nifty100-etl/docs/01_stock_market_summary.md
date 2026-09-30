# Stock Market Fundamentals — Summary & Company Analysis

*Prepared for the Bluestock Fintech prerequisite learning program. This is a domain-knowledge primer, not investment or trading advice.*

## 1. What is a stock market?

A stock market is an organised venue where shares (small ownership units) of publicly listed companies are bought and sold. It lets companies raise capital from the public and lets investors participate in a company's growth.

## 2. NSE & BSE

- **NSE (National Stock Exchange)** — India's largest exchange by trading volume, home of the Nifty indices.
- **BSE (Bombay Stock Exchange)** — Asia's oldest exchange, home of the Sensex.
Most large Indian companies are dual-listed on both.

## 3. Nifty & Sensex

- **Nifty 50** — NSE's benchmark index of the top 50 companies by free-float market cap.
- **Sensex** — BSE's benchmark index of its top 30 companies.
Both serve as barometers of overall market health.

## 4. IPO & SME IPO

- **IPO (Initial Public Offering)** — the first time a company sells shares to the public to get listed.
- **SME IPO** — a smaller-scale IPO process for small and medium enterprises, with lighter listing requirements than a mainboard IPO.

## 5. Market capitalization

`Market cap = share price × total outstanding shares`. Companies are commonly bucketed as large-cap, mid-cap, or small-cap based on this figure.

## 6. PE ratio (Price-to-Earnings)

`PE = share price / earnings per share (EPS)`. It shows how much investors are paying for each rupee of earnings. A high PE can mean high growth expectations — or an overvalued stock.

## 7. PB ratio (Price-to-Book)

`PB = share price / book value per share`. Book value is what would be left for shareholders if the company liquidated all assets and paid off all liabilities today. Useful for asset-heavy businesses like banks.

## 8. EPS (Earnings Per Share)

`EPS = net profit / total outstanding shares`. It standardizes profit on a per-share basis so companies of different sizes can be compared.

## 9. Dividend

A portion of profit a company distributes to shareholders, usually as cash per share. Not all companies pay dividends — growth companies often reinvest profits instead.

## 10. Bonus & stock split

- **Bonus shares** — free additional shares issued to existing shareholders (e.g. 1:1 bonus doubles your share count) funded from reserves; doesn't dilute your % ownership.
- **Stock split** — dividing each existing share into multiple shares (e.g. 1:5 split), reducing price per share while keeping total value constant. Both increase liquidity and affordability without changing fundamentals.

## 11. Trading volume

The number of shares traded in a period. High volume alongside a price move suggests strong conviction behind that move; low volume moves are viewed more skeptically.

## 12–14. The three core financial statements

| Statement | What it shows | Key line items |
|---|---|---|
| **Balance Sheet** | Financial position at a point in time | Assets, Liabilities, Equity (Assets = Liabilities + Equity) |
| **Profit & Loss (Income Statement)** | Performance over a period | Sales, Operating Profit, Net Profit, EPS |
| **Cash Flow Statement** | Actual cash movement over a period | Cash from Operations, Investing, Financing |

A company can show an accounting profit on the P&L while still running out of cash — which is why the cash flow statement matters just as much.

## 15. Basic financial ratios

| Ratio | Formula | Tells you |
|---|---|---|
| ROE | Net profit / Equity | Return generated on shareholders' money |
| ROCE | EBIT / Capital employed | Return on all capital, debt + equity |
| Debt-to-Equity | Total debt / Equity | Leverage / financial risk |
| OPM% | Operating profit / Sales | Core operating efficiency |
| Dividend payout % | Dividends paid / Net profit | How much profit is returned vs reinvested |

---

## Company financial statement analysis (worked example)

Rather than analyse a single stock's raw filings, the worked example below applies the exact same ratio framework used above to a *representative* company from the synthetic `nifty100.db` built for this internship's Sprint 1 (see the ETL project alongside this document). This keeps the write-up self-contained and reproducible from the database rather than depending on any single real ticker's numbers, which change over time.

**How to reproduce this analysis for a real company**: pick any Nifty 100 constituent, pull its last 5 years of P&L, balance sheet, and cash flow statements (from the company's investor relations page, [screener.in](https://www.screener.in), or NSE/BSE filings), and run the same three checks:

1. **Trend check** — is sales/net profit growing YoY, or flat/declining?
2. **Balance check** — does `Total Assets ≈ Total Liabilities + Equity`? (This is exactly DQ-04 in the ETL project.)
3. **Quality check** — is operating cash flow consistently positive and roughly tracking net profit? A company with rising "paper profit" but negative operating cash flow is a red flag.

```sql
-- Example: run this against nifty100.db to reproduce steps 1-3 for company_id = 1
SELECT year, sales, net_profit, opm_pct FROM profitandloss WHERE company_id = 1 ORDER BY year;
SELECT year, total_assets, total_liabilities, equity_capital FROM balancesheet WHERE company_id = 1 ORDER BY year;
SELECT year, cash_from_operations, net_cash_flow FROM cashflow WHERE company_id = 1 ORDER BY year;
```

## Recommended resources

- CA Rachana Ranade — *Basics of Stock Market* (YouTube playlist)
- Zerodha Varsity — https://zerodha.com/varsity/
- SEBI Investor Education — https://investor.sebi.gov.in/
