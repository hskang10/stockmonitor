from __future__ import annotations

import pandas as pd
import yfinance as yf


def download_history(ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise RuntimeError(f"시장 데이터를 받지 못했습니다: {ticker}")

    # yfinance 버전에 따라 MultiIndex가 반환될 수 있다.
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.get_level_values(-1):
            df = df.xs(ticker, axis=1, level=-1)
        else:
            df.columns = df.columns.get_level_values(0)

    close_name = "Adj Close" if "Adj Close" in df.columns else "Close"
    if close_name not in df.columns:
        raise RuntimeError(f"종가 열을 찾지 못했습니다: {ticker}")

    result = pd.DataFrame(index=df.index)
    result["Close"] = pd.to_numeric(df[close_name], errors="coerce")
    result = result.dropna().sort_index()
    if len(result) < 220:
        raise RuntimeError(f"200일 지표 계산에 필요한 데이터가 부족합니다: {ticker}")
    return result
