from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        .main-title {font-size: 1.85rem; font-weight: 850; letter-spacing: -0.04em;}
        .subtitle {opacity: .72; margin-top: -.4rem;}
        .decision-box {
            border-radius: 14px; padding: 16px; border: 1px solid rgba(128,128,128,.25);
            box-shadow: 0 4px 16px rgba(0,0,0,.06); min-height: 278px;
        }
        .score-0, .score-1 {background: rgba(128,128,128,.07);}
        .score-2 {background: rgba(241,196,15,.13);}
        .score-3 {background: rgba(230,126,34,.14);}
        .score-4 {background: rgba(231,76,60,.14);}
        .trend-up {border-left: 5px solid #2ecc71;}
        .trend-down {border-left: 5px solid #e74c3c;}
        .action-pill {
            display:inline-block; padding:6px 10px; border-radius:999px;
            font-weight:800; font-size:.83rem; margin:8px 0;
        }
        .muted {opacity:.68; font-size:.82rem;}
        .big-action {font-size:1.2rem; font-weight:900; margin-top:8px;}
        .score-dots {letter-spacing:.18rem; font-size:1.2rem;}
        .kpi-label {opacity:.7; font-size:.78rem;}
        .kpi-value {font-size:1.08rem; font-weight:800;}
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18); padding: 10px; border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
