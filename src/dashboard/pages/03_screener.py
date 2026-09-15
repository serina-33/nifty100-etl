from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

from src.screener.engine import (
    latest_complete_snapshot,
    apply_screener,
    compute_composite_score,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Stock Screener",
    page_icon="🔎",
    layout="wide",
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


def load_screener_data():
    """
    Load the latest complete financial snapshot.

    latest_complete_snapshot() requires a SQLite connection,
    so we explicitly create and pass the connection here.
    """
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}")
        return pd.DataFrame()

    conn = None

    try:
        conn = sqlite3.connect(DB_PATH)

        df = latest_complete_snapshot(conn)

        if df is None:
            return pd.DataFrame()

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        return df

    except Exception as e:
        st.error("Unable to load screener data.")
        st.exception(e)
        return pd.DataFrame()

    finally:
        if conn is not None:
            conn.close()


# ============================================================
# LOAD DATA
# ============================================================

df = load_screener_data()

if df.empty:
    st.warning(
        "No screener data is available. "
        "Please check the database and financial data."
    )
    st.stop()


# ============================================================
# NORMALIZE COLUMN NAMES
# ============================================================

df.columns = [str(c).strip() for c in df.columns]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_column(dataframe, possible_names):
    """
    Find the first matching column from a list of possible names.
    """
    lower_map = {
        str(col).lower().strip(): col
        for col in dataframe.columns
    }

    for name in possible_names:
        key = str(name).lower().strip()

        if key in lower_map:
            return lower_map[key]

    return None


def numeric_series(dataframe, possible_names, default=0.0):
    """
    Return a numeric Series safely.
    """
    col = find_column(dataframe, possible_names)

    if col is None:
        return pd.Series(
            default,
            index=dataframe.index,
            dtype="float64",
        )

    return pd.to_numeric(
        dataframe[col],
        errors="coerce",
    ).fillna(default)


def safe_display_number(value, decimals=2):
    """
    Convert a value into a dashboard-friendly number.
    """
    try:
        value = float(value)

        if np.isnan(value):
            return "N/A"

        return f"{value:.{decimals}f}"

    except Exception:
        return "N/A"


# ============================================================
# CREATE COMPATIBLE COLUMNS
# ============================================================

# ROE
if find_column(df, ["roe_pct", "ROE", "roe"]) is None:
    df["roe_pct"] = numeric_series(
        df,
        ["roe_pct", "ROE", "roe"],
    )

# ROCE
if find_column(df, ["roce_pct", "ROCE", "roce"]) is None:
    df["roce_pct"] = numeric_series(
        df,
        ["roce_pct", "ROCE", "roce"],
    )

# Debt to Equity
if find_column(df, ["debt_to_equity", "D/E", "de"]) is None:
    df["debt_to_equity"] = numeric_series(
        df,
        ["debt_to_equity", "D/E", "de"],
    )

# FCF
if find_column(df, ["fcf", "free_cash_flow", "free_cashflow"]) is None:
    df["fcf"] = numeric_series(
        df,
        ["fcf", "free_cash_flow", "free_cashflow"],
    )

# Revenue CAGR
if find_column(
    df,
    ["revenue_cagr_5yr", "revenue_cagr", "sales_cagr_5yr"]
) is None:
    df["revenue_cagr_5yr"] = numeric_series(
        df,
        [
            "revenue_cagr_5yr",
            "revenue_cagr",
            "sales_cagr_5yr",
        ],
    )

# PAT CAGR
if find_column(
    df,
    ["pat_cagr_5yr", "pat_cagr", "profit_cagr_5yr"]
) is None:
    df["pat_cagr_5yr"] = numeric_series(
        df,
        [
            "pat_cagr_5yr",
            "pat_cagr",
            "profit_cagr_5yr",
        ],
    )

# OPM
if find_column(
    df,
    ["opm_pct", "OPM", "operating_margin"]
) is None:
    df["opm_pct"] = numeric_series(
        df,
        ["opm_pct", "OPM", "operating_margin"],
    )

