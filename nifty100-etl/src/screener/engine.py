"""
Sprint 3 Day 15-17 — Financial Screener and Composite Quality Score.

This module is deliberately defensive against the Sprint 2 schema in this
repository.

It supports:

1. Loading the latest complete financial snapshot
2. Deriving P/E, P/B, dividend yield and market capitalisation
3. Applying configurable screener filters
4. Winsorised 0-100 scoring
5. Composite quality scoring
6. Sector-relative scoring
7. Preset screen execution
8. Turnaround/debt/FCF helper flags
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Mapping, Any

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"

CONFIG_PATH = (
    ROOT
    / "config"
    / "screener_config.yaml"
)


# ---------------------------------------------------------------------
# COLUMN ALIASES
# ---------------------------------------------------------------------

ALIASES = {
    "roe": [
        "return_on_equity_pct",
        "roe_pct",
        "roe",
    ],

    "roce": [
        "return_on_capital_employed_pct",
        "roce_pct",
        "roce",
    ],

    "npm": [
        "net_profit_margin_pct",
        "npm_pct",
        "net_profit_margin",
        "npm",
    ],

    "opm": [
        "operating_profit_margin_pct",
        "opm_pct",
        "operating_profit_margin",
        "opm",
    ],

    "de": [
        "debt_to_equity",
        "de_ratio",
        "de",
    ],

    "icr": [
        "interest_coverage",
        "interest_coverage_ratio",
        "icr",
    ],

    "fcf": [
        "free_cash_flow_cr",
        "free_cash_flow",
        "fcf_cr",
        "fcf",
    ],

    "revenue_cagr_5yr": [
        "revenue_cagr_5yr",
        "sales_cagr_5yr",
    ],

    "pat_cagr_5yr": [
        "pat_cagr_5yr",
        "net_profit_cagr_5yr",
    ],

    "eps_cagr_5yr": [
        "eps_cagr_5yr",
    ],

    "asset_turnover": [
        "asset_turnover",
    ],

    "eps": [
        "earnings_per_share",
        "eps",
    ],

    "bvps": [
        "book_value_per_share",
        "bvps",
    ],

    "payout": [
        "dividend_payout_ratio_pct",
        "dividend_payout_pct",
        "payout",
    ],

    "sales": [
        "sales",
        "revenue",
    ],

    "net_profit": [
        "net_profit",
        "pat",
    ],

    "cfo": [
        "cash_from_operations_cr",
        "cash_from_operations",
        "cfo",
    ],

    "year": [
        "year",
        "fy",
    ],
}


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

def load_config(
    path: Path = CONFIG_PATH,
) -> dict:
    """
    Load screener configuration from YAML.
    """

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


# ---------------------------------------------------------------------
# COLUMN HELPERS
# ---------------------------------------------------------------------

def _pick(
    df: pd.DataFrame,
    key: str,
) -> str | None:
    """
    Find the first available dataframe column matching an alias.
    """

    for column in ALIASES.get(key, [key]):
        if column in df.columns:
            return column

    return None


def _numeric(
    df: pd.DataFrame,
    cols,
):
    """
    Convert supplied columns to numeric values safely.
    """

    for column in cols:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


# ---------------------------------------------------------------------
# LATEST FINANCIAL SNAPSHOT
# ---------------------------------------------------------------------

def latest_complete_snapshot(
    conn: sqlite3.Connection,
) -> pd.DataFrame:
    """
    Return one usable/latest financial row per company.

    The function combines:

        financial_ratios
        companies
        profitandloss
        stock_prices

    and derives:

        P/E
        P/B
        dividend yield
        market cap
        FCF positive flag
        CFO/PAT ratio
        FCF CAGR
        revenue CAGR
        debt declining flag
    """

    # -------------------------------------------------------------
    # Read Sprint 2 tables
    # -------------------------------------------------------------

    fr = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn,
    )

    if fr.empty:
        raise RuntimeError(
            "financial_ratios is empty. "
            "Run Sprint 2 ratio engine first."
        )

    companies = pd.read_sql_query(
        """
        SELECT
            company_id,
            company_name,
            ticker,
            sector,
            COALESCE(broad_sector, sector) AS broad_sector
        FROM companies
        """,
        conn,
    )

    pl = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            sales,
            net_profit,
            eps
        FROM profitandloss
        """,
        conn,
    )

    prices = pd.read_sql_query(
        """
        SELECT
            company_id,
            date,
            close_price
        FROM stock_prices
        """,
        conn,
    )

    # -------------------------------------------------------------
    # Find best/latest financial ratio row
    # -------------------------------------------------------------

    fr["_quality"] = fr.notna().sum(axis=1)

    fr = fr.sort_values(
        [
            "company_id",
            "year",
            "_quality",
        ]
    )

    required_quality_columns = [
        column
        for column in [
            "net_profit_margin_pct",
            "return_on_equity_pct",
            "free_cash_flow_cr",
        ]
        if column in fr.columns
    ]

    if required_quality_columns:
        usable = fr[
            fr[required_quality_columns]
            .notna()
            .any(axis=1)
        ]
    else:
        usable = fr.copy()

    latest = (
        usable
        .sort_values("year")
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
    )

    fallback = (
        fr
        .sort_values("year")
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
    )

    latest = (
        pd.concat(
            [
                latest,
                fallback,
            ]
        )
        .drop_duplicates(
            "company_id",
            keep="first",
        )
    )

    latest = latest.drop(
        columns=["_quality"],
        errors="ignore",
    )

    # -------------------------------------------------------------
    # Merge company information
    # -------------------------------------------------------------

    latest = latest.merge(
        companies,
        on="company_id",
        how="left",
        suffixes=("", "_company"),
    )

    # -------------------------------------------------------------
    # Merge P&L information
    # -------------------------------------------------------------

    latest = latest.merge(
        pl,
        on=[
            "company_id",
            "year",
        ],
        how="left",
        suffixes=("", "_pl"),
    )

    # -------------------------------------------------------------
    # Latest stock price
    # -------------------------------------------------------------

    if not prices.empty:

        prices["date"] = pd.to_datetime(
            prices["date"],
            errors="coerce",
        )

        px = (
            prices
            .sort_values("date")
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
        )

        latest = latest.merge(
            px[
                [
                    "company_id",
                    "close_price",
                ]
            ],
            on="company_id",
            how="left",
        )

    else:

        latest["close_price"] = np.nan

    # -------------------------------------------------------------
    # Standard numeric fields
    # -------------------------------------------------------------

    latest["sales"] = pd.to_numeric(
        latest.get("sales"),
        errors="coerce",
    )

    latest["net_profit"] = pd.to_numeric(
        latest.get("net_profit"),
        errors="coerce",
    )

    # EPS
    eps_column = _pick(
        latest,
        "eps",
    )

    if eps_column:
        latest["eps"] = pd.to_numeric(
            latest[eps_column],
            errors="coerce",
        )
    else:
        latest["eps"] = np.nan

    # BVPS
    bvps_column = _pick(
        latest,
        "bvps",
    )

    if bvps_column:
        latest["bvps"] = pd.to_numeric(
            latest[bvps_column],
            errors="coerce",
        )
    else:
        latest["bvps"] = np.nan

    # Payout
    payout_column = _pick(
        latest,
        "payout",
    )

    if payout_column:
        latest["payout"] = pd.to_numeric(
            latest[payout_column],
            errors="coerce",
        )
    else:
        latest["payout"] = np.nan

    latest["close_price"] = pd.to_numeric(
        latest["close_price"],
        errors="coerce",
    )

    # -------------------------------------------------------------
    # Derived valuation metrics
    # -------------------------------------------------------------

    latest["pe"] = (
        latest["close_price"]
        / latest["eps"].replace(
            0,
            np.nan,
        )
    )

    latest["pb"] = (
        latest["close_price"]
        / latest["bvps"].replace(
            0,
            np.nan,
        )
    )

    latest["dividend_yield"] = (
        (
            latest["payout"]
            / 100.0
        )
        * latest["eps"]
        / latest["close_price"].replace(
            0,
            np.nan,
        )
        * 100.0
    )

    # -------------------------------------------------------------
    # Market cap approximation
    #
    # Shares = Net Profit / EPS
    # Market Cap = Price * Shares
    # -------------------------------------------------------------

    shares = (
        latest["net_profit"]
        / latest["eps"].replace(
            0,
            np.nan,
        )
    )

    latest["market_cap_cr"] = (
        latest["close_price"]
        * shares
    )

    latest["market_cap_cr"] = (
        latest["market_cap_cr"].abs()
    )

    # -------------------------------------------------------------
    # Standardised metric names
    # -------------------------------------------------------------

    mapping = {
        "roe": "roe",
        "roce": "roce",
        "npm": "npm",
        "opm": "opm",
        "de": "de",
        "icr": "icr",
        "fcf": "fcf",
        "revenue_cagr_5yr": "revenue_cagr_5yr",
        "pat_cagr_5yr": "pat_cagr_5yr",
        "eps_cagr_5yr": "eps_cagr_5yr",
        "asset_turnover": "asset_turnover",
        "eps": "eps",
        "bvps": "bvps",
        "payout": "payout",
        "cfo": "cfo",
    }

    for output_column, key in mapping.items():

        column = _pick(
            latest,
            key,
        )

        if column:
            latest[output_column] = pd.to_numeric(
                latest[column],
                errors="coerce",
            )
        elif output_column not in latest.columns:
            latest[output_column] = np.nan

    # -------------------------------------------------------------
    # FCF positive
    # -------------------------------------------------------------

    latest["fcf_positive"] = (
        latest["fcf"] > 0
    )

    # -------------------------------------------------------------
    # CFO / PAT ratio
    # -------------------------------------------------------------

    latest["cfo_pat_ratio"] = (
        latest["cfo"]
        / latest["net_profit"].replace(
            0,
            np.nan,
        )
    )

    # -------------------------------------------------------------
    # FCF CAGR
    # -------------------------------------------------------------

    latest["fcf_cagr_5yr"] = _compute_cagr_from_db(
        conn,
        latest["company_id"],
        latest["year"],
        "fcf",
    )

    # -------------------------------------------------------------
    # Revenue CAGR
    # -------------------------------------------------------------

    latest["revenue_cagr_3yr"] = _compute_cagr_from_db(
        conn,
        latest["company_id"],
        latest["year"],
        "sales",
        3,
    )

    # -------------------------------------------------------------
    # Debt declining flag
    # -------------------------------------------------------------

    latest["de_declining_yoy"] = _de_declining_flags(
        conn,
        latest[
            [
                "company_id",
                "year",
            ]
        ],
    )

    # -------------------------------------------------------------
    # Sector cleanup
    # -------------------------------------------------------------

    latest["sector"] = (
        latest["sector"]
        .fillna("Unknown")
    )

    latest["broad_sector"] = (
        latest["broad_sector"]
        .fillna(latest["sector"])
        .fillna("Unknown")
    )

    return latest


