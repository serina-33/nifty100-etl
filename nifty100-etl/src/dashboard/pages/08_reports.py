from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Annual Reports",
    page_icon="📄",
    layout="wide"
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


@st.cache_data(ttl=600)
def get_companies():
    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            """
            SELECT company_id, company_name, ticker
            FROM companies
            ORDER BY company_name
            """,
            conn
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_reports(company_id):
    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            """
            SELECT document_id, company_id, doc_type, url, filed_date
            FROM documents
            WHERE company_id = ?
            ORDER BY filed_date DESC
            """,
            conn,
            params=(company_id,)
        )
    finally:
        conn.close()


st.title("📄 Annual Reports")
st.caption("Company annual reports and filing documents")

companies = get_companies()

if companies.empty:
    st.warning("No companies available.")
    st.stop()


company_label = (
    companies["company_name"].astype(str)
    + " ("
    + companies["ticker"].astype(str)
    + ")"
)

selected_label = st.selectbox(
    "Select Company",
    company_label.tolist()
)

selected_index = company_label.tolist().index(selected_label)

company_id = companies.iloc[selected_index]["company_id"]
company_name = companies.iloc[selected_index]["company_name"]
ticker = companies.iloc[selected_index]["ticker"]

st.subheader(f"{company_name} ({ticker})")

reports = get_reports(company_id)

if reports.empty:

    st.error("🔴 Report unavailable")

    st.info(
        "No annual-report document is currently available "
        "for this company in the project database."
    )

else:

    for _, report in reports.iterrows():

        filed_date = report["filed_date"]

        if pd.isna(filed_date):
            year_display = "Year unavailable"
        else:
            year_display = str(filed_date)[:4]

        doc_type = report["doc_type"]

        if pd.isna(doc_type):
            doc_type = "Annual Report"

        url = report["url"]

        if pd.isna(url):
            url = ""

        url = str(url).strip()

        # IMPORTANT:
        # Define valid_report_url BEFORE using it.
        valid_report_url = (
            url != ""
            and url.lower() not in [
                "nan",
                "none",
                "null",
                "n/a"
            ]
        )

        st.markdown(f"### 📅 {year_display}")

        st.write(f"Document type: {doc_type}")

        if valid_report_url:

            st.link_button(
                "📄 Open Annual Report",
                url,
                width="stretch"
            )

        else:

            st.error("🔴 Report unavailable") 