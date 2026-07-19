from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        if len(df.columns.levels) >= 2:
            df.columns = [
                col[0] if col[0] in {"Open", "High", "Low", "Close", "Adj Close", "Volume"} else "_".join(
                    str(x) for x in col if x
                )
                for col in df.columns
            ]
    return df


def fetch_market_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    Ticker.history를 우선 사용한다.
    실패 시 yf.download로 한 번 더 시도한다.
    """
    errors: list[str] = []

    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=False, actions=False)
    except Exception as exc:
        errors.append(f"Ticker.history: {exc}")
        df = pd.DataFrame()

    if df.empty:
        try:
            df = yf.download(
                ticker,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception as exc:
            errors.append(f"yf.download: {exc}")
            df = pd.DataFrame()

    if df.empty:
        raise RuntimeError("시장 데이터를 가져오지 못했습니다. " + " | ".join(errors))

    df = _flatten_columns(df.copy())
    if "Close" not in df.columns:
        raise RuntimeError(f"Close 열이 없습니다. 현재 열: {list(df.columns)}")

    df.index = pd.to_datetime(df.index)
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)

    keep = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in df.columns]
    df = df[keep].copy()
    df.index.name = "Date"
    return df
