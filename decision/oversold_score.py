from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import pandas as pd


@dataclass(frozen=True)
class TechnicalDecision:
    close: float
    disparity20: float
    disparity60: float
    disparity200: float
    rsi14: float
    drawdown_pct: float
    trend: str
    score: int
    stage: str
    technical_buy_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def evaluate_latest(df: pd.DataFrame) -> TechnicalDecision:
    row = df.iloc[-1]

    # 100점: 이격도 70점 + RSI 25점 + 낙폭 5점
    score_d20 = _clamp((100 - row["Disparity20"]) / 8 * 25, 0, 25)
    score_d60 = _clamp((100 - row["Disparity60"]) / 12 * 20, 0, 20)
    score_d200 = _clamp((100 - row["Disparity200"]) / 20 * 25, 0, 25)
    score_rsi = _clamp((50 - row["RSI14"]) / 25 * 25, 0, 25)
    score_dd = _clamp((-row["Drawdown"] * 100) / 20 * 5, 0, 5)
    raw = score_d20 + score_d60 + score_d200 + score_rsi + score_dd

    if row["Close"] >= row["MA200"] and row["MA200Slope20"] >= 0:
        trend = "장기 상승"
        trend_factor = 1.00
    elif row["Close"] >= row["MA200"]:
        trend = "상승 둔화"
        trend_factor = 0.90
    elif row["MA200Slope20"] >= 0:
        trend = "200일선 하회"
        trend_factor = 0.80
    else:
        trend = "장기 하락"
        trend_factor = 0.65

    score = int(round(_clamp(raw * trend_factor, 0, 100)))
    if score >= 80:
        stage, ratio = "3차 진입", 0.50
    elif score >= 65:
        stage, ratio = "2차 진입", 0.30
    elif score >= 50:
        stage, ratio = "1차 진입", 0.10
    else:
        stage, ratio = "관망", 0.00

    return TechnicalDecision(
        close=float(row["Close"]),
        disparity20=float(row["Disparity20"]),
        disparity60=float(row["Disparity60"]),
        disparity200=float(row["Disparity200"]),
        rsi14=float(row["RSI14"]),
        drawdown_pct=float(row["Drawdown"] * 100),
        trend=trend,
        score=score,
        stage=stage,
        technical_buy_ratio=ratio,
    )
