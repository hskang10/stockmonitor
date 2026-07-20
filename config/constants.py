from __future__ import annotations

INDEXES = {
    "S&P 500": "^GSPC",
    "Nasdaq-100": "^NDX",
    "Nifty 50": "^NSEI",
    "KOSPI": "^KS11",
}

BLS_SERIES = {
    "headline": "CUSR0000SA0",
    "core": "CUSR0000SA0L1E",
}

DEFAULT_LOOKBACK = "5y"
DEFAULT_INTERVAL = "1d"

# 기술 신호별 기본 현금 투입률
STAGE_BUY_RATIOS = {
    "관망": 0.00,
    "1차 진입": 0.10,
    "2차 진입": 0.30,
    "3차 진입": 0.50,
}
