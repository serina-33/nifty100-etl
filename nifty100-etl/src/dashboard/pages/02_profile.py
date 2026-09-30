import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Company Profile",
    page_icon="🏢",
    layout="wide",
)


# ============================================================
# DATABASE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


@st.cache_resource
def get_connection():
    """Create a SQLite database connection."""
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}")
        st.stop()

    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
    )


conn = get_connection()


def read_query(query, params=()):
    """Run a SQL query and return a DataFrame."""
    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )
    except Exception as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


# ============================================================
# HEADER
# ============================================================

st.title("🏢 Company Profile")

st.markdown(
    """
    Select a Nifty 100 company to view its profile,
    financial information and available historical data.
    """
)

st.divider()


# ============================================================
# GET COMPANY LIST
# ============================================================

companies = read_query(
    """
    SELECT *
    FROM companies
    """
)

if companies.empty:
    st.error("No companies found in the database.")
    st.stop()


# ============================================================
# IDENTIFY COMPANY COLUMN
# ============================================================

if "company_id" in companies.columns:
    id_column = "company_id"
elif "ticker" in companies.columns:
    id_column = "ticker"
else:
    id_column = companies.columns[0]


# Try to find the best display name column
if "company_name" in companies.columns:
    name_column = "company_name"
elif "name" in companies.columns:
    name_column = "name"
else:
    name_column = id_column


# ============================================================
# COMPANY SELECTOR
# ============================================================

company_options = companies[id_column].dropna().astype(str).tolist()

selected_company = st.selectbox(
    "Select Company",
    company_options,
)


selected_row = companies[
    companies[id_column].astype(str) == selected_company
]

if selected_row.empty:
    st.error("Selected company was not found.")
    st.stop()


company = selected_row.iloc[0]


# ============================================================
# COMPANY TITLE
# ============================================================

company_name = company.get(
    name_column,
    selected_company,
)

st.header(str(company_name))

st.caption(
    f"Company ID / Ticker: {selected_company}"
)


# ============================================================
# BASIC INFORMATION
# ============================================================

st.subheader("📌 Company Information")

info_columns = [
    "company_id",
    "ticker",
    "company_name",
    "broad_sector",
    "sub_sector",
    "market_cap_category",
]

info_data = {}

for column in info_columns:
    if column in companies.columns:
        value = company[column]

        if pd.isna(value):
            value = "N/A"

        info_data[column.replace("_", " ").title()] = value


if info_data:
    info_df = pd.DataFrame(
        list(info_data.items()),
        columns=["Field", "Value"],
    )

    st.dataframe(
        info_df,
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No basic company information available.")


# ============================================================
# FINANCIAL KPIs
# ============================================================

st.subheader("📈 Latest Financial KPIs")

kpi_columns = [
    "roe_percentage",
    "roe_pct",
    "roce_percentage",
    "roce_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "pat_cagr_5yr",
    "pe_ratio",
    "price_to_book",
    "ev_to_ebitda",
    "dividend_yield",
]

available_kpis = [
    column
    for column in kpi_columns
    if column in companies.columns
]

if available_kpis:

    metric_columns = st.columns(
        min(4, len(available_kpis))
    )

    for index, column in enumerate(available_kpis):

        value = company[column]

        if pd.isna(value):
            value = "N/A"
        elif isinstance(value, (int, float)):
            value = f"{value:.2f}"

        with metric_columns[
            index % len(metric_columns)
        ]:
            st.metric(
                column.replace("_", " ").title(),
                value,
            )

else:
    st.info(
        "No KPI columns were found directly in the companies table."
    )


# ============================================================
# FINANCIAL RATIOS TABLE
# ============================================================

st.subheader("📊 Financial Ratios")

try:

    ratio_columns_df = read_query(
        "PRAGMA table_info(financial_ratios)"
    )

    if not ratio_columns_df.empty:

        ratio_columns = ratio_columns_df[
            "name"
        ].tolist()

        # Find company identifier used in ratios
        if "company_id" in ratio_columns:
            ratio_id_column = "company_id"
        elif "ticker" in ratio_columns:
            ratio_id_column = "ticker"
        else:
            ratio_id_column = None

        if ratio_id_column:

            ratios = read_query(
                f"""
                SELECT *
                FROM financial_ratios
                WHERE CAST("{ratio_id_column}" AS TEXT) = ?
                """,
                (str(selected_company),),
            )

            if ratios.empty:

                # Sometimes company_id may differ from ticker.
                # Try company name if available.
                st.info(
                    "No financial ratio records found for this company."
                )

            else:
                st.dataframe(
                    ratios,
                    width="stretch",
                    hide_index=True,
                )

        else:
            st.info(
                "Could not identify the company column in financial_ratios."
            )

except Exception as exc:
    st.info(
        f"Financial ratio table could not be loaded: {exc}"
    )


# ============================================================
# HISTORICAL DATA
# ============================================================

st.subheader("📅 Historical Financial Data")

possible_tables = [
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "cashflow",
    "pl",
    "bs",
]

tables_df = read_query(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    """
)

existing_tables = (
    tables_df["name"].tolist()
    if not tables_df.empty
    else []
)

available_financial_tables = [
    table
    for table in possible_tables
    if table in existing_tables
]


if available_financial_tables:

    selected_table = st.selectbox(
        "Select financial statement",
        available_financial_tables,
    )

    statement = read_query(
        f'SELECT * FROM "{selected_table}" LIMIT 200'
    )

    if not statement.empty:

        # Try to filter using company_id/ticker
        statement_columns = statement.columns.tolist()

        filter_column = None

        if "company_id" in statement_columns:
            filter_column = "company_id"
        elif "ticker" in statement_columns:
            filter_column = "ticker"

        if filter_column:

            full_statement = read_query(
                f'SELECT * FROM "{selected_table}" '
                f'WHERE CAST("{filter_column}" AS TEXT) = ?',
                (str(selected_company),),
            )

            if not full_statement.empty:
                statement = full_statement

        st.dataframe(
            statement,
            width="stretch",
            hide_index=True,
        )

    else:
        st.info(
            f"No data found in {selected_table}."
        )

else:
    st.info(
        "No standard historical financial statement "
        "tables were found."
    )


# ============================================================
# RAW COMPANY RECORD
# ============================================================

with st.expander("🔎 View Complete Company Record"):

    raw_record = pd.DataFrame(
        [company.to_dict()]
    )

    st.dataframe(
        raw_record,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Nifty 100 Financial Analytics | Company Profile"
) 