# P/E
if find_column(
    df,
    ["pe_ratio", "P/E", "pe"]
) is None:
    df["pe_ratio"] = numeric_series(
        df,
        ["pe_ratio", "P/E", "pe"],
    )

# P/B
if find_column(
    df,
    ["pb_ratio", "P/B", "pb"]
) is None:
    df["pb_ratio"] = numeric_series(
        df,
        ["pb_ratio", "P/B", "pb"],
    )

# Dividend payout
if find_column(
    df,
    [
        "dividend_payout_pct",
        "dividend_yield",
        "dividend_yield_pct",
        "payout",
    ]
) is None:
    df["dividend_payout_pct"] = numeric_series(
        df,
        [
            "dividend_payout_pct",
            "dividend_yield",
            "dividend_yield_pct",
            "payout",
        ],
    )

# Interest Coverage Ratio
if find_column(
    df,
    [
        "interest_coverage_ratio",
        "interest_coverage",
        "icr",
        "ICR",
    ]
) is None:
    df["interest_coverage_ratio"] = numeric_series(
        df,
        [
            "interest_coverage_ratio",
            "interest_coverage",
            "icr",
            "ICR",
        ],
    )


# ============================================================
# TITLE
# ============================================================

st.title("🔎 Stock Screener")

st.write(
    "Filter Nifty 100 companies using financial quality, "
    "valuation, growth, dividend and debt metrics."
)


# ============================================================
# PRESETS
# ============================================================

st.subheader("Screening Presets")

preset_options = [
    "Custom",
    "Quality",
    "Value",
    "Growth",
    "Dividend",
    "Debt-Free",
    "Turnaround",
]

preset = st.selectbox(
    "Choose a preset",
    preset_options,
    index=0,
)


# ============================================================
# DEFAULT VALUES
# ============================================================

defaults = {
    "roe_min": 0.0,
    "de_max": 10.0,
    "fcf_min": -100000.0,
    "revenue_cagr_min": -50.0,
    "pat_cagr_min": -50.0,
    "opm_min": -50.0,
    "pe_max": 200.0,
    "pb_max": 50.0,
    "dividend_min": 0.0,
    "icr_min": 0.0,
}


# ============================================================
# PRESET VALUES
# ============================================================

preset_values = {
    "Quality": {
        "roe_min": 15.0,
        "de_max": 1.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 8.0,
        "pat_cagr_min": 8.0,
        "opm_min": 15.0,
        "pe_max": 60.0,
        "pb_max": 10.0,
        "dividend_min": 0.0,
        "icr_min": 3.0,
    },
    "Value": {
        "roe_min": 8.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "pe_max": 25.0,
        "pb_max": 5.0,
        "dividend_min": 0.0,
        "icr_min": 1.5,
    },
    "Growth": {
        "roe_min": 12.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 12.0,
        "pat_cagr_min": 15.0,
        "opm_min": 10.0,
        "pe_max": 100.0,
        "pb_max": 15.0,
        "dividend_min": 0.0,
        "icr_min": 2.0,
    },
    "Dividend": {
        "roe_min": 8.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "pe_max": 50.0,
        "pb_max": 10.0,
        "dividend_min": 2.0,
        "icr_min": 1.5,
    },
    "Debt-Free": {
        "roe_min": 10.0,
        "de_max": 0.1,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "pe_max": 100.0,
        "pb_max": 15.0,
        "dividend_min": 0.0,
        "icr_min": 3.0,
    },
    "Turnaround": {
        "roe_min": 5.0,
        "de_max": 3.0,
        "fcf_min": -10000.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 15.0,
        "dividend_min": 0.0,
        "icr_min": 1.0,
    },
}


if preset != "Custom":
    selected_defaults = preset_values[preset]
else:
    selected_defaults = defaults


# ============================================================
# SESSION STATE FOR SLIDERS
# ============================================================

for key, value in selected_defaults.items():
    state_key = f"screener_{key}"

    if (
        preset != "Custom"
        and st.session_state.get("last_screener_preset") != preset
    ):
        st.session_state[state_key] = value

    elif state_key not in st.session_state:
        st.session_state[state_key] = value


