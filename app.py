from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf


APP_TITLE = "Global Oversold Dashboard v1 + CPI Macro Engine"
DB_PATH = Path(os.getenv("DASHBOARD_DB_PATH", "global_oversold.db"))
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

INDEXES = {
    "S&P 500": {"ticker": "^GSPC", "code": "SP500"},
    "Nasdaq-100": {"ticker": "^NDX", "code": "NASDAQ100"},
    "Nifty 50": {"ticker": "^NSEI", "code": "NIFTY50"},
    "KOSPI": {"ticker": "^KS11", "code": "KOSPI"},
}

BLS_SERIES = {
    "headline": "CUSR0000SA0",
    "core": "CUSR0000SA0L1E",
}


@dataclass(frozen=True)
class CPIConsensus:
    reference_period: str
    release_time_kst: str
    source: str
    headline_mom: float
    headline_yoy: float
    core_mom: float
    core_yoy: float


@dataclass(frozen=True)
class CPIActual:
    reference_period: str
    headline_mom: float
    headline_yoy: float
    core_mom: float
    core_yoy: float
    fetched_at_utc: str


@dataclass(frozen=True)
class CPIClassification:
    classification: str
    risk_score_change: int
    delay_sessions: int
    macro_multiplier: float
    reason: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cpi_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_period TEXT NOT NULL UNIQUE,
                release_time_kst TEXT NOT NULL,
                consensus_source TEXT NOT NULL,
                consensus_entered_at_utc TEXT NOT NULL,
                consensus_locked INTEGER NOT NULL DEFAULT 0,
                consensus_headline_mom REAL NOT NULL,
                consensus_headline_yoy REAL NOT NULL,
                consensus_core_mom REAL NOT NULL,
                consensus_core_yoy REAL NOT NULL,
                actual_headline_mom REAL,
                actual_headline_yoy REAL,
                actual_core_mom REAL,
                actual_core_yoy REAL,
                surprise_headline_mom REAL,
                surprise_headline_yoy REAL,
                surprise_core_mom REAL,
                surprise_core_yoy REAL,
                classification TEXT,
                risk_score_change INTEGER,
                delay_sessions INTEGER,
                macro_multiplier REAL,
                decision_reason TEXT,
                actual_fetched_at_utc TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                updated_at_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cycle_state (
                index_code TEXT PRIMARY KEY,
                cycle_active INTEGER NOT NULL DEFAULT 0,
                cycle_started_date TEXT,
                last_buy_date TEXT,
                stage INTEGER NOT NULL DEFAULT 0,
                updated_at_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at_utc TEXT NOT NULL,
                index_code TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )


# ---------------------------
# Market data / indicators
# ---------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def download_index_data(ticker: str, period: str = "10y") -> pd.DataFrame:
    raw = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"{ticker} 가격 데이터를 가져오지 못했습니다.")

    # yfinance can return a MultiIndex even for one ticker.
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
        else:
            raise RuntimeError(f"{ticker}: Close 열이 없습니다.")
    else:
        close = raw["Close"]

    df = pd.DataFrame({"Close": pd.to_numeric(close, errors="coerce")})
    df = df.dropna().sort_index()
    if len(df) < 260:
        raise RuntimeError(f"{ticker}: 지표 계산에 필요한 데이터가 부족합니다.")
    return df


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100)
    rsi = rsi.where(avg_gain != 0, 0)
    return rsi


def add_indicators(
    price: pd.DataFrame,
    percentile_window: int = 756,
    percentile_level: float = 0.10,
) -> pd.DataFrame:
    df = price.copy()

    for window in (20, 60, 200):
        df[f"MA{window}"] = df["Close"].rolling(window).mean()
        df[f"Disparity{window}"] = df["Close"] / df[f"MA{window}"] * 100

    df["RSI14"] = wilder_rsi(df["Close"], 14)

    # Rolling lower-tail thresholds prevent a fixed threshold from dominating all regimes.
    min_periods = min(252, percentile_window)
    for column in ("Disparity20", "Disparity60", "Disparity200", "RSI14"):
        df[f"{column}_PCTL"] = (
            df[column]
            .rolling(percentile_window, min_periods=min_periods)
            .quantile(percentile_level)
        )

    conditions = [
        df["Disparity20"] <= df["Disparity20_PCTL"],
        df["Disparity60"] <= df["Disparity60_PCTL"],
        df["Disparity200"] <= df["Disparity200_PCTL"],
        df["RSI14"] <= df["RSI14_PCTL"],
    ]
    df["OversoldScore"] = sum(condition.astype(int) for condition in conditions)

    df["Trend"] = np.select(
        [
            (df["Close"] >= df["MA200"]) & (df["MA60"] >= df["MA200"]),
            df["Close"] >= df["MA200"],
        ],
        ["UPTREND", "MIXED"],
        default="DOWNTREND",
    )
    return df.dropna().copy()


