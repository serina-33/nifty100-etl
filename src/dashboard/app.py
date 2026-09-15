from pathlib import Path

import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

DASHBOARD_DIR = Path(__file__).resolve().parent
PAGES_DIR = DASHBOARD_DIR / "pages"


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PAGE DEFINITIONS
# ============================================================

PAGES = {
    "01_home.py": "🏠 Home",
    "02_profile.py": "🏢 Company Profile",
    "03_screener.py": "🔎 Stock Screener",
    "04_peers.py": "👥 Peer Comparison",
    "05_trends.py": "📈 Trends",
    "06_sectors.py": "🏭 Sector Analysis",
    "07_capital.py": "💰 Capital Allocation",
    "08_reports.py": "📄 Reports",
}


# ============================================================
# CHECK PAGE FILES
# ============================================================

missing_pages = []

for filename in PAGES:
    page_path = PAGES_DIR / filename

    if not page_path.exists():
        missing_pages.append(str(page_path))


if missing_pages:

    st.error("Some Streamlit page files are missing.")

    st.write("Expected pages:")

    for page in missing_pages:
        st.code(page)

    st.info(
        "Make sure all 8 files are inside "
        "src/dashboard/pages/"
    )

    st.stop()


# ============================================================
# STREAMLIT NAVIGATION
# ============================================================

try:

    pages = [
        st.Page(
            str(PAGES_DIR / filename),
            title=title,
        )
        for filename, title in PAGES.items()
    ]

    navigation = st.navigation(
        pages,
        position="sidebar",
    )

    navigation.run()


# ============================================================
# FALLBACK FOR OLDER STREAMLIT
# ============================================================

except AttributeError:

    st.sidebar.title("Nifty 100 Analytics")

    selected_page = st.sidebar.radio(
        "Navigate",
        list(PAGES.values()),
    )

    selected_filename = list(PAGES.keys())[
        list(PAGES.values()).index(selected_page)
    ]

    page_file = PAGES_DIR / selected_filename

    # Execute selected page
    code = page_file.read_text(
        encoding="utf-8"
    )

    exec(
        compile(
            code,
            str(page_file),
            "exec",
        )
    )