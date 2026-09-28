from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"


# ============================================================
# MARKET CAP LOADER
# ============================================================

def load_market_cap():
    """
    Search for market_cap.xlsx in the common project locations.
    """

    candidates = [
        ROOT / "market_cap.xlsx",
        ROOT / "data" / "raw" / "market_cap.xlsx",
        ROOT / "data" / "market_cap.xlsx",
    ]

    for path in candidates:
        if path.exists():
            print(f"Market cap file found: {path}")

            try:
                return pd.read_excel(path)
            except Exception as exc:
                print(f"Could not read market cap file: {exc}")
                return pd.DataFrame()

    print("WARNING: market_cap.xlsx was not found.")
    print("FCF yield will be N/A unless market cap data is available.")

    return pd.DataFrame()


# ============================================================
# NORMALISE MARKET CAP DATA
# ============================================================

def prepare_market_cap(market_cap):
    """
    Standardise market cap column names and identify
    ticker + market cap columns.
    """

    if market_cap.empty:
        return pd.DataFrame()

    market_cap = market_cap.copy()

    market_cap.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    ]

    # --------------------------------------------------------
    # Find ticker column
    # --------------------------------------------------------

    ticker_col = None

    possible_ticker_columns = [
        "ticker",
        "symbol",
        "stock",
        "company_ticker",
    ]

    for column in possible_ticker_columns:
        if column in market_cap.columns:
            ticker_col = column
            break

    # --------------------------------------------------------
    # Find market cap column
    # --------------------------------------------------------

    market_cap_col = None

    possible_market_cap_columns = [
        "market_cap_crore",
        "market_cap",
        "market_cap_cr",
        "market_cap_in_crore",
    ]

    for column in possible_market_cap_columns:
        if column in market_cap.columns:
            market_cap_col = column
            break

    if ticker_col is None:
        print("WARNING: No ticker column found in market_cap.xlsx")
        return pd.DataFrame()

    if market_cap_col is None:
        print("WARNING: No market cap column found in market_cap.xlsx")
        return pd.DataFrame()

    # --------------------------------------------------------
    # Clean values
    # --------------------------------------------------------

    market_cap[ticker_col] = (
        market_cap[ticker_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    market_cap[market_cap_col] = pd.to_numeric(
        market_cap[market_cap_col],
        errors="coerce",
    )

    market_cap = market_cap[
        [ticker_col, market_cap_col]
    ].copy()

    market_cap = market_cap.rename(
        columns={
            ticker_col: "ticker",
            market_cap_col: "market_cap_crore",
        }
    )

    return market_cap


# ============================================================
# LOAD DATABASE TABLES
# ============================================================

def load_database_tables():
    """
    Load companies, financial ratios, profit & loss,
    and cash flow data from SQLite.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                company_id,
                company_name,
                ticker,
                sector
            FROM companies
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            conn,
        )

        profit_loss = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            """,
            conn,
        )

        cashflow = pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            """,
            conn,
        )

    finally:
        conn.close()

    return companies, ratios, profit_loss, cashflow


# ============================================================
# LATEST RATIOS
# ============================================================

def get_latest_ratios(ratios):
    """
    Get the latest financial ratio record for each company.
    """

    if ratios.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "year",
                "pe_ratio",
                "pb_ratio",
            ]
        )

    ratios = ratios.copy()

    # Make sure year is numeric
    if "year" in ratios.columns:
        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce",
        )
    else:
        ratios["year"] = np.nan

    # Ensure P/E exists
    if "pe_ratio" not in ratios.columns:
        ratios["pe_ratio"] = np.nan

    # Ensure P/B exists
    if "pb_ratio" not in ratios.columns:
        ratios["pb_ratio"] = np.nan

    ratios["pe_ratio"] = pd.to_numeric(
        ratios["pe_ratio"],
        errors="coerce",
    )

    ratios["pb_ratio"] = pd.to_numeric(
        ratios["pb_ratio"],
        errors="coerce",
    )

    ratios = ratios.sort_values(
        ["company_id", "year"]
    )

    latest = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest = latest[
        [
            "company_id",
            "year",
            "pe_ratio",
            "pb_ratio",
        ]
    ]

    return latest


# ============================================================
# FCF CALCULATION
# ============================================================

def calculate_latest_fcf(cashflow):
    """
    Calculate latest Free Cash Flow.

    FCF = Cash From Operations - Cash From Investing
    """

    if cashflow.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "fcf",
            ]
        )

    cashflow = cashflow.copy()

    if "year" in cashflow.columns:
        cashflow["year"] = pd.to_numeric(
            cashflow["year"],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    if "cash_from_operations" not in cashflow.columns:
        cashflow["cash_from_operations"] = np.nan

    if "cash_from_investing" not in cashflow.columns:
        cashflow["cash_from_investing"] = np.nan

    cashflow["cash_from_operations"] = pd.to_numeric(
        cashflow["cash_from_operations"],
        errors="coerce",
    )

    cashflow["cash_from_investing"] = pd.to_numeric(
        cashflow["cash_from_investing"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Latest year for every company
    # --------------------------------------------------------

    cashflow = cashflow.sort_values(
        ["company_id", "year"]
    )

    latest = (
        cashflow
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    latest["fcf"] = (
        latest["cash_from_operations"]
        - latest["cash_from_investing"]
    )

    return latest[
        [
            "company_id",
            "fcf",
        ]
    ]


# ============================================================
# 5-YEAR MEDIAN P/E
# ============================================================

def calculate_5yr_median_pe(ratios):
    """
    Calculate the median P/E using the latest 5 available
    years for each company.
    """

    if ratios.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "5yr_median_PE",
            ]
        )

    ratios = ratios.copy()

    if "pe_ratio" not in ratios.columns:
        return pd.DataFrame(
            columns=[
                "company_id",
                "5yr_median_PE",
            ]
        )

    ratios["pe_ratio"] = pd.to_numeric(
        ratios["pe_ratio"],
        errors="coerce",
    )

    if "year" in ratios.columns:
        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce",
        )
    else:
        ratios["year"] = np.nan

    ratios = ratios.dropna(
        subset=["pe_ratio"]
    )

    if ratios.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "5yr_median_PE",
            ]
        )

    ratios = ratios.sort_values(
        ["company_id", "year"]
    )

    last_5 = (
        ratios
        .groupby("company_id")
        .tail(5)
        .copy()
    )

    median_pe = (
        last_5
        .groupby("company_id")["pe_ratio"]
        .median()
        .reset_index()
    )

    median_pe = median_pe.rename(
        columns={
            "pe_ratio": "5yr_median_PE"
        }
    )

    return median_pe


# ============================================================
# BUILD VALUATION
# ============================================================

def build():
    """
    Build the complete valuation summary.

    Output columns:

    company_id
    company_name
    sector
    P/E
    P/B
    EV/EBITDA
    FCF_yield_pct
    5yr_median_PE
    PE_vs_sector_median_pct
    flag
    """

    print("=" * 70)
    print("NIFTY 100 VALUATION ANALYSIS")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Load database
    # --------------------------------------------------------

    print("\nLoading database...")

    companies, ratios, profit_loss, cashflow = (
        load_database_tables()
    )

    print(
        f"Companies loaded: {len(companies)}"
    )

    print(
        f"Financial ratio rows: {len(ratios)}"
    )

    print(
        f"Cash flow rows: {len(cashflow)}"
    )

    # --------------------------------------------------------
    # Latest ratios
    # --------------------------------------------------------

    latest_ratios = get_latest_ratios(
        ratios
    )

    # --------------------------------------------------------
    # Base company table
    # --------------------------------------------------------

    output = companies[
        [
            "company_id",
            "company_name",
            "ticker",
            "sector",
        ]
    ].copy()

    output = output.merge(
        latest_ratios,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Market cap
    # --------------------------------------------------------

    market_cap = load_market_cap()

    market_cap = prepare_market_cap(
        market_cap
    )

    if not market_cap.empty:

        output["ticker"] = (
            output["ticker"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        output = output.merge(
            market_cap,
            on="ticker",
            how="left",
        )

    else:

        output["market_cap_crore"] = np.nan

    # --------------------------------------------------------
    # Latest FCF
    # --------------------------------------------------------

    latest_fcf = calculate_latest_fcf(
        cashflow
    )

    output = output.merge(
        latest_fcf,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # FCF Yield
    #
    # FCF Yield = FCF / Market Cap × 100
    # --------------------------------------------------------

    output["fcf_yield_pct"] = np.where(
        (
            output["market_cap_crore"].notna()
            &
            (output["market_cap_crore"] > 0)
            &
            output["fcf"].notna()
        ),
        (
            output["fcf"]
            / output["market_cap_crore"]
            * 100
        ),
        np.nan,
    )

    # --------------------------------------------------------
    # 5-year median P/E
    # --------------------------------------------------------

    median_pe = calculate_5yr_median_pe(
        ratios
    )

    output = output.merge(
        median_pe,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Sector median P/E
    # --------------------------------------------------------

    output["pe_ratio"] = pd.to_numeric(
        output["pe_ratio"],
        errors="coerce",
    )

    sector_median = (
        output
        .groupby("sector")["pe_ratio"]
        .median()
        .rename("sector_median_pe")
        .reset_index()
    )

    output = output.merge(
        sector_median,
        on="sector",
        how="left",
    )

    # --------------------------------------------------------
    # P/E vs sector median
    #
    # Formula:
    #
    # ((Company P/E / Sector Median P/E) - 1) × 100
    # --------------------------------------------------------

    output["PE_vs_sector_median_pct"] = np.where(
        (
            output["pe_ratio"].notna()
            &
            output["sector_median_pe"].notna()
            &
            (output["sector_median_pe"] > 0)
        ),
        (
            (
                output["pe_ratio"]
                / output["sector_median_pe"]
            )
            - 1
        )
        * 100,
        np.nan,
    )

    # --------------------------------------------------------
    # Valuation flags
    #
    # P/E > sector median × 1.5
    #       -> Caution
    #
    # P/E < sector median × 0.7
    #       -> Discount
    #
    # Otherwise
    #       -> Fair
    # --------------------------------------------------------

    output["flag"] = "Fair"

    caution_condition = (
        output["pe_ratio"].notna()
        &
        output["sector_median_pe"].notna()
        &
        (
            output["pe_ratio"]
            > output["sector_median_pe"] * 1.5
        )
    )

    discount_condition = (
        output["pe_ratio"].notna()
        &
        output["sector_median_pe"].notna()
        &
        (
            output["pe_ratio"]
            < output["sector_median_pe"] * 0.7
        )
    )

    output.loc[
        caution_condition,
        "flag",
    ] = "Caution"

    output.loc[
        discount_condition,
        "flag",
    ] = "Discount"

    # --------------------------------------------------------
    # EV/EBITDA
    #
    # If EV/EBITDA is not present in the project database,
    # keep it as N/A instead of crashing.
    # --------------------------------------------------------

    output["EV/EBITDA"] = np.nan

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    final_output = output[
        [
            "company_id",
            "company_name",
            "sector",
            "pe_ratio",
            "pb_ratio",
            "EV/EBITDA",
            "fcf_yield_pct",
            "5yr_median_PE",
            "PE_vs_sector_median_pct",
            "flag",
        ]
    ].copy()

    # ========================================================
    # IMPORTANT:
    # Rename FCF column to EXACT required Sprint 4 name
    # ========================================================

    final_output = final_output.rename(
        columns={
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "fcf_yield_pct": "FCF_yield_pct",
        }
    )

    # --------------------------------------------------------
    # Ensure exact column order
    # --------------------------------------------------------

    final_output = final_output[
        [
            "company_id",
            "company_name",
            "sector",
            "P/E",
            "P/B",
            "EV/EBITDA",
            "FCF_yield_pct",
            "5yr_median_PE",
            "PE_vs_sector_median_pct",
            "flag",
        ]
    ]

    # --------------------------------------------------------
    # Excel output
    # --------------------------------------------------------

    summary_path = (
        OUTPUT_DIR
        / "valuation_summary.xlsx"
    )

    final_output.to_excel(
        summary_path,
        index=False,
    )

    # --------------------------------------------------------
    # Flagged companies only
    # --------------------------------------------------------

    flags = final_output[
        final_output["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    flags_path = (
        OUTPUT_DIR
        / "valuation_flags.csv"
    )

    flags.to_csv(
        flags_path,
        index=False,
    )

    # --------------------------------------------------------
    # Print verification
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("VALUATION OUTPUT CREATED")
    print("=" * 70)

    print(
        f"\nRows: {len(final_output)}"
    )

    print(
        "\nColumns:"
    )

    print(
        list(final_output.columns)
    )

    print(
        f"\nExcel file:"
    )

    print(
        summary_path
    )

    print(
        f"\nCSV file:"
    )

    print(
        flags_path
    )

    print("\nFlag distribution:")

    print(
        final_output["flag"]
        .value_counts(dropna=False)
    )

    print("\nFCF yield available:")

    print(
        final_output["FCF_yield_pct"]
        .notna()
        .sum()
    )

    print("\n" + "=" * 70)

    return final_output


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    df = build()

    print(
        "\nSUCCESS: Valuation analysis completed."
    )