def technical_stage(score: int, trend: str) -> tuple[int, float, str]:
    """
    Returns (stage, percentage of available cash, label).

    Initial implementation:
    score 0-1: no buy
    score 2: reconnaissance 10%
    score 3: main 20%
    score 4: deep oversold 30%

    Downtrend halves deployment and blocks the first reconnaissance stage.
    """
    mapping = {
        0: (0, 0.0, "NO_BUY"),
        1: (0, 0.0, "WATCH"),
        2: (1, 10.0, "RECON"),
        3: (2, 20.0, "MAIN"),
        4: (3, 30.0, "DEEP"),
    }
    stage, pct, label = mapping[int(score)]

    if trend == "DOWNTREND":
        if stage == 1:
            return 0, 0.0, "BLOCKED_BY_DOWNTREND"
        pct *= 0.5
        label += "_HALF_DOWNTREND"

    return stage, pct, label


def get_cycle_state(index_code: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM cycle_state WHERE index_code = ?",
            (index_code,),
        ).fetchone()


def evaluate_cycle(
    index_code: str,
    latest_date: pd.Timestamp,
    score: int,
    proposed_stage: int,
    technical_pct: float,
    cooldown_sessions: int,
    price_index: pd.DatetimeIndex,
) -> dict[str, Any]:
    state = get_cycle_state(index_code)

    cycle_active = bool(state["cycle_active"]) if state else False
    previous_stage = int(state["stage"]) if state else 0
    last_buy_date = pd.Timestamp(state["last_buy_date"]) if state and state["last_buy_date"] else None

    # Score <= 1 resets the oversold cycle.
    if score <= 1:
        return {
            "cycle_active": False,
            "previous_stage": previous_stage,
            "proposed_stage": 0,
            "cooldown_ok": True,
            "stage_upgrade": False,
            "cycle_allowed_pct": 0.0,
            "cycle_reason": "과매도 점수가 1 이하이므로 사이클 종료/대기",
        }

    cooldown_ok = True
    sessions_since_buy = None
    if last_buy_date is not None:
        sessions_since_buy = int((price_index > last_buy_date).sum())
        cooldown_ok = sessions_since_buy >= cooldown_sessions

    stage_upgrade = proposed_stage > previous_stage

    # A deeper stage may buy even inside cooldown; repeated same-stage buys are blocked.
    allowed = proposed_stage > 0 and (not cycle_active or cooldown_ok or stage_upgrade)
    allowed_pct = technical_pct if allowed else 0.0

    if not allowed:
        reason = f"동일 사이클·동일 단계 반복매수 차단 ({sessions_since_buy}/{cooldown_sessions}거래일)"
    elif stage_upgrade and cycle_active:
        reason = "더 깊은 과매도 단계 진입으로 추가 매수 허용"
    elif not cycle_active:
        reason = "신규 과매도 사이클 진입"
    else:
        reason = "쿨다운 충족으로 매수 허용"

    return {
        "cycle_active": cycle_active,
        "previous_stage": previous_stage,
        "proposed_stage": proposed_stage,
        "cooldown_ok": cooldown_ok,
        "sessions_since_buy": sessions_since_buy,
        "stage_upgrade": stage_upgrade,
        "cycle_allowed_pct": allowed_pct,
        "cycle_reason": reason,
    }


