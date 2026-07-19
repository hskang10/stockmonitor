from __future__ import annotations

import numpy as np
import pandas as pd

from config import MIN_PERCENTILE_SAMPLES, PERCENTILE_WINDOW


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder 방식 RSI. pandas ewm(alpha=1/period, adjust=False) 사용."""
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    both_zero = (avg_gain == 0) & (avg_loss == 0)
    only_gain = (avg_gain > 0) & (avg_loss == 0)
    only_loss = (avg_gain == 0) & (avg_loss > 0)

    rsi = rsi.mask(both_zero, 50.0)
    rsi = rsi.mask(only_gain, 100.0)
    rsi = rsi.mask(only_loss, 0.0)
    return rsi


def rolling_percentile_rank(series: pd.Series, window: int = 252) -> pd.Series:
    """
    당일 값을 과거 분포에 넣지 않기 위해 shift(1)된 창과 당일 값을 비교한다.
    0에 가까울수록 최근 1년 분포에서 극단적으로 낮은 값이다.
    """
    shifted = series.shift(1)

    def rank_last(values: np.ndarray) -> float:
        current = values[-1]
        history = values[:-1]
        valid = history[~np.isnan(history)]
        if np.isnan(current) or len(valid) < MIN_PERCENTILE_SAMPLES:
            return np.nan
        return float((valid <= current).mean() * 100)

    joined = pd.concat([shifted, series], axis=1)
    return joined.iloc[:, 1].rolling(window + 1, min_periods=MIN_PERCENTILE_SAMPLES + 1).apply(
        lambda arr: rank_last(arr), raw=True
    )


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"].astype(float)

    out["Ret"] = close.pct_change()
    out["MA5"] = close.rolling(5, min_periods=5).mean()
    out["MA20"] = close.rolling(20, min_periods=20).mean()
    out["MA60"] = close.rolling(60, min_periods=60).mean()
    out["MA200"] = close.rolling(200, min_periods=200).mean()

    out["Disparity20"] = close / out["MA20"] * 100
    out["Disparity60"] = close / out["MA60"] * 100
    out["Disparity200"] = close / out["MA200"] * 100
    out["RSI14"] = wilder_rsi(close, 14)

    # 미래정보 방지: 당일 제외 이전 252거래일
    out["D20_Q20"] = out["Disparity20"].shift(1).rolling(
        PERCENTILE_WINDOW, min_periods=MIN_PERCENTILE_SAMPLES
    ).quantile(0.20)
    out["D60_Q20"] = out["Disparity60"].shift(1).rolling(
        PERCENTILE_WINDOW, min_periods=MIN_PERCENTILE_SAMPLES
    ).quantile(0.20)
    out["D200_Q25"] = out["Disparity200"].shift(1).rolling(
        PERCENTILE_WINDOW, min_periods=MIN_PERCENTILE_SAMPLES
    ).quantile(0.25)

    out["P20"] = (out["Disparity20"] <= out["D20_Q20"]).astype("Int64")
    out["P60"] = (out["Disparity60"] <= out["D60_Q20"]).astype("Int64")
    out["P200"] = (out["Disparity200"] <= out["D200_Q25"]).astype("Int64")
    out["PRSI"] = (out["RSI14"] <= 35).astype("Int64")
    out["OversoldScore"] = (
        out[["P20", "P60", "P200", "PRSI"]].fillna(0).sum(axis=1).astype(int)
    )

    out["MA200_Slope20"] = out["MA200"] / out["MA200"].shift(20) - 1
    out["TrendState"] = np.where(
        out["MA200_Slope20"].isna(),
        "INSUFFICIENT_DATA",
        np.where(out["MA200_Slope20"] > 0, "TREND_UP", "TREND_DOWN"),
    )

    out["ReversalConfirmed"] = (
        (out["RSI14"] > out["RSI14"].shift(1))
        & (close > out["MA5"])
        & (close.shift(1) <= out["MA5"].shift(1))
        & (close > close.shift(1))
    )

    out["PctRank20"] = rolling_percentile_rank(out["Disparity20"])
    out["PctRank60"] = rolling_percentile_rank(out["Disparity60"])
    out["PctRank200"] = rolling_percentile_rank(out["Disparity200"])
    out["PctRankRSI"] = rolling_percentile_rank(out["RSI14"])
    out["CompositePercentile"] = out[
        ["PctRank20", "PctRank60", "PctRank200", "PctRankRSI"]
    ].mean(axis=1, skipna=True)

    return out