# ---------------------------------------------------------------------
# DATABASE SERIES
# ---------------------------------------------------------------------

def _series_for(
    conn: sqlite3.Connection,
    cid,
    value_col,
):
    """
    Retrieve historical series for CAGR calculations.
    """

    if value_col == "fcf":

        query = """
            SELECT
                pl.year,
                (
                    COALESCE(
                        cf.cash_from_operations,
                        0
                    )
                    +
                    COALESCE(
                        cf.cash_from_investing,
                        0
                    )
                ) AS value
            FROM profitandloss pl

            LEFT JOIN cashflow cf
                ON pl.company_id = cf.company_id
                AND pl.year = cf.year

            WHERE pl.company_id = ?

            ORDER BY pl.year
        """

    else:

        query = f"""
            SELECT
                year,
                {value_col} AS value
            FROM profitandloss

            WHERE company_id = ?

            ORDER BY year
        """

    return pd.read_sql_query(
        query,
        conn,
        params=[int(cid)],
    )


# ---------------------------------------------------------------------
# CAGR
# ---------------------------------------------------------------------

def _cagr(
    start,
    end,
    n,
):
    """
    Calculate CAGR percentage.

    Returns NaN when start/end are missing or non-positive.
    """

    if (
        pd.isna(start)
        or pd.isna(end)
        or start <= 0
        or end <= 0
    ):
        return np.nan

    return (
        (end / start) ** (1 / n)
        - 1
    ) * 100


