from __future__ import annotations

INDEX_CONFIG = {
    "S&P 500": {
        "code": "SPX",
        "ticker": "^GSPC",
        "display_name": "S&P 500",
        "is_kospi": False,
    },
    "Nasdaq-100": {
        "code": "NDX",
        "ticker": "^NDX",
        "display_name": "Nasdaq-100",
        "is_kospi": False,
    },
    "Nifty 50": {
        "code": "NIFTY",
        "ticker": "^NSEI",
        "display_name": "Nifty 50",
        "is_kospi": False,
    },
    "KOSPI": {
        "code": "KOSPI",
        "ticker": "^KS11",
        "display_name": "KOSPI",
        "is_kospi": True,
    },
}

APP_TITLE = "Gems 3.0 글로벌 지수 과매도 진입 대시보드"
SYSTEM_STATUS = "CONDITIONALLY_APPROVED"
SYSTEM_USE = "CASH_DEPLOYMENT_TIMING_ASSISTANT"

LOOKBACK_PERIOD = "5y"
CACHE_TTL_SECONDS = 300

PERCENTILE_WINDOW = 252
MIN_PERCENTILE_SAMPLES = 126
COOLDOWN_DAYS = 10
CYCLE_EXPIRY_DAYS = 120

DEFAULT_TARGET_WEIGHTS = {
    "SPX": 0.30,
    "NDX": 0.30,
    "NIFTY": 0.20,
    "KOSPI": 0.20,
}