st.session_state["last_screener_preset"] = preset


# ============================================================
# FILTER SLIDERS
# ============================================================

st.subheader("Screening Filters")

col1, col2, col3, col4, col5 = st.columns(5)


with col1:
    roe_min = st.slider(
        "ROE minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        value=float(st.session_state["screener_roe_min"]),
        step=1.0,
        key="screener_roe_min",
    )

    de_max = st.slider(
        "Debt / Equity maximum",
        min_value=0.0,
        max_value=20.0,
        value=float(st.session_state["screener_de_max"]),
        step=0.1,
        key="screener_de_max",
    )


with col2:
    fcf_min = st.slider(
        "FCF minimum",
        min_value=-100000.0,
        max_value=100000.0,
        value=float(st.session_state["screener_fcf_min"]),
        step=1000.0,
        key="screener_fcf_min",
    )

    revenue_cagr_min = st.slider(
        "Revenue CAGR minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        value=float(
            st.session_state["screener_revenue_cagr_min"]
        ),
        step=1.0,
        key="screener_revenue_cagr_min",
    )


with col3:
    pat_cagr_min = st.slider(
        "PAT CAGR minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        value=float(
            st.session_state["screener_pat_cagr_min"]
        ),
        step=1.0,
        key="screener_pat_cagr_min",
    )

    opm_min = st.slider(
        "OPM minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        value=float(st.session_state["screener_opm_min"]),
        step=1.0,
        key="screener_opm_min",
    )


with col4:
    pe_max = st.slider(
        "P/E maximum",
        min_value=0.0,
        max_value=200.0,
        value=float(st.session_state["screener_pe_max"]),
        step=1.0,
        key="screener_pe_max",
    )

    pb_max = st.slider(
        "P/B maximum",
        min_value=0.0,
        max_value=50.0,
        value=float(st.session_state["screener_pb_max"]),
        step=0.5,
        key="screener_pb_max",
    )


with col5:
    dividend_min = st.slider(
        "Dividend minimum (%)",
        min_value=0.0,
        max_value=20.0,
        value=float(
            st.session_state["screener_dividend_min"]
        ),
        step=0.5,
        key="screener_dividend_min",
    )

    icr_min = st.slider(
        "ICR minimum",
        min_value=0.0,
        max_value=30.0,
        value=float(st.session_state["screener_icr_min"]),
        step=0.5,
        key="screener_icr_min",
    )


# ============================================================
# APPLY SCREENER
# ============================================================

thresholds = {
    "roe_min": roe_min,
    "de_max": de_max,
    "fcf_min": fcf_min,
    "revenue_cagr_min": revenue_cagr_min,
    "pat_cagr_min": pat_cagr_min,
    "opm_min": opm_min,
    "pe_max": pe_max,
    "pb_max": pb_max,
    "dividend_min": dividend_min,
    "icr_min": icr_min,
}


# ============================================================
# RUN SCREENING
# ============================================================

try:
    filtered = apply_screener(
        df.copy(),
        thresholds,
    )

except TypeError:
    # Compatibility fallback if engine expects
    # individual keyword arguments.
    try:
        filtered = apply_screener(
            df.copy(),
            roe_min=roe_min,
            de_max=de_max,
            fcf_min=fcf_min,
            revenue_cagr_min=revenue_cagr_min,
            pat_cagr_min=pat_cagr_min,
            opm_min=opm_min,
            pe_max=pe_max,
            pb_max=pb_max,
            dividend_min=dividend_min,
            icr_min=icr_min,
        )

    except Exception as e:
        st.error("Unable to apply screener filters.")
        st.exception(e)
        filtered = pd.DataFrame()

except Exception as e:
    st.error("Unable to apply screener filters.")
    st.exception(e)
    filtered = pd.DataFrame()


# ============================================================
# COMPOSITE QUALITY SCORE
# ============================================================

if not filtered.empty:

    try:
        scored = compute_composite_score(filtered.copy())

        if isinstance(scored, pd.DataFrame):
            filtered = scored

    except Exception:
        # If the engine's score function is not compatible,
        # continue showing the filtered results.
        pass


