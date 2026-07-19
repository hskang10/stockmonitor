from __future__ import annotations

import html
from typing import Any

import plotly.graph_objects as go
import streamlit as st


ACTION_COLORS = {
    "RECON": "#d4a017",
    "MAIN_ENTRY": "#e67e22",
    "EXTREME_ENTRY": "#c0392b",
    "EXTREME_RECON": "#8e44ad",
    "WAIT_REVERSAL": "#7f8c8d",
    "NO_SIGNAL": "#7f8c8d",
    "COOLDOWN": "#5d6d7e",
    "SAME_LEVEL_LOCK": "#5d6d7e",
    "CYCLE_LIMIT": "#34495e",
    "CASH_LOCK": "#34495e",
    "DATA_WARNING": "#8e44ad",
    "DATA_INVALID": "#6c1b1b",
    "AUTOTRADE_DISABLED": "#2c3e50",
}


def score_dots(score: int) -> str:
    return "●" * score + "○" * (4 - score)


def decision_card(m: dict) -> None:
    score = int(m["OversoldScore"])
    trend = m["TrendState"]
    action = m["ActionCode"]
    action_color = ACTION_COLORS.get(action, "#7f8c8d")
    reason = html.escape(str(m["Reason"]))
    name = html.escape(str(m["DisplayName"]))

    st.markdown(
        f"""
        <div class="decision-box score-{score} {'trend-up' if trend == 'TREND_UP' else 'trend-down'}">
            <div style="display:flex;justify-content:space-between;align-items:start;">
                <div>
                    <div style="font-size:1.08rem;font-weight:900;">{name}</div>
                    <div class="muted">{m['Date']} · {m['Close']:,.2f} · {m['Ret']:+.2f}%</div>
                </div>
                <div style="font-weight:900;">{score}/4</div>
            </div>
            <div class="score-dots">{score_dots(score)}</div>
            <div class="action-pill" style="background:{action_color};color:white;">{action}</div>
            <div class="big-action">가용 현금 {m['RecommendedCashPct']:.0f}%</div>
            <div style="display:flex;justify-content:space-between;margin-top:12px;">
                <div><div class="kpi-label">장기 추세</div><div class="kpi-value">{'상승' if trend == 'TREND_UP' else '하락'}</div></div>
                <div><div class="kpi-label">사이클 누적</div><div class="kpi-value">{m['CycleInvestedPct']:.0f}%</div></div>
                <div><div class="kpi-label">데이터</div><div class="kpi-value">{m['DataStatus'].replace('DATA_', '')}</div></div>
            </div>
            <div class="muted" style="margin-top:12px;line-height:1.45;"><b>근거:</b> {reason}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cap = max(float(m.get("CycleLimitPct", 0)), 1.0)
    invested = min(float(m.get("CycleInvestedPct", 0)), cap)
    st.progress(invested / cap, text=f"사이클 사용 {invested:.0f}% / {cap:.0f}%")


def sparkline(series, title: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=series, mode="lines", hovertemplate="%{y:,.2f}<extra></extra>"))
    fig.update_layout(
        height=130,
        margin=dict(l=5, r=5, t=30, b=5),
        title=dict(text=title, font=dict(size=12)),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def heatmap_chart(rows: list[dict]):
    names = [r["DisplayName"] for r in rows]
    z = [[r["PctRank20"], r["PctRank60"], r["PctRank200"], r["PctRankRSI"]] for r in rows]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["20일 이격도", "60일 이격도", "200일 이격도", "RSI14"],
            y=names,
            zmin=0,
            zmax=100,
            reversescale=True,
            colorscale="RdYlGn",
            colorbar=dict(title="백분위"),
            hovertemplate="%{y}<br>%{x}: %{z:.1f}백분위<extra></extra>",
        )
    )
    fig.update_layout(height=310, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
