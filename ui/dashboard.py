from __future__ import annotations

import pandas as pd
import streamlit as st

from config.constants import INDEXES
from decision.decision_engine import combine
from decision.oversold_score import evaluate_latest
from market.downloader import download_history
from market.indicators import add_indicators
from ui.charts import indicator_chart, price_chart, rsi_chart
from ui.macro_panel import render_macro_panel


@st.cache_data(ttl=3600, show_spinner=False)
def load_market(ticker: str) -> pd.DataFrame:
    return add_indicators(download_history(ticker))


def render_dashboard() -> None:
    st.title("Global Oversold Dashboard")
    st.caption("이격도·RSI·장기추세와 CPI 서프라이즈를 결합한 단계적 현금 투입 대시보드")

    with st.sidebar:
        st.header("설정")
        selected_name = st.selectbox("지수", list(INDEXES))
        ticker = INDEXES[selected_name]
        st.caption(f"Ticker: {ticker}")
        if st.button("시장 데이터 새로고침", width="stretch"):
            load_market.clear()

    try:
        with st.spinner("시장 데이터를 계산하는 중입니다..."):
            df = load_market(ticker)
            technical = evaluate_latest(df)
    except Exception as exc:
        st.error(str(exc))
        return

    st.subheader(f"{selected_name} 기술 신호")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("종가", f"{technical.close:,.2f}")
    c2.metric("20일 이격도", f"{technical.disparity20:.2f}%")
    c3.metric("200일 이격도", f"{technical.disparity200:.2f}%")
    c4.metric("RSI14", f"{technical.rsi14:.1f}")
    c5.metric("과매도 점수", f"{technical.score}/100")

    st.info(
        f"추세: {technical.trend} · 단계: {technical.stage} · "
        f"기술 기준 현금 투입률: {technical.technical_buy_ratio:.0%}"
    )

    st.plotly_chart(price_chart(df.tail(500), f"{selected_name} 가격과 이동평균"), width="stretch")
    left, right = st.columns(2)
    left.plotly_chart(indicator_chart(df.tail(500)), width="stretch")
    right.plotly_chart(rsi_chart(df.tail(500)), width="stretch")

    st.divider()
    cpi = render_macro_panel()

    st.divider()
    st.subheader("통합 의사결정")
    final = combine(technical, cpi)
    a, b, c, d = st.columns(4)
    a.metric("기술 투입률", f"{final.technical_buy_ratio:.0%}")
    b.metric("CPI 배수", f"{final.macro_multiplier:.2f}x")
    c.metric("최종 투입률", f"{final.final_buy_ratio:.0%}")
    d.metric("대기 세션", str(final.delay_sessions))
    st.success(final.action)

    with st.expander("최근 계산 데이터"):
        st.dataframe(df.tail(30), width="stretch")