def record_buy(index_code: str, market_date: str, stage: int) -> None:
    now = utc_now_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cycle_state (
                index_code, cycle_active, cycle_started_date,
                last_buy_date, stage, updated_at_utc
            ) VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(index_code) DO UPDATE SET
                cycle_active = 1,
                cycle_started_date = COALESCE(cycle_state.cycle_started_date, excluded.cycle_started_date),
                last_buy_date = excluded.last_buy_date,
                stage = MAX(cycle_state.stage, excluded.stage),
                updated_at_utc = excluded.updated_at_utc
            """,
            (index_code, market_date, market_date, stage, now),
        )


def reset_cycle(index_code: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cycle_state (
                index_code, cycle_active, stage, updated_at_utc
            ) VALUES (?, 0, 0, ?)
            ON CONFLICT(index_code) DO UPDATE SET
                cycle_active = 0,
                cycle_started_date = NULL,
                last_buy_date = NULL,
                stage = 0,
                updated_at_utc = excluded.updated_at_utc
            """,
            (index_code, utc_now_iso()),
        )


# ---------------------------
# CPI macro engine
# ---------------------------

def save_consensus(consensus: CPIConsensus) -> None:
    now = utc_now_iso()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT consensus_locked FROM cpi_events WHERE reference_period = ?",
            (consensus.reference_period,),
        ).fetchone()
        if existing and int(existing["consensus_locked"]) == 1:
            raise ValueError("이미 발표 처리되어 잠긴 컨센서스입니다.")

        conn.execute(
            """
            INSERT INTO cpi_events (
                reference_period, release_time_kst, consensus_source,
                consensus_entered_at_utc, consensus_headline_mom,
                consensus_headline_yoy, consensus_core_mom,
                consensus_core_yoy, status, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            ON CONFLICT(reference_period) DO UPDATE SET
                release_time_kst = excluded.release_time_kst,
                consensus_source = excluded.consensus_source,
                consensus_entered_at_utc = excluded.consensus_entered_at_utc,
                consensus_headline_mom = excluded.consensus_headline_mom,
                consensus_headline_yoy = excluded.consensus_headline_yoy,
                consensus_core_mom = excluded.consensus_core_mom,
                consensus_core_yoy = excluded.consensus_core_yoy,
                updated_at_utc = excluded.updated_at_utc
            """,
            (
                consensus.reference_period,
                consensus.release_time_kst,
                consensus.source,
                now,
                consensus.headline_mom,
                consensus.headline_yoy,
                consensus.core_mom,
                consensus.core_yoy,
                now,
            ),
        )


def get_cpi_event(reference_period: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM cpi_events WHERE reference_period = ?",
            (reference_period,),
        ).fetchone()


def get_latest_processed_cpi() -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM cpi_events
            WHERE status = 'PROCESSED'
            ORDER BY reference_period DESC
            LIMIT 1
            """
        ).fetchone()


def list_cpi_events() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT
                reference_period AS 기준월,
                release_time_kst AS 발표시각_KST,
                status AS 상태,
                consensus_core_mom AS Core_MoM_예상,
                actual_core_mom AS Core_MoM_실제,
                surprise_core_mom AS Core_MoM_서프라이즈,
                classification AS 분류,
                risk_score_change AS 위험점수,
                macro_multiplier AS 매크로배수
            FROM cpi_events
            ORDER BY reference_period DESC
            """,
            conn,
        )


