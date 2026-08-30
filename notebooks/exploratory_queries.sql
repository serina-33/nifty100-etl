-- =====================================================================
-- exploratory_queries.sql — Day 07 deliverable
-- 10 exploratory queries to sanity-check nifty100.db after Sprint 1
-- Run: sqlite3 nifty100.db < notebooks/exploratory_queries.sql
-- =====================================================================

-- 1. Row counts across all tables (quick health check)
SELECT 'companies' t, COUNT(*) n FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- 2. Companies per sector
SELECT sector, COUNT(*) AS n_companies
FROM companies
GROUP BY sector
ORDER BY n_companies DESC;

-- 3. Top 10 companies by latest-year sales
SELECT c.company_name, p.year, p.sales
FROM profitandloss p
JOIN companies c ON c.company_id = p.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
ORDER BY p.sales DESC
LIMIT 10;

-- 4. Companies with fewer than 5 years of P&L history (Day 06 manual review)
SELECT c.company_name, COUNT(DISTINCT p.year) AS years_covered
FROM companies c
JOIN profitandloss p ON p.company_id = c.company_id
GROUP BY c.company_id
HAVING years_covered < 5
ORDER BY years_covered ASC;

-- 5. Average OPM% by sector (latest year)
SELECT c.sector, ROUND(AVG(p.opm_pct), 2) AS avg_opm_pct
FROM profitandloss p
JOIN companies c ON c.company_id = p.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss)
GROUP BY c.sector
ORDER BY avg_opm_pct DESC;

-- 6. Balance sheets that fail the <1% balance check (feeds DQ-04)
SELECT c.company_name, b.year, b.total_assets,
       (b.total_liabilities + b.equity_capital) AS liab_plus_equity,
       ROUND(ABS(b.total_assets - (b.total_liabilities + b.equity_capital)) / b.total_assets * 100, 2) AS diff_pct
FROM balancesheet b
JOIN companies c ON c.company_id = b.company_id
WHERE ABS(b.total_assets - (b.total_liabilities + b.equity_capital)) / b.total_assets > 0.01
ORDER BY diff_pct DESC
LIMIT 15;

-- 7. Stock price trend (monthly close) for a single company (parameter: company_id)
SELECT date, close_price, volume
FROM stock_prices
WHERE company_id = 1
ORDER BY date;

-- 8. Top 10 companies by average ROE% over last 5 years
SELECT c.company_name, ROUND(AVG(r.roe_pct), 2) AS avg_roe_pct
FROM financial_ratios r
JOIN companies c ON c.company_id = r.company_id
GROUP BY c.company_id
ORDER BY avg_roe_pct DESC
LIMIT 10;

-- 9. Peer-group network size per company
SELECT c.company_name, COUNT(pg.peer_company_id) AS n_peers
FROM companies c
LEFT JOIN peer_groups pg ON pg.company_id = c.company_id
GROUP BY c.company_id
ORDER BY n_peers DESC;

-- 10. Analyst rating distribution vs sector
SELECT c.sector, a.analyst_rating, COUNT(*) AS n
FROM analysis a
JOIN companies c ON c.company_id = a.company_id
GROUP BY c.sector, a.analyst_rating
ORDER BY c.sector, n DESC;