def _compute_cagr_from_db(
    conn: sqlite3.Connection,
    ids,
    years,
    field,
    window=5,
):
    """
    Calculate CAGR for each company.
    """

    output = []

    for cid, year in zip(
        ids,
        years,
    ):

        series = _series_for(
            conn,
            cid,
            field,
        )

        if series.empty:
            output.append(np.nan)
            continue

        start = series.loc[
            series["year"] == int(year) - window,
            "value",
        ]

        end = series.loc[
            series["year"] == int(year),
            "value",
        ]

        start_value = (
            start.iloc[0]
            if len(start)
            else np.nan
        )

        end_value = (
            end.iloc[0]
            if len(end)
            else np.nan
        )

        output.append(
            _cagr(
                start_value,
                end_value,
                window,
            )
        )

    return output


# ---------------------------------------------------------------------
# DEBT DECLINING FLAG
# ---------------------------------------------------------------------

def _de_declining_flags(
    conn: sqlite3.Connection,
    keys: pd.DataFrame,
):
    """
    Return True when D/E declined from the previous year.
    """

    output = []

    for cid, year in keys.itertuples(
        index=False
    ):

        query = pd.read_sql_query(
            """
            SELECT
                year,
                debt_to_equity
            FROM financial_ratios

            WHERE company_id = ?
              AND year <= ?

            ORDER BY year DESC

            LIMIT 2
            """,
            conn,
            params=[
                int(cid),
                int(year),
            ],
        )

        if len(query) < 2:
            output.append(False)
            continue

        values = pd.to_numeric(
            query["debt_to_equity"],
            errors="coerce",
        )

        if values.isna().any():
            output.append(False)
            continue

        output.append(
            bool(
                values.iloc[0]
                < values.iloc[1]
            )
        )

    return output