# ============================================================
# RESULT COUNT
# ============================================================

st.divider()

result_col1, result_col2, result_col3 = st.columns(3)

with result_col1:
    st.metric(
        "Companies Found",
        len(filtered),
    )

with result_col2:
    st.metric(
        "Companies Available",
        len(df),
    )

with result_col3:
    percentage = (
        (len(filtered) / len(df)) * 100
        if len(df) > 0
        else 0
    )

    st.metric(
        "Match %",
        f"{percentage:.1f}%",
    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

st.subheader("Screening Results")


if filtered.empty:

    st.warning(
        "No companies match the selected filters. "
        "Try relaxing one or more filters."
    )

else:

    display_df = filtered.copy()

    # --------------------------------------------------------
    # Rename common columns for dashboard display
    # --------------------------------------------------------

    rename_map = {}

    column_mapping = {
        "company_name": "Company",
        "ticker": "Ticker",
        "sector": "Sector",
        "roe_pct": "ROE %",
        "roce_pct": "ROCE %",
        "opm_pct": "OPM %",
        "debt_to_equity": "D/E",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "revenue_cagr_5yr": "Revenue CAGR 5Y %",
        "pat_cagr_5yr": "PAT CAGR 5Y %",
        "fcf": "FCF",
        "dividend_payout_pct": "Dividend %",
        "interest_coverage_ratio": "ICR",
        "composite_score": "Quality Score",
        "score": "Quality Score",
    }

    for old_name, new_name in column_mapping.items():
        if old_name in display_df.columns:
            rename_map[old_name] = new_name

    display_df = display_df.rename(
        columns=rename_map
    )


    # --------------------------------------------------------
    # Select useful columns
    # --------------------------------------------------------

    preferred_columns = [
        "Company",
        "Ticker",
        "Sector",
        "ROE %",
        "ROCE %",
        "OPM %",
        "D/E",
        "P/E",
        "P/B",
        "Revenue CAGR 5Y %",
        "PAT CAGR 5Y %",
        "FCF",
        "Dividend %",
        "ICR",
        "Quality Score",
    ]

    available_columns = [
        col
        for col in preferred_columns
        if col in display_df.columns
    ]

    if available_columns:
        display_df = display_df[
            available_columns
        ]


    # --------------------------------------------------------
    # Clean NaN / Infinity
    # --------------------------------------------------------

    display_df = display_df.replace(
        [np.inf, -np.inf],
        np.nan,
    )


    # --------------------------------------------------------
    # Sort by Quality Score when available
    # --------------------------------------------------------

    if "Quality Score" in display_df.columns:
        display_df = display_df.sort_values(
            "Quality Score",
            ascending=False,
            na_position="last",
        )


    # --------------------------------------------------------
    # Display table
    # --------------------------------------------------------

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )


    # ========================================================
    # CSV DOWNLOAD
    # ========================================================

    csv_data = display_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Screening Results CSV",
        data=csv_data,
        file_name="screener_results.csv",
        mime="text/csv",
    )


# ============================================================
# ACTIVE FILTER SUMMARY
# ============================================================

with st.expander("View Active Filters"):

    filter_summary = pd.DataFrame(
        {
            "Filter": [
                "Preset",
                "ROE minimum",
                "D/E maximum",
                "FCF minimum",
                "Revenue CAGR minimum",
                "PAT CAGR minimum",
                "OPM minimum",
                "P/E maximum",
                "P/B maximum",
                "Dividend minimum",
                "ICR minimum",
            ],
            "Value": [
                preset,
                f"{roe_min:.1f}%",
                f"{de_max:.1f}",
                f"{fcf_min:,.0f}",
                f"{revenue_cagr_min:.1f}%",
                f"{pat_cagr_min:.1f}%",
                f"{opm_min:.1f}%",
                f"{pe_max:.1f}",
                f"{pb_max:.1f}",
                f"{dividend_min:.1f}%",
                f"{icr_min:.1f}",
            ],
        }
    )

    st.dataframe(
        filter_summary,
        width="stretch",
        hide_index=True,
    ) 