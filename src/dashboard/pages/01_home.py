import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
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
        return pd.read_sql_query(query, conn, params=params)
    except Exception as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


# ============================================================
# HEADER
# ============================================================

st.title("📊 Nifty 100 Financial Analytics")
st.markdown(
    """
    Welcome to the **Nifty 100 Financial Analytics Dashboard**.

    Explore company profiles, financial performance, ratios,
    screening results, sectors, peers and valuation metrics.
    """
)

st.divider()


# ============================================================
# DATABASE INFORMATION
# ============================================================

tables_df = read_query(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
)

table_names = tables_df["name"].tolist() if not tables_df.empty else []


def table_count(table_name):
    """Return the number of rows in a database table."""
    if table_name not in table_names:
        return 0

    result = read_query(
        f'SELECT COUNT(*) AS count FROM "{table_name}"'
    )

    if result.empty:
        return 0

    return int(result.iloc[0]["count"])


company_count = table_count("companies")
ratio_count = table_count("financial_ratios")


# ============================================================
# KPI CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Nifty 100 Companies",
        f"{company_count:,}",
    )

with col2:
    st.metric(
        "Financial Ratio Records",
        f"{ratio_count:,}",
    )

with col3:
    st.metric(
        "Database Tables",
        f"{len(table_names):,}",
    )

with col4:
    st.metric(
        "Project Status",
        "Completed",
    )


st.divider()


# ============================================================
# COMPANY DATA
# ============================================================

st.subheader("🏢 Company Overview")

companies = read_query(
    """
    SELECT *
    FROM companies
    LIMIT 100
    """
)

if companies.empty:
    st.warning("No company records were found in the database.")
else:
    # Find useful columns dynamically
    preferred_columns = [
        "company_id",
        "ticker",
        "company_name",
        "broad_sector",
        "sub_sector",
        "market_cap_category",
        "roe_percentage",
        "roe_pct",
        "roce_percentage",
        "roce_pct",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in companies.columns
    ]

    if available_columns:
        display_df = companies[available_columns].copy()
    else:
        display_df = companies.copy()

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# SECTOR SUMMARY
# ============================================================

st.subheader("🏭 Sector Summary")

if "broad_sector" in companies.columns:

    sector_summary = (
        companies["broad_sector"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    sector_summary.columns = [
        "Sector",
        "Company Count",
    ]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.dataframe(
            sector_summary,
            width="stretch",
            hide_index=True,
        )

    with col2:
        st.bar_chart(
            sector_summary.set_index("Sector")
        )

else:
    st.info(
        "The companies table does not contain a broad_sector column."
    )


# ============================================================
# DATABASE TABLES
# ============================================================

st.subheader("🗄️ Database Tables")

if table_names:
    table_info = []

    for table in table_names:
        table_info.append(
            {
                "Table": table,
                "Rows": table_count(table),
            }
        )

    table_info_df = pd.DataFrame(table_info)

    st.dataframe(
        table_info_df,
        width="stretch",
        hide_index=True,
    )
else:
    st.warning("No database tables were found.")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Nifty 100 Financial Analytics | SQLite + Python + Streamlit"
) 
 