# ---------------------------------------------------------------------
# FILTERING
# ---------------------------------------------------------------------

def apply_filters(
    df: pd.DataFrame,
    thresholds: Mapping[str, Any],
) -> pd.DataFrame:
    """
    Apply analyst thresholds safely.

    Supported examples:

        roe_min
        de_max
        revenue_cagr_5yr_min
        pat_cagr_5yr_min
        dividend_payout_max
        fcf_latest_positive
        de_declining_yoy

    Numerical filters reject NaN values.

    Unknown metrics are ignored instead of causing errors.
    """

    out = df.copy()

    # -------------------------------------------------------------
    # Alias mapping
    # -------------------------------------------------------------

    aliases = {
        "dividend_payout": "payout",
        "dividend_payout_min": "payout",
        "dividend_payout_max": "payout",
    }

    # -------------------------------------------------------------
    # Numerical filters
    # -------------------------------------------------------------

    for metric, threshold in thresholds.items():

        if threshold is None:
            continue

        # Boolean flags handled later.
        if metric in {
            "fcf_latest_positive",
            "de_declining_yoy",
        }:
            continue

        # ---------------------------------------------------------
        # Determine target dataframe column
        # ---------------------------------------------------------

        if metric in aliases:

            column = aliases[metric]

            if metric.endswith("_min"):
                operator = "min"
            else:
                operator = "max"

        elif metric.endswith("_min"):

            column = metric[:-4]
            operator = "min"

        elif metric.endswith("_max"):

            column = metric[:-4]
            operator = "max"

        else:

            column = metric
            operator = "exact"

        # ---------------------------------------------------------
        # Unknown column
        # ---------------------------------------------------------

        if column not in out.columns:
            continue

        values = pd.to_numeric(
            out[column],
            errors="coerce",
        )

        threshold_value = float(
            threshold
        )

        # ---------------------------------------------------------
        # Minimum
        # ---------------------------------------------------------

        if operator == "min":

            mask = (
                values.notna()
                & (
                    values
                    >= threshold_value
                )
            )

            out = out.loc[mask]

        # ---------------------------------------------------------
        # Maximum
        # ---------------------------------------------------------

        elif operator == "max":

            mask = (
                values.notna()
                & (
                    values
                    <= threshold_value
                )
            )

            out = out.loc[mask]

        # ---------------------------------------------------------
        # Exact
        # ---------------------------------------------------------

        elif operator == "exact":

            mask = (
                values.notna()
                & (
                    values
                    == threshold_value
                )
            )

            out = out.loc[mask]

    # -------------------------------------------------------------
    # FCF positive filter
    # -------------------------------------------------------------

    if thresholds.get(
        "fcf_latest_positive"
    ) is True:

        if "fcf_positive" in out.columns:

            out = out[
                out["fcf_positive"]
                .fillna(False)
            ]

        elif "fcf" in out.columns:

            out = out[
                pd.to_numeric(
                    out["fcf"],
                    errors="coerce",
                )
                > 0
            ]

    # -------------------------------------------------------------
    # Debt declining filter
    # -------------------------------------------------------------

    if thresholds.get(
        "de_declining_yoy"
    ) is True:

        if "de_declining_yoy" in out.columns:

            out = out[
                out["de_declining_yoy"]
                .fillna(False)
            ]

    return out


