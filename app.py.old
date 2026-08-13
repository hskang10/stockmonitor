from __future__ import annotations

import streamlit as st

from storage.database import init_db
from ui.dashboard import render_dashboard

st.set_page_config(
    page_title="Global Oversold Dashboard",
    page_icon="📉",
    layout="wide",
)

init_db()
render_dashboard()
