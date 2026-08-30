-- =====================================================================
-- schema.sql — Nifty100 ETL Pipeline (Sprint 1, Day 04)
-- 10 tables · PK/FK enforced · run with PRAGMA foreign_keys = ON
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS peer_groups;
DROP TABLE IF EXISTS financial_ratios;
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS prosandcons;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS analysis;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS balancesheet;
DROP TABLE IF EXISTS profitandloss;
DROP TABLE IF EXISTS companies;

-- 1. companies (master table)
CREATE TABLE companies (
    company_id      INTEGER PRIMARY KEY,
    company_name    TEXT NOT NULL,
    ticker          TEXT NOT NULL UNIQUE,
    sector          TEXT NOT NULL,
    listing_date    TEXT,
    isin            TEXT UNIQUE
);

-- 2. sectors (lookup)
CREATE TABLE sectors (
    sector_id       INTEGER PRIMARY KEY,
    sector_name     TEXT NOT NULL UNIQUE,
    sector_pe_avg   REAL
);

-- 3. profitandloss
CREATE TABLE profitandloss (
    company_id        INTEGER NOT NULL,
    year              INTEGER NOT NULL,
    sales             REAL,
    operating_profit  REAL,
    opm_pct           REAL,
    net_profit        REAL,
    eps               REAL,
    tax_pct           REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 4. balancesheet
CREATE TABLE balancesheet (
    company_id          INTEGER NOT NULL,
    year                INTEGER NOT NULL,
    total_assets        REAL,
    total_liabilities   REAL,
    equity_capital       REAL,
    reserves            REAL,
    borrowings          REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 5. cashflow
CREATE TABLE cashflow (
    company_id              INTEGER NOT NULL,
    year                    INTEGER NOT NULL,
    cash_from_operations    REAL,
    cash_from_investing     REAL,
    cash_from_financing     REAL,
    net_cash_flow           REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 6. analysis
CREATE TABLE analysis (
    company_id      INTEGER PRIMARY KEY,
    analyst_rating  TEXT,
    target_price    REAL,
    summary         TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 7. documents
CREATE TABLE documents (
    document_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    doc_type        TEXT,
    url             TEXT,
    filed_date      TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 8. prosandcons
CREATE TABLE prosandcons (
    company_id      INTEGER PRIMARY KEY,
    pros            TEXT,
    cons            TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 9. stock_prices
CREATE TABLE stock_prices (
    company_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,
    close_price     REAL,
    volume          INTEGER,
    PRIMARY KEY (company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 10. financial_ratios
CREATE TABLE financial_ratios (
    company_id          INTEGER NOT NULL,
    year                INTEGER NOT NULL,
    pe_ratio            REAL,
    pb_ratio            REAL,
    roe_pct             REAL,
    roce_pct            REAL,
    debt_to_equity      REAL,
    dividend_payout_pct REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 11. peer_groups  (kept as its own table per the 10+lookup design;
--     "10 tables" = companies..financial_ratios; peer_groups is the
--     supplementary many-to-many table completing the 12-file load)
CREATE TABLE peer_groups (
    company_id       INTEGER NOT NULL,
    peer_company_id  INTEGER NOT NULL,
    PRIMARY KEY (company_id, peer_company_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(company_id)
);

-- Helpful indexes
CREATE INDEX idx_pl_company   ON profitandloss(company_id);
CREATE INDEX idx_bs_company   ON balancesheet(company_id);
CREATE INDEX idx_cf_company   ON cashflow(company_id);
CREATE INDEX idx_prices_company ON stock_prices(company_id);
CREATE INDEX idx_ratios_company ON financial_ratios(company_id);