# ---------------------------------------------------------------------
# SCREENER
# ---------------------------------------------------------------------

def apply_screener(
    df: pd.DataFrame,
    thresholds: Mapping[str, Any],
) -> pd.DataFrame:
    """
    Apply financial screener rules.

    D/E screening is not applied to financial companies because
    leverage has a different meaning for banks, NBFCs and insurers.
    """

    thresholds_copy = dict(
        thresholds
    )

    if "de_max" in thresholds_copy:

        df = df.copy()

        if "broad_sector" in df.columns:

            non_financial = (
                df["broad_sector"]
                .astype(str)
                .str.lower()
                .ne("financials")
            )

            screened = apply_filters(
                df[non_financial],
                thresholds_copy,
            )

            return screened

    return apply_filters(
        df,
        thresholds_copy,
    )


# ---------------------------------------------------------------------
# WINSOR SCALE
# ---------------------------------------------------------------------

def winsor_scale(
    series,
    higher_is_better=True,
):
    """
    Convert values to a 0-100 winsorised score.

    Values are clipped to the 10th and 90th percentiles.

    NaN values receive a neutral score of 50.
    """

    x = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid = x.dropna()

    # Not enough observations
    if len(valid) < 2:
        return pd.Series(
            50.0,
            index=series.index,
        )

    lo, hi = np.nanpercentile(
        valid,
        [10, 90],
    )

    clipped = x.clip(
        lo,
        hi,
    )

    if math.isclose(
        hi,
        lo,
    ):

        score = pd.Series(
            50.0,
            index=x.index,
        )

    else:

        score = (
            (clipped - lo)
            / (hi - lo)
            * 100
        )

    # Reverse score for metrics where lower is better.
    if not higher_is_better:
        score = 100 - score

    # Missing values receive neutral score.
    return score.fillna(50)


# ---------------------------------------------------------------------
# COMPOSITE SCORE
# ---------------------------------------------------------------------