def _parse_bls(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    if payload.get("status") != "REQUEST_SUCCEEDED":
        messages = "; ".join(payload.get("message") or [])
        raise RuntimeError(f"BLS API 요청 실패: {messages}")

    result: dict[str, dict[str, float]] = {}
    for series in payload.get("Results", {}).get("series", []):
        values: dict[str, float] = {}
        for item in series.get("data", []):
            period = item.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            key = f"{int(item['year']):04d}-{int(period[1:]):02d}"
            value = item.get("value")

# 숫자가 아닌 값은 건너뛴다.
            if value in (None, "", "-"):
               continue

            try:
               values[key] = float(value)
            except ValueError:
                continue
            result[series["seriesID"]] = values
            return result


def fetch_bls_indexes(reference_period: str, registration_key: str | None) -> dict[str, dict[str, float]]:
    year = int(reference_period[:4])
    payload: dict[str, Any] = {
        "seriesid": list(BLS_SERIES.values()),
        "startyear": str(year - 1),
        "endyear": str(year),
    }
    if registration_key:
        payload["registrationkey"] = registration_key.strip()

    response = requests.post(
        BLS_API_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return _parse_bls(response.json())


def previous_month(period: str) -> str:
    year, month = map(int, period.split("-"))
    return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"


def year_ago(period: str) -> str:
    year, month = map(int, period.split("-"))
    return f"{year - 1:04d}-{month:02d}"


def pct_change(current: float, previous: float) -> float:
    return round((current / previous - 1) * 100, 1)


def calculate_cpi_actual(indexes: dict[str, dict[str, float]], reference_period: str) -> CPIActual:
    prior = previous_month(reference_period)
    prior_year = year_ago(reference_period)

    missing = []
    for name, series_id in BLS_SERIES.items():
        series = indexes.get(series_id, {})
        for period in (reference_period, prior, prior_year):
            if period not in series:
                missing.append(f"{name}:{period}")
    if missing:
        raise ValueError(
            "BLS에서 예상 기준월을 확인하지 못해 처리를 중단합니다. 누락: "
            + ", ".join(missing)
        )

    headline = indexes[BLS_SERIES["headline"]]
    core = indexes[BLS_SERIES["core"]]
    return CPIActual(
        reference_period=reference_period,
        headline_mom=pct_change(headline[reference_period], headline[prior]),
        headline_yoy=pct_change(headline[reference_period], headline[prior_year]),
        core_mom=pct_change(core[reference_period], core[prior]),
        core_yoy=pct_change(core[reference_period], core[prior_year]),
        fetched_at_utc=utc_now_iso(),
    )


def classify_cpi(consensus: CPIConsensus, actual: CPIActual) -> CPIClassification:
    hm = round(actual.headline_mom - consensus.headline_mom, 1)
    cm = round(actual.core_mom - consensus.core_mom, 1)

    if cm >= 0.2:
        return CPIClassification(
            "INFLATION_SHOCK", 3, 1, 0.0,
            "Core CPI MoM이 컨센서스를 0.2%p 이상 상회: 1거래일 지연 및 신규매수 잠금",
        )
    if cm >= 0.1 and hm >= 0.1:
        return CPIClassification(
            "REINFLATION", 2, 1, 0.5,
            "Headline/Core MoM 동반 상회: 1거래일 지연, 기술적 매수비중 50%",
        )
    if cm > 0:
        return CPIClassification(
            "SLIGHTLY_HOT", 1, 0, 0.75,
            "Core CPI가 소폭 상회: 기술적 매수비중 75%",
        )
    if cm <= -0.1 and hm <= 0:
        return CPIClassification(
            "DISINFLATION_POSITIVE", -2, 0, 1.0,
            "Core CPI 하회 및 Headline 상방 충격 없음: 기술적 매수비중 유지",
        )
    return CPIClassification(
        "CPI_NEUTRAL", 0, 0, 1.0,
        "CPI가 대체로 예상 범위: 기술적 매수비중 유지",
    )


def process_cpi(reference_period: str, registration_key: str | None) -> dict[str, Any]:
    row = get_cpi_event(reference_period)
    if row is None:
        raise ValueError("먼저 해당 기준월 컨센서스를 저장하세요.")

    consensus = CPIConsensus(
        reference_period=row["reference_period"],
        release_time_kst=row["release_time_kst"],
        source=row["consensus_source"],
        headline_mom=float(row["consensus_headline_mom"]),
        headline_yoy=float(row["consensus_headline_yoy"]),
        core_mom=float(row["consensus_core_mom"]),
        core_yoy=float(row["consensus_core_yoy"]),
    )
    actual = calculate_cpi_actual(
        fetch_bls_indexes(reference_period, registration_key),
        reference_period,
    )
    classification = classify_cpi(consensus, actual)
    surprises = {
        key: round(getattr(actual, key) - getattr(consensus, key), 1)
        for key in ("headline_mom", "headline_yoy", "core_mom", "core_yoy")
    }

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE cpi_events SET
                consensus_locked = 1,
                actual_headline_mom = ?, actual_headline_yoy = ?,
                actual_core_mom = ?, actual_core_yoy = ?,
                surprise_headline_mom = ?, surprise_headline_yoy = ?,
                surprise_core_mom = ?, surprise_core_yoy = ?,
                classification = ?, risk_score_change = ?,
                delay_sessions = ?, macro_multiplier = ?,
                decision_reason = ?, actual_fetched_at_utc = ?,
                status = 'PROCESSED', updated_at_utc = ?
            WHERE reference_period = ?
            """,
            (
                actual.headline_mom, actual.headline_yoy,
                actual.core_mom, actual.core_yoy,
                surprises["headline_mom"], surprises["headline_yoy"],
                surprises["core_mom"], surprises["core_yoy"],
                classification.classification,
                classification.risk_score_change,
                classification.delay_sessions,
                classification.macro_multiplier,
                classification.reason,
                actual.fetched_at_utc,
                utc_now_iso(),
                reference_period,
            ),
        )

    return {
        "consensus": asdict(consensus),
        "actual": asdict(actual),
        "surprises": surprises,
        "classification": asdict(classification),
    }


# ---------------------------
# Combined decision engine
# ---------------------------

def current_macro_state() -> dict[str, Any]:
    row = get_latest_processed_cpi()
    if row is None:
        return {
            "available": False,
            "reference_period": None,
            "classification": "NO_CPI_DATA",
            "risk_score": None,
            "multiplier": 1.0,
            "delay_sessions": 0,
            "reason": "처리된 CPI가 없어 중립 배수 1.0을 사용합니다.",
        }
    return {
        "available": True,
        "reference_period": row["reference_period"],
        "classification": row["classification"],
        "risk_score": row["risk_score_change"],
        "multiplier": float(row["macro_multiplier"]),
        "delay_sessions": int(row["delay_sessions"] or 0),
        "reason": row["decision_reason"],
    }


def final_decision(
    technical_pct: float,
    cycle_allowed_pct: float,
    macro_multiplier: float,
    delay_sessions: int,
) -> dict[str, Any]:
    base_pct = min(technical_pct, cycle_allowed_pct)
    calculated = round(base_pct * macro_multiplier, 2)
    allowed = calculated > 0 and delay_sessions == 0

    return {
        "technical_buy_pct": round(technical_pct, 2),
        "cycle_allowed_pct": round(cycle_allowed_pct, 2),
        "macro_multiplier": round(macro_multiplier, 2),
        "final_buy_pct": calculated if allowed else 0.0,
        "delay_sessions": delay_sessions,
        "action": "BUY_ALLOWED" if allowed else "HOLD_OR_DELAY",
    }


def build_dashboard(
    percentile_window: int,
    percentile_level: float,
    cooldown_sessions: int,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    macro = current_macro_state()
    rows = []
    histories: dict[str, pd.DataFrame] = {}
    decisions: dict[str, dict[str, Any]] = {}

    for name, cfg in INDEXES.items():
        data = add_indicators(
            download_index_data(cfg["ticker"]),
            percentile_window=percentile_window,
            percentile_level=percentile_level,
        )
        histories[name] = data
        latest = data.iloc[-1]
        score = int(latest["OversoldScore"])
        stage, technical_pct, stage_label = technical_stage(score, str(latest["Trend"]))
        cycle = evaluate_cycle(
            cfg["code"],
            data.index[-1],
            score,
            stage,
            technical_pct,
            cooldown_sessions,
            data.index,
        )
        decision = final_decision(
            technical_pct,
            cycle["cycle_allowed_pct"],
            macro["multiplier"],
            macro["delay_sessions"],
        )
        decisions[name] = {**cycle, **decision, "stage_label": stage_label}

        rows.append(
            {
                "지수": name,
                "기준일": data.index[-1].strftime("%Y-%m-%d"),
                "종가": round(float(latest["Close"]), 2),
                "이격20": round(float(latest["Disparity20"]), 2),
                "이격60": round(float(latest["Disparity60"]), 2),
                "이격200": round(float(latest["Disparity200"]), 2),
                "RSI14": round(float(latest["RSI14"]), 1),
                "과매도점수": score,
                "추세": str(latest["Trend"]),
                "기술단계": stage_label,
                "기술매수%": technical_pct,
                "사이클허용%": cycle["cycle_allowed_pct"],
                "CPI배수": macro["multiplier"],
                "최종매수%": decision["final_buy_pct"],
                "결론": decision["action"],
            }
        )

    return pd.DataFrame(rows), histories, decisions


def log_decision(index_code: str, payload: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO decision_log (created_at_utc, index_code, payload_json)
            VALUES (?, ?, ?)
            """,
            (utc_now_iso(), index_code, json.dumps(payload, ensure_ascii=False, default=str)),
        )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    init_db()

    st.title(APP_TITLE)
    st.caption(
        "S&P 500 · Nasdaq-100 · Nifty 50 · KOSPI의 이격도/RSI 기반 과매도 판단과 "
        "CPI 매크로 배수를 결합합니다. 자동주문은 수행하지 않습니다."
    )

    with st.sidebar:
        st.header("기술 설정")
        percentile_years = st.selectbox("롤링 백분위 표본", [3, 5, 10], index=0)
        percentile_window = percentile_years * 252
        percentile_level = st.slider("과매도 하위 백분위", 0.05, 0.20, 0.10, 0.01)
        cooldown_sessions = st.number_input("동일 단계 쿨다운(거래일)", 1, 30, 10)
        bls_key = st.text_input("BLS 등록키(선택)", type="password")
        bls_key = bls_key or os.getenv("BLS_REGISTRATION_KEY", "")
        if st.button("가격 데이터 캐시 새로고침"):
            download_index_data.clear()
            st.success("가격 데이터 캐시를 초기화했습니다.")

    tab_dashboard, tab_detail, tab_cpi, tab_cycles = st.tabs(
        ["통합 대시보드", "지수 상세", "CPI 엔진", "사이클 관리"]
    )

    with tab_dashboard:
        macro = current_macro_state()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CPI 기준월", macro["reference_period"] or "-")
        m2.metric("CPI 분류", macro["classification"])
        m3.metric("매크로 배수", macro["multiplier"])
        m4.metric("지연 거래일", macro["delay_sessions"])
        st.info(macro["reason"])

        try:
            with st.spinner("4개 지수 데이터와 기술지표를 계산하는 중입니다."):
                summary, histories, decisions = build_dashboard(
                    percentile_window,
                    percentile_level,
                    int(cooldown_sessions),
                )
            st.dataframe(summary, use_container_width=True, hide_index=True)

            st.download_button(
                "통합 결과 CSV 다운로드",
                summary.to_csv(index=False).encode("utf-8-sig"),
                file_name="global_oversold_dashboard.csv",
                mime="text/csv",
            )

            st.subheader("판정 해석")
            selected = st.selectbox("지수 선택", list(INDEXES.keys()), key="dashboard_select")
            d = decisions[selected]
            st.write(
                f"**{selected}**: {d['stage_label']} · "
                f"{d['cycle_reason']} · 최종 결론 **{d['action']} "
                f"{d['final_buy_pct']}%**"
            )

        except Exception as exc:
            st.error(f"시장 데이터 처리 실패: {exc}")

    with tab_detail:
        selected = st.selectbox("상세 지수", list(INDEXES.keys()), key="detail_select")
        try:
            data = add_indicators(
                download_index_data(INDEXES[selected]["ticker"]),
                percentile_window=percentile_window,
                percentile_level=percentile_level,
            )
            latest = data.iloc[-1]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("종가", f"{latest['Close']:.2f}")
            c2.metric("RSI14", f"{latest['RSI14']:.1f}")
            c3.metric("과매도점수", int(latest["OversoldScore"]))
            c4.metric("추세", latest["Trend"])

            chart_cols = [
                "Close", "MA20", "MA60", "MA200",
            ]
            st.line_chart(data[chart_cols].tail(504))

            st.subheader("최근 지표")
            recent_cols = [
                "Close", "MA20", "MA60", "MA200",
                "Disparity20", "Disparity60", "Disparity200",
                "RSI14", "OversoldScore", "Trend",
            ]
            st.dataframe(data[recent_cols].tail(30).sort_index(ascending=False))

        except Exception as exc:
            st.error(str(exc))

    with tab_cpi:
        input_tab, process_tab, history_tab = st.tabs(
            ["컨센서스 입력", "실제값 조회", "CPI 이력"]
        )

        with input_tab:
            today = date.today()
            prior_month = today.month - 1 or 12
            prior_year = today.year if today.month > 1 else today.year - 1
            default_period = f"{prior_year:04d}-{prior_month:02d}"

            reference_period = st.text_input("CPI 기준월(YYYY-MM)", value=default_period)
            release_date = st.date_input("발표일")
            release_time = st.time_input(
                "발표시각(KST)",
                value=datetime.strptime("21:30", "%H:%M").time(),
            )
            source = st.text_input("컨센서스 출처")

            c1, c2, c3, c4 = st.columns(4)
            hm = c1.number_input("Headline MoM 예상(%)", value=0.2, step=0.1, format="%.1f")
            hy = c2.number_input("Headline YoY 예상(%)", value=2.7, step=0.1, format="%.1f")
            cm = c3.number_input("Core MoM 예상(%)", value=0.2, step=0.1, format="%.1f")
            cy = c4.number_input("Core YoY 예상(%)", value=2.9, step=0.1, format="%.1f")

            if st.button("CPI 컨센서스 저장", type="primary"):
                try:
                    datetime.strptime(reference_period, "%Y-%m")
                    if not source.strip():
                        raise ValueError("컨센서스 출처를 입력하세요.")
                    save_consensus(
                        CPIConsensus(
                            reference_period,
                            datetime.combine(release_date, release_time).isoformat(timespec="minutes"),
                            source.strip(),
                            float(hm), float(hy), float(cm), float(cy),
                        )
                    )
                    st.success("저장했습니다. 실제값 처리 후 컨센서스가 잠깁니다.")
                except Exception as exc:
                    st.error(str(exc))

        with process_tab:
            events = list_cpi_events()
            if events.empty:
                st.info("먼저 컨센서스를 입력하세요.")
            else:
                period = st.selectbox("처리할 기준월", events["기준월"].tolist())
                if st.button("BLS 실제값 조회 및 CPI 판정", type="primary"):
                    try:
                        result = process_cpi(period, bls_key or None)
                        st.success("CPI 처리 완료")
                        st.json(result)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

                row = get_cpi_event(period)
                if row:
                    values = pd.DataFrame(
                        [
                            ["Headline MoM", row["consensus_headline_mom"], row["actual_headline_mom"], row["surprise_headline_mom"]],
                            ["Headline YoY", row["consensus_headline_yoy"], row["actual_headline_yoy"], row["surprise_headline_yoy"]],
                            ["Core MoM", row["consensus_core_mom"], row["actual_core_mom"], row["surprise_core_mom"]],
                            ["Core YoY", row["consensus_core_yoy"], row["actual_core_yoy"], row["surprise_core_yoy"]],
                        ],
                        columns=["항목", "컨센서스", "실제", "서프라이즈"],
                    )
                    st.dataframe(values, hide_index=True, use_container_width=True)
                    if row["decision_reason"]:
                        st.info(row["decision_reason"])

        with history_tab:
            cpi_history = list_cpi_events()
            st.dataframe(cpi_history, hide_index=True, use_container_width=True)

    with tab_cycles:
        st.subheader("사이클 상태")
        with get_conn() as conn:
            cycle_df = pd.read_sql_query(
                "SELECT * FROM cycle_state ORDER BY index_code",
                conn,
            )
        st.dataframe(cycle_df, hide_index=True, use_container_width=True)

        selected_code = st.selectbox(
            "관리할 지수",
            [cfg["code"] for cfg in INDEXES.values()],
        )
        c1, c2 = st.columns(2)

        with c1:
            stage = st.number_input("체결 단계", 1, 3, 1)
            market_date = st.date_input("체결 기준일", key="cycle_market_date")
            if st.button("수동 매수 체결 기록"):
                record_buy(selected_code, market_date.isoformat(), int(stage))
                st.success("사이클 체결 기록을 저장했습니다.")
                st.rerun()

        with c2:
            st.write("과매도 사이클이 종료되었거나 기록을 초기화할 때 사용합니다.")
            if st.button("선택 지수 사이클 초기화"):
                reset_cycle(selected_code)
                st.success("사이클을 초기화했습니다.")
                st.rerun()


if __name__ == "__main__":
    main()
