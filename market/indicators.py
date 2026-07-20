from __future__ import annotations

import numpy as np
import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100).clip(0, 100)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for window in (20, 60, 200):
        out[f"MA{window}"] = out["Close"].rolling(window).mean()
        out[f"Disparity{window}"] = out["Close"] / out[f"MA{window}"] * 100

    out["RSI14"] = wilder_rsi(out["Close"], 14)
    out["Drawdown"] = out["Close"] / out["Close"].cummax() - 1
    out["MA200Slope20"] = out["MA200"].pct_change(20) * 100
    return out.dropna().copy()
