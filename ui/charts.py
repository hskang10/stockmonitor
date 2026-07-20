from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def price_chart(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA60"], name="MA60"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], name="MA200"))
    fig.update_layout(title=title, height=420, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def indicator_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Disparity20"], name="20일 이격도"))
    fig.add_trace(go.Scatter(x=df.index, y=df["Disparity60"], name="60일 이격도"))
    fig.add_trace(go.Scatter(x=df.index, y=df["Disparity200"], name="200일 이격도"))
    fig.add_hline(y=100, line_dash="dash")
    fig.update_layout(title="이격도", height=360, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def rsi_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI14"))
    fig.add_hline(y=70, line_dash="dash")
    fig.add_hline(y=30, line_dash="dash")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(title="RSI(14)", height=300, margin=dict(l=10, r=10, t=45, b=10))
    return fig