def compute_composite_score(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the Sprint 3 composite quality score.

    Score components:

        Profitability
        Cash Quality
        Growth
        Leverage

    Missing optional columns are handled defensively.
    """

    out = df.copy()

    # -------------------------------------------------------------
    # Required numerical columns
    # -------------------------------------------------------------

    required_numeric = [
        "roe",
        "roce",
        "npm",
        "fcf_cagr_5yr",
        "cfo_pat_ratio",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "de",
        "icr",
    ]

    for column in required_numeric:

        if column not in out.columns:
            out[column] = np.nan

    # -------------------------------------------------------------
    # FCF CAGR fallback
    #
    # Full Sprint 3 database:
    #     fcf_cagr_5yr is calculated from historical DB data.
    #
    # Small unit-test dataframe:
    #     fcf_cagr_5yr may not exist.
    #
    # In that case FCF is used as a defensive proxy so the scoring
    # function remains usable.
    # -------------------------------------------------------------

    if (
        "fcf_cagr_5yr" not in df.columns
        and "fcf" in out.columns
    ):

        out["fcf_cagr_5yr"] = pd.to_numeric(
            out["fcf"],
            errors="coerce",
        )

    # -------------------------------------------------------------
    # CFO/PAT fallback
    # -------------------------------------------------------------

    if (
        "cfo_pat_ratio" not in df.columns
        and "cfo" in out.columns
        and "net_profit" in out.columns
    ):

        cfo = pd.to_numeric(
            out["cfo"],
            errors="coerce",
        )

        net_profit = pd.to_numeric(
            out["net_profit"],
            errors="coerce",
        )

        out["cfo_pat_ratio"] = (
            cfo
            / net_profit.replace(
                0,
                np.nan,
            )
        )

    elif "cfo_pat_ratio" not in df.columns:

        out["cfo_pat_ratio"] = 0.0

    # -------------------------------------------------------------
    # FCF positive fallback
    # -------------------------------------------------------------

    if "fcf_positive" not in out.columns:

        if "fcf" in out.columns:

            out["fcf_positive"] = (
                pd.to_numeric(
                    out["fcf"],
                    errors="coerce",
                )
                > 0
            )

        else:

            out["fcf_positive"] = False

    # -------------------------------------------------------------
    # Ensure broad sector exists
    # -------------------------------------------------------------

    if "broad_sector" not in out.columns:
        out["broad_sector"] = "Unknown"

    out["broad_sector"] = (
        out["broad_sector"]
        .fillna("Unknown")
    )

    # -------------------------------------------------------------
    # PROFITABILITY SCORE
    #
    # ROE       = 15%
    # ROCE      = 10%
    # NPM       = 10%
    #
    # Total     = 35%
    # -------------------------------------------------------------

    profitability_score = (
        winsor_scale(
            out["roe"]
        ) * 0.15

        +

        winsor_scale(
            out["roce"]
        ) * 0.10

        +

        winsor_scale(
            out["npm"]
        ) * 0.10
    )

    # -------------------------------------------------------------
    # CASH QUALITY SCORE
    #
    # FCF CAGR     = 15%
    # CFO/PAT      = 10%
    # FCF Positive  = 5%
    #
    # Total         = 30%
    # -------------------------------------------------------------

    cash_quality_score = (
        winsor_scale(
            out["fcf_cagr_5yr"]
        ) * 0.15

        +

        winsor_scale(
            out["cfo_pat_ratio"]
        ) * 0.10

        +

        winsor_scale(
            out["fcf_positive"].astype(float)
        ) * 0.05
    )

    # -------------------------------------------------------------
    # GROWTH SCORE
    #
    # Revenue CAGR = 10%
    # PAT CAGR     = 10%
    #
    # Total        = 20%
    # -------------------------------------------------------------

    growth_score = (
        winsor_scale(
            out["revenue_cagr_5yr"]
        ) * 0.10

        +

        winsor_scale(
            out["pat_cagr_5yr"]
        ) * 0.10
    )

    # -------------------------------------------------------------
    # LEVERAGE SCORE
    #
    # D/E              = 10%
    # Interest coverage = 5%
    #
    # Total              = 15%
    # -------------------------------------------------------------

    leverage_score = (
        winsor_scale(
            out["de"],
            higher_is_better=False,
        ) * 0.10

        +

        winsor_scale(
            out["icr"]
        ) * 0.05
    )

    # -------------------------------------------------------------
    # Store component scores
    # -------------------------------------------------------------

    out["profitability_score"] = (
        profitability_score
    )

    out["cash_quality_score"] = (
        cash_quality_score
    )

    out["growth_score"] = (
        growth_score
    )

    out["leverage_score"] = (
        leverage_score
    )

    # -------------------------------------------------------------
    # Raw composite score
    # -------------------------------------------------------------

    out["composite_quality_score"] = (
        profitability_score
        + cash_quality_score
        + growth_score
        + leverage_score
    )

    # -------------------------------------------------------------
    # Sector-relative score
    #
    # Companies are normalised against companies in the same
    # broad sector.
    # -------------------------------------------------------------

    out[
        "sector_relative_composite_score"
    ] = (
        out
        .groupby("broad_sector")[
            "composite_quality_score"
        ]
        .transform(
            lambda values:
                winsor_scale(values)
                .reindex(values.index)
        )
    )

    # -------------------------------------------------------------
    # Final score
    # -------------------------------------------------------------

    out["composite_quality_score"] = (
        out[
            "sector_relative_composite_score"
        ]
        .round(2)
    )

    # -------------------------------------------------------------
    # Highest quality first
    # -------------------------------------------------------------

    return out.sort_values(
        "composite_quality_score",
        ascending=False,
    )


# ---------------------------------------------------------------------
# PRESETS
# ---------------------------------------------------------------------

def run_preset(
    df,
    name,
    config,
):
    """
    Run one screener preset and calculate composite score.
    """

    thresholds = config[
        "presets"
    ][name]

    result = apply_screener(
        df,
        thresholds,
    )

    return compute_composite_score(
        result
    )


def run_all_presets(
    df,
    config,
):
    """
    Run every configured screener preset.
    """

    return {
        name: run_preset(
            df,
            name,
            config,
        )

        for name in config[
            "presets"
        ]
    }

