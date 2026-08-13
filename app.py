
import os
from datetime import date, timedelta
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf

# ============================================================
# PAGE
# ============================================================
st.set_page_config(
    page_title="Investment Decision Cockpit",
    page_icon="🎯",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.15rem; padding-bottom: 2rem; max-width: 1550px;}
    div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.18); border-radius:12px; padding:9px 12px;}
    /* Compact metric values: long Market regime text should wrap instead of clipping. */
    div[data-testid="stMetricValue"] {
        font-size:1.05rem !important;
        line-height:1.22 !important;
        white-space:normal !important;
        overflow-wrap:anywhere !important;
        word-break:keep-all !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size:inherit !important;
        line-height:inherit !important;
        white-space:normal !important;
    }
    .section-label {font-size:.80rem; font-weight:750; letter-spacing:.05em; color:#7a7a7a; margin:.55rem 0 .35rem 0; text-transform:uppercase;}
    .status-card {border:1px solid rgba(128,128,128,.20); border-left:5px solid #8a8a8a; border-radius:13px; padding:10px 12px; min-height:86px; background:rgba(128,128,128,.035);}
    .status-label {font-size:.73rem; font-weight:720; color:#777; margin-bottom:4px;}
    .status-value {font-size:1.02rem; line-height:1.22; font-weight:800; word-break:keep-all;}
    .status-sub {font-size:.72rem; color:#777; margin-top:4px;}
    .status-good {border-left-color:#2474d2; background:rgba(36,116,210,.08);} .status-good .status-value {color:#1f63b7;}
    .status-warn {border-left-color:#e49318; background:rgba(228,147,24,.09);} .status-warn .status-value {color:#a96600;}
    .status-bad {border-left-color:#d94b4b; background:rgba(217,75,75,.08);} .status-bad .status-value {color:#b73535;}
    .status-neutral {border-left-color:#8b8b8b; background:rgba(128,128,128,.04);} .status-neutral .status-value {color:#666;}

    .asset-card {border:1px solid rgba(128,128,128,.20); border-left:5px solid #8a8a8a; border-radius:15px; padding:14px 15px 12px 15px; min-height:190px; background:rgba(128,128,128,.025); margin-bottom:8px;}
    .asset-card.card-good {border-left-color:#2474d2; background:rgba(36,116,210,.055);}
    .asset-card.card-mid {border-left-color:#e49318; background:rgba(228,147,24,.055);}
    .asset-card.card-watch {border-left-color:#d9822b; background:rgba(217,130,43,.045);}
    .asset-card.card-wait {border-left-color:#d94b4b; background:rgba(217,75,75,.045);}
    .asset-title {font-size:1rem; font-weight:780; margin-bottom:1px;}
    .asset-ticker {font-size:.76rem; color:#888; margin-bottom:8px;}
    .action {display:inline-block; padding:4px 9px; border-radius:999px; font-size:.84rem; font-weight:780; margin-bottom:7px;}
    .action-good {background:#dbeafe; color:#1f5eaa;} .action-mid {background:#fff0cc; color:#966000;}
    .action-watch {background:#ffead7; color:#9a4f08;} .action-wait {background:#fde0e0; color:#ad3030;}
    .score-line {font-size:.82rem; color:#666; margin:3px 0;} .reason {font-size:.79rem; line-height:1.42; color:#707070; margin-top:6px;}
    .summary-box {border:1px solid rgba(128,128,128,.18); border-radius:13px; padding:12px 14px; background:rgba(128,128,128,.025); min-height:92px;}
    .summary-big {font-size:1.15rem; font-weight:780; margin-bottom:4px;} .summary-small {font-size:.82rem; color:#777; line-height:1.4;}
    </style>
    """, unsafe_allow_html=True,
)

st.title("🎯 Investment Decision Cockpit")
st.caption("첫 화면에서 7개 자산의 진입환경을 확인하고, 필요할 때만 거시·가격·컨센서스 상세 화면으로 내려갑니다.")

# ============================================================
# CONFIG
# ============================================================
FRED_SERIES = {
    # Inflation
    "CPI": "CPIAUCSL",
    "Core CPI": "CPILFESL",
    "PPI Final Demand": "PPIFID",
    "Core PPI": "PPICOR",
    "PCE": "PCEPI",
    "Core PCE": "PCEPILFE",

    # Employment
    "Nonfarm Payrolls": "PAYEMS",
    "Unemployment Rate": "UNRATE",
    "Average Hourly Earnings": "CES0500000003",
    "Initial Claims": "ICSA",

    # Growth / demand
    "Real Retail Sales": "RRSFS",
    "Industrial Production": "INDPRO",

    # Rates / credit
    "Fed Funds": "DFF",
    "US 2Y": "DGS2",
    "US 10Y": "DGS10",
    "US 30Y": "DGS30",
    "US 10Y Real Yield": "DFII10",
    "10Y-2Y Spread": "T10Y2Y",
    "HY OAS": "BAMLH0A0HYM2",
}

DEFAULT_ASSETS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Nifty 50": "^NSEI",
    "KOSPI": "^KS11",
    "US 10Y Treasury ETF (proxy)": "IEF",
    "US Long Treasury ETF (proxy)": "TLT",
    "Gold ETF (proxy)": "GLD",
}

ASSET_GROUP = {
    "S&P 500": "Equity",
    "Nasdaq 100": "Equity",
    "Nifty 50": "Equity",
    "KOSPI": "Equity",
    "US 10Y Treasury ETF (proxy)": "Bond",
    "US Long Treasury ETF (proxy)": "Bond",
    "Gold ETF (proxy)": "Gold",
}

# ============================================================
# HELPERS
# ============================================================
def fred_key():
    # 1) Streamlit secrets
    try:
        k = st.secrets.get("FRED_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    # 2) environment
    return os.getenv("FRED_API_KEY", "")


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def load_fred_series(series_id: str, api_key: str, start_date: str) -> pd.Series:
    if not api_key:
        return pd.Series(dtype=float)

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    obs = r.json().get("observations", [])

    if not obs:
        return pd.Series(dtype=float)

    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    s = df.dropna(subset=["value"]).set_index("date")["value"].sort_index()
    s.name = series_id
    return s


@st.cache_data(ttl=60 * 30, show_spinner=False)
def load_market_prices(tickers: tuple, period="3y") -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    raw = yf.download(
        list(tickers),
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    if raw.empty:
        return pd.DataFrame()

    if len(tickers) == 1:
        if "Close" in raw.columns:
            close = raw[["Close"]].copy()
            close.columns = [tickers[0]]
            return close.dropna(how="all")
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex) and "Close" in raw.columns.get_level_values(0):
        close = raw["Close"].copy()
    elif isinstance(raw.columns, pd.MultiIndex) and "Close" in raw.columns.get_level_values(1):
        close = raw.xs("Close", axis=1, level=1).copy()
    else:
        return pd.DataFrame()

    return close.dropna(how="all")


def pct_change(s: pd.Series, periods: int) -> pd.Series:
    return s.pct_change(periods=periods) * 100


def annualized_change(s: pd.Series, months: int) -> pd.Series:
    # For monthly index-level series: rolling annualized compounded change
    return ((s / s.shift(months)) ** (12 / months) - 1) * 100


def yoy_monthly(s: pd.Series) -> pd.Series:
    return pct_change(s, 12)


def mom_monthly(s: pd.Series) -> pd.Series:
    return pct_change(s, 1)


def latest_valid(s: pd.Series):
    if s is None or len(s.dropna()) == 0:
        return np.nan
    return float(s.dropna().iloc[-1])


def value_months_ago(s: pd.Series, months: int):
    x = s.dropna()
    if len(x) <= months:
        return np.nan
    return float(x.iloc[-1 - months])


def slope_label(now, past, inverse=False, tol=0.05):
    if pd.isna(now) or pd.isna(past):
        return "N/A"
    diff = now - past
    if abs(diff) <= tol:
        return "→"
    rising = diff > 0
    if inverse:
        rising = not rising
    return "↑" if rising else "↓"


def rsi_wilder(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def asset_metrics(close: pd.Series) -> dict:
    s = close.dropna().copy()
    if len(s) < 70:
        return {}

    ma20 = s.rolling(20).mean()
    ma60 = s.rolling(60).mean()
    ma200 = s.rolling(200).mean()
    rsi = rsi_wilder(s, 14)

    ret_1m = (s.iloc[-1] / s.iloc[-22] - 1) * 100 if len(s) >= 22 else np.nan
    ret_3m = (s.iloc[-1] / s.iloc[-66] - 1) * 100 if len(s) >= 66 else np.nan
    ret_6m = (s.iloc[-1] / s.iloc[-132] - 1) * 100 if len(s) >= 132 else np.nan
    ret_1y = (s.iloc[-1] / s.iloc[-253] - 1) * 100 if len(s) >= 253 else np.nan

    d20 = (s / ma20 - 1) * 100
    d60 = (s / ma60 - 1) * 100
    d200 = (s / ma200 - 1) * 100

    # 252-trading-day percentile thresholds, requiring >=126 obs
    hist = pd.DataFrame({"D20": d20, "D60": d60, "D200": d200, "RSI": rsi}).dropna()
    hist = hist.tail(252)

    score = np.nan
    q20_d20 = q20_d60 = q25_d200 = np.nan
    if len(hist) >= 126:
        q20_d20 = hist["D20"].quantile(0.20)
        q20_d60 = hist["D60"].quantile(0.20)
        q25_d200 = hist["D200"].quantile(0.25)
        score = int(
            (hist["D20"].iloc[-1] <= q20_d20)
            + (hist["D60"].iloc[-1] <= q20_d60)
            + (hist["D200"].iloc[-1] <= q25_d200)
            + (hist["RSI"].iloc[-1] <= 35)
        )

    ma200_slope20 = np.nan
    if len(ma200.dropna()) >= 21:
        ma200_slope20 = ma200.dropna().iloc[-1] - ma200.dropna().iloc[-21]

    trend = "상승" if pd.notna(ma200_slope20) and ma200_slope20 > 0 else "하락/미확인"

    # Drawdown from 1Y high
    one_year = s.tail(252)
    drawdown_1y = (s.iloc[-1] / one_year.max() - 1) * 100 if len(one_year) else np.nan

    return {
        "Price": s.iloc[-1],
        "1M %": ret_1m,
        "3M %": ret_3m,
        "6M %": ret_6m,
        "1Y %": ret_1y,
        "RSI14": rsi.iloc[-1],
        "D20 %": d20.iloc[-1],
        "D60 %": d60.iloc[-1],
        "D200 %": d200.iloc[-1] if len(d200.dropna()) else np.nan,
        "1Y Drawdown %": drawdown_1y,
        "Oversold Score": score,
        "MA200 Trend": trend,
    }


def classify_inflation(core_cpi_yoy, core_cpi_3m, core_pce_yoy):
    vals = [core_cpi_yoy, core_cpi_3m, core_pce_yoy]
    if any(pd.isna(x) for x in vals):
        return "확인 필요", 0

    # directional score using current values vs recent history is handled outside;
    # this level is intentionally conservative.
    if core_cpi_3m > core_cpi_yoy + 0.5:
        return "재가속 경계", -1
    if core_cpi_3m < core_cpi_yoy - 0.3:
        return "둔화 우세", 1
    return "혼조/안정", 0


def make_macro_summary(m):
    """
    Returns category labels and a macro risk score.
    score > 0 = more risk-on friendly, <0 = defensive
    This is a heuristic, not a forecast.
    """
    out = {}
    score = 0

    # Inflation
    if all(pd.notna(m.get(k)) for k in ["core_cpi_yoy", "core_cpi_yoy_3mago", "core_cpi_3m_ann"]):
        if m["core_cpi_yoy"] < m["core_cpi_yoy_3mago"] and m["core_cpi_3m_ann"] <= m["core_cpi_yoy"] + 0.3:
            out["Inflation"] = "둔화"
            score += 1
        elif m["core_cpi_yoy"] > m["core_cpi_yoy_3mago"] and m["core_cpi_3m_ann"] > m["core_cpi_yoy"]:
            out["Inflation"] = "재가속"
            score -= 1
        else:
            out["Inflation"] = "혼조"
    else:
        out["Inflation"] = "확인 필요"

    # Employment
    if all(pd.notna(m.get(k)) for k in ["unrate", "unrate_3mago", "payroll_3m_avg", "payroll_6m_avg"]):
        if (m["unrate"] - m["unrate_3mago"] > 0.3) and (m["payroll_3m_avg"] < m["payroll_6m_avg"] * 0.75):
            out["Employment"] = "빠른 악화"
            score -= 2
        elif (m["unrate"] >= m["unrate_3mago"]) and (m["payroll_3m_avg"] <= m["payroll_6m_avg"]):
            out["Employment"] = "완만한 냉각"
            score += 0
        else:
            out["Employment"] = "견조"
            score += 1
    else:
        out["Employment"] = "확인 필요"

    # Growth
    if all(pd.notna(m.get(k)) for k in ["real_retail_yoy", "real_retail_yoy_3mago", "indpro_yoy", "indpro_yoy_3mago"]):
        diffs = [
            m["real_retail_yoy"] - m["real_retail_yoy_3mago"],
            m["indpro_yoy"] - m["indpro_yoy_3mago"],
        ]
        if np.mean(diffs) > 0.3:
            out["Growth"] = "개선"
            score += 1
        elif np.mean(diffs) < -0.3:
            out["Growth"] = "둔화"
            score -= 1
        else:
            out["Growth"] = "횡보"
    else:
        out["Growth"] = "확인 필요"

    # Rates / credit
    if all(pd.notna(m.get(k)) for k in ["us10y", "us10y_20dago", "hy_oas", "hy_oas_20dago"]):
        if (m["us10y"] < m["us10y_20dago"]) and (m["hy_oas"] <= m["hy_oas_20dago"] + 0.15):
            out["Financial Conditions"] = "완화/안정"
            score += 1
        elif (m["us10y"] > m["us10y_20dago"] + 0.25) or (m["hy_oas"] > m["hy_oas_20dago"] + 0.40):
            out["Financial Conditions"] = "긴축/스트레스"
            score -= 1
        else:
            out["Financial Conditions"] = "중립"
    else:
        out["Financial Conditions"] = "확인 필요"

    # Overall regime heuristic
    if out["Inflation"] == "둔화" and out["Employment"] in ["견조", "완만한 냉각"] and out["Growth"] in ["개선", "횡보"]:
        regime = "연착륙/골디락스 후보"
    elif out["Employment"] == "빠른 악화" and out["Growth"] == "둔화":
        regime = "경착륙/침체 위험"
    elif out["Inflation"] == "재가속" and out["Growth"] in ["개선", "횡보"]:
        regime = "재인플레이션/금리상승 위험"
    elif out["Inflation"] == "재가속" and out["Growth"] == "둔화":
        regime = "스태그플레이션 위험"
    else:
        regime = "전환/혼조 국면"

    if score >= 3:
        bias = "Risk-on 우세"
    elif score <= -3:
        bias = "Risk-off 우세"
    else:
        bias = "Neutral / 선택적"

    return out, regime, bias, score


def price_signal_text(row, group):
    score = row.get("Oversold Score", np.nan)
    rsi = row.get("RSI14", np.nan)
    trend = row.get("MA200 Trend", "")
    dd = row.get("1Y Drawdown %", np.nan)

    if pd.isna(score):
        return "데이터 확인"

    if group == "Equity":
        if score >= 3 and trend == "상승":
            return "과매도 + 장기상승추세"
        if score >= 3:
            return "과매도(추세 확인 필요)"
        if rsi >= 70 and dd > -3:
            return "단기 과열"
        if trend == "상승":
            return "상승추세 / 중립"
        return "약세추세 / 중립"

    if group == "Bond":
        if score >= 3:
            return "채권가격 과매도"
        if trend == "상승":
            return "채권가격 상승추세"
        return "채권가격 약세/중립"

    if group == "Gold":
        if score >= 3:
            return "금 가격 과매도"
        if rsi >= 70:
            return "금 단기 과열"
        return "중립"

    return "중립"


def recommendation_text(asset_name, group, row, macro_bias, macro_regime):
    """
    Heuristic "context", not personalized financial advice or a prediction.
    """
    price_sig = price_signal_text(row, group)

    if group == "Equity":
        if "경착륙" in macro_regime:
            if row.get("Oversold Score", 0) >= 3:
                return "정찰/분할 접근 — 침체 확인 전 대량진입 경계"
            return "보수적 — 경기악화 확인 필요"
        if macro_bias == "Risk-on 우세":
            if "과열" in price_sig:
                return "추격보다 눌림 대기"
            if row.get("Oversold Score", 0) >= 2:
                return "분할매수 우호"
            return "정상 비중 / 눌림 매수"
        if macro_bias == "Risk-off 우세":
            return "비중 확대 신중"
        return "중립 — 가격신호 우선"

    if group == "Bond":
        if "경착륙" in macro_regime:
            return "우호 가능 — 금리 하락 경로 확인"
        if "재인플레이션" in macro_regime or "스태그플레이션" in macro_regime:
            return "금리 재상승 위험 경계"
        return "금리 방향과 분할진입 병행"

    if group == "Gold":
        if "스태그플레이션" in macro_regime or "경착륙" in macro_regime:
            return "분산자산 역할 확대 가능"
        if "재인플레이션" in macro_regime:
            return "실질금리·달러 동반 확인"
        return "분산 목적 유지 / 가격신호 병행"

    return "확인 필요"




def rate_condition(m):
    """최근 미 국채/실질금리 방향을 요약한다. 예측값이 아니라 현재 추세 판정이다."""
    if pd.isna(m.get("us10y")) or pd.isna(m.get("us10y_20dago")):
        return "확인 필요", np.nan, np.nan, np.nan

    d10_1m = m["us10y"] - m["us10y_20dago"]
    d10_3m = m["us10y"] - m["us10y_60dago"] if pd.notna(m.get("us10y_60dago")) else np.nan
    dreal = m["real10y"] - m["real10y_20dago"] if pd.notna(m.get("real10y")) and pd.notna(m.get("real10y_20dago")) else np.nan

    if d10_1m >= 0.25 or (pd.notna(dreal) and dreal >= 0.15):
        label = "↑↑ 급등 경계"
    elif d10_1m >= 0.10:
        label = "↑ 상승"
    elif d10_1m <= -0.20 and (pd.isna(dreal) or dreal <= -0.05):
        label = "↓↓ 완화"
    elif d10_1m <= -0.10:
        label = "↓ 하락"
    else:
        label = "→ 안정"
    return label, d10_1m, d10_3m, dreal


def rate_fit_score(asset_name, group, m):
    """자산별 금리 적합도 0~15."""
    u10, u10p = m.get("us10y"), m.get("us10y_20dago")
    u30, u30p = m.get("us30y"), m.get("us30y_20dago")
    rr, rrp = m.get("real10y"), m.get("real10y_20dago")

    d10 = u10 - u10p if pd.notna(u10) and pd.notna(u10p) else np.nan
    d30 = u30 - u30p if pd.notna(u30) and pd.notna(u30p) else np.nan
    dr = rr - rrp if pd.notna(rr) and pd.notna(rrp) else np.nan

    if group == "Equity":
        p = 8
        if pd.notna(d10):
            if d10 <= -0.20: p += 4
            elif d10 <= -0.05: p += 2
            elif d10 >= 0.25: p -= 5
            elif d10 >= 0.10: p -= 2
        if asset_name == "Nasdaq 100" and pd.notna(dr):
            if dr <= -0.10: p += 3
            elif dr >= 0.15: p -= 4
        elif pd.notna(dr):
            if dr <= -0.10: p += 1
            elif dr >= 0.15: p -= 2
        return int(np.clip(p, 0, 15))

    if group == "Bond":
        d = d30 if "Long" in asset_name else d10
        p = 7
        if pd.notna(d):
            if d <= -0.30: p += 8
            elif d <= -0.15: p += 6
            elif d <= -0.05: p += 3
            elif d >= 0.30: p -= 7
            elif d >= 0.15: p -= 5
            elif d >= 0.05: p -= 2
        return int(np.clip(p, 0, 15))

    if group == "Gold":
        p = 7
        if pd.notna(dr):
            if dr <= -0.20: p += 8
            elif dr <= -0.10: p += 6
            elif dr <= -0.03: p += 3
            elif dr >= 0.20: p -= 7
            elif dr >= 0.10: p -= 5
            elif dr >= 0.03: p -= 2
        elif pd.notna(d10):
            if d10 <= -0.15: p += 4
            elif d10 >= 0.15: p -= 4
        return int(np.clip(p, 0, 15))

    return 7

def macro_fit_score(asset_name, group, macro_state, macro_regime, macro_bias, m):
    """경기·물가·고용 중심 거시 적합도 0~20. 금리는 별도 점수에서 평가."""
    if group == "Equity":
        p = 10
        if macro_state.get("Growth") == "개선": p += 4
        elif macro_state.get("Growth") == "둔화": p -= 4
        if macro_state.get("Inflation") == "둔화": p += 3
        elif macro_state.get("Inflation") == "재가속": p -= 4
        if macro_state.get("Employment") == "견조": p += 2
        elif macro_state.get("Employment") == "빠른 악화": p -= 5
        cap = 16 if asset_name in ["KOSPI", "Nifty 50"] else 20
        return int(np.clip(p, 0, cap))

    if group == "Bond":
        p = 8
        if macro_state.get("Inflation") == "둔화": p += 6
        elif macro_state.get("Inflation") == "재가속": p -= 6
        if macro_state.get("Growth") == "둔화": p += 4
        elif macro_state.get("Growth") == "개선": p -= 2
        if macro_state.get("Employment") == "빠른 악화": p += 3
        if "경착륙" in macro_regime: p += 2
        return int(np.clip(p, 0, 20))

    if group == "Gold":
        p = 9
        if "경착륙" in macro_regime: p += 5
        if "스태그플레이션" in macro_regime: p += 6
        if macro_state.get("Inflation") == "재가속": p += 2
        return int(np.clip(p, 0, 20))

    return 10


def entry_decision(row, macro_state, macro_regime, macro_bias, m):
    group, asset_name = row["분류"], row["자산"]
    oversold = row.get("Oversold Score", np.nan)
    rsi = row.get("RSI14", np.nan)
    r1m = row.get("1M %", np.nan)
    trend_up = row.get("MA200 Trend") == "상승"

    price_pts = int(round(oversold * 8.75)) if pd.notna(oversold) else 0
    trend_pts = 20 if trend_up else 5
    macro_pts = macro_fit_score(asset_name, group, macro_state, macro_regime, macro_bias, m)
    rate_pts = rate_fit_score(asset_name, group, m)

    if pd.isna(r1m): pullback_pts = 3
    elif -12 <= r1m <= -2: pullback_pts = 10
    elif -2 < r1m <= 1.5: pullback_pts = 7
    elif -20 <= r1m < -12: pullback_pts = 6
    elif 1.5 < r1m <= 5: pullback_pts = 3
    else: pullback_pts = 0

    score = price_pts + trend_pts + macro_pts + rate_pts + pullback_pts
    if pd.notna(rsi) and rsi >= 70: score = min(score, 58)
    if group == "Equity" and "경착륙" in macro_regime: score = min(score, 58)

    if score >= 75: action, css = "진입 우호", "action-good"
    elif score >= 60: action, css = "분할 진입", "action-mid"
    elif score >= 45: action, css = "정찰 / 대기", "action-watch"
    else: action, css = "대기", "action-wait"

    notes = []
    if pd.notna(oversold): notes.append(f"과매도 {int(oversold)}/4")
    notes.append("MA200 상승" if trend_up else "MA200 약세/미확인")
    if pd.notna(rsi): notes.append(f"RSI {rsi:.0f}")
    notes.append(f"거시 {macro_pts}/20")
    notes.append(f"금리 {rate_pts}/15")
    if asset_name == "KOSPI": notes.append("원/달러·외인수급 별도 확인")
    elif asset_name == "Nifty 50": notes.append("인도금리·루피 별도 확인")

    return {
        "Entry Score": int(score), "Action": action, "CSS": css,
        "Price Pts": price_pts, "Trend Pts": trend_pts, "Macro Pts": macro_pts,
        "Rate Pts": rate_pts, "Pullback Pts": pullback_pts,
        "Reason": " · ".join(notes),
    }



def status_tone(value, kind="generic"):
    """첫 화면 상태카드 색상: blue=우호, orange=주의/혼조, red=비우호, gray=미확인."""
    s = str(value)
    if any(k in s for k in ["확인 필요", "N/A", "미확인"]):
        return "status-neutral"

    if kind == "regime":
        if any(k in s for k in ["연착륙", "골디락스"]): return "status-good"
        if any(k in s for k in ["경착륙", "침체", "스태그플레이션", "재인플레이션"]): return "status-bad"
        return "status-warn"
    if kind == "buy":
        if any(k in s for k in ["확대", "정상"]): return "status-good"
        if "축소" in s: return "status-warn"
        if "방어" in s: return "status-bad"
    if kind == "growth":
        if "개선" in s: return "status-good"
        if "둔화" in s: return "status-bad"
        return "status-warn"
    if kind == "inflation":
        if "둔화" in s: return "status-good"
        if "재가속" in s: return "status-bad"
        return "status-warn"
    if kind == "employment":
        if "견조" in s: return "status-good"
        if "빠른 악화" in s: return "status-bad"
        if "완만한 냉각" in s: return "status-warn"
        return "status-neutral"
    if kind == "rates":
        if any(k in s for k in ["↓↓", "↓ 하락", "완화"]): return "status-good"
        if any(k in s for k in ["↑↑", "급등"]): return "status-bad"
        if "↑ 상승" in s: return "status-warn"
        if "안정" in s: return "status-good"
        return "status-neutral"
    return "status-neutral"


def status_card(label, value, kind="generic", sub=""):
    tone = status_tone(value, kind)
    sub_html = f'<div class="status-sub">{sub}</div>' if sub else ''
    return f"""<div class=\"status-card {tone}\"><div class=\"status-label\">{label}</div><div class=\"status-value\">{value}</div>{sub_html}</div>"""

def card_html(row):
    price, r1m = row.get("Price", np.nan), row.get("1M %", np.nan)
    ptxt = "N/A" if pd.isna(price) else f"{price:,.2f}"
    rtxt = "N/A" if pd.isna(r1m) else f"{r1m:+.1f}%"
    card_cls = {"action-good":"card-good", "action-mid":"card-mid", "action-watch":"card-watch", "action-wait":"card-wait"}.get(row['CSS'], "")
    return f"""<div class="asset-card {card_cls}"><div class="asset-title">{row['자산']}</div>
    <div class="asset-ticker">{row['Ticker']}</div><div class="action {row['CSS']}">{row['Action']}</div>
    <div class="score-line"><b>진입점수 {int(row['Entry Score'])}/100</b> · 1M {rtxt}</div>
    <div class="score-line">가격 {ptxt} · MA200 {row['MA200 Trend']}</div><div class="reason">{row['Reason']}</div></div>"""

def fig_lines(series_dict, title, ytitle="", last_n=None):
    fig = go.Figure()
    for name, s in series_dict.items():
        x = s.dropna()
        if last_n:
            x = x.tail(last_n)
        if len(x):
            fig.add_trace(go.Scatter(x=x.index, y=x.values, mode="lines", name=name))
    fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h"),
        yaxis_title=ytitle,
        hovermode="x unified",
    )
    return fig


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.header("설정")

api_key = fred_key()
if api_key:
    st.sidebar.success("FRED API Key 자동 연결됨")
else:
    st.sidebar.error("FRED_API_KEY가 설정되지 않았습니다. Streamlit Secrets 또는 환경변수를 확인하세요.")

years = st.sidebar.slider("거시 시계열 조회기간(년)", 2, 10, 5)

st.sidebar.subheader("시장 티커")
asset_map = {}
for name, default_ticker in DEFAULT_ASSETS.items():
    asset_map[name] = st.sidebar.text_input(name, value=default_ticker)

st.sidebar.caption(
    "IEF/TLT/GLD는 미국 상장 프록시입니다. 실제 보유한 국내상장 ETF의 Yahoo Finance 티커가 있으면 교체하세요."
)

consensus_file = st.sidebar.file_uploader(
    "컨센서스 CSV (선택)",
    type=["csv"],
    help="권장 열: release_date, indicator, actual, consensus, previous",
)

refresh = st.sidebar.button("🔄 캐시 비우고 새로고침")
if refresh:
    st.cache_data.clear()
    st.rerun()

# ============================================================
# LOAD DATA
# ============================================================
start_date = str(date.today() - timedelta(days=365 * years + 120))

fred = {}
if api_key:
    with st.spinner("FRED 경제데이터 불러오는 중..."):
        for label, sid in FRED_SERIES.items():
            try:
                fred[label] = load_fred_series(sid, api_key, start_date)
            except Exception as e:
                fred[label] = pd.Series(dtype=float)
                st.sidebar.error(f"{label} 로드 실패: {e}")
else:
    for label in FRED_SERIES:
        fred[label] = pd.Series(dtype=float)

tickers = tuple(dict.fromkeys(asset_map.values()))
with st.spinner("시장가격 불러오는 중..."):
    try:
        prices = load_market_prices(tickers, "3y")
    except Exception as e:
        prices = pd.DataFrame()
        st.error(f"시장가격 로드 실패: {e}")

# ============================================================
# TRANSFORM MACRO DATA
# ============================================================
macro_series = {}

# Inflation
for name in ["CPI", "Core CPI", "PPI Final Demand", "Core PPI", "PCE", "Core PCE"]:
    s = fred[name]
    if len(s):
        macro_series[f"{name} YoY"] = yoy_monthly(s)
        macro_series[f"{name} MoM"] = mom_monthly(s)
        macro_series[f"{name} 3M Ann."] = annualized_change(s, 3)
        macro_series[f"{name} 6M Ann."] = annualized_change(s, 6)

# Employment
payems = fred["Nonfarm Payrolls"]
payroll_change = payems.diff() if len(payems) else pd.Series(dtype=float)
payroll_3m = payroll_change.rolling(3).mean()
payroll_6m = payroll_change.rolling(6).mean()

unrate = fred["Unemployment Rate"]
wage = fred["Average Hourly Earnings"]
wage_yoy = yoy_monthly(wage) if len(wage) else pd.Series(dtype=float)
claims = fred["Initial Claims"]
claims_4w = claims.rolling(4).mean() if len(claims) else pd.Series(dtype=float)

# Growth
real_retail_yoy = yoy_monthly(fred["Real Retail Sales"]) if len(fred["Real Retail Sales"]) else pd.Series(dtype=float)
indpro_yoy = yoy_monthly(fred["Industrial Production"]) if len(fred["Industrial Production"]) else pd.Series(dtype=float)

# Rates
dgs2 = fred["US 2Y"]
dgs10 = fred["US 10Y"]
dgs30 = fred["US 30Y"]
real10 = fred["US 10Y Real Yield"]
hy_oas = fred["HY OAS"]
spread = fred["10Y-2Y Spread"]

def daily_lookback(s, n=20):
    x = s.dropna()
    return float(x.iloc[-1-n]) if len(x) > n else np.nan

m = {
    "core_cpi_yoy": latest_valid(macro_series.get("Core CPI YoY", pd.Series(dtype=float))),
    "core_cpi_yoy_3mago": value_months_ago(macro_series.get("Core CPI YoY", pd.Series(dtype=float)), 3),
    "core_cpi_3m_ann": latest_valid(macro_series.get("Core CPI 3M Ann.", pd.Series(dtype=float))),
    "core_pce_yoy": latest_valid(macro_series.get("Core PCE YoY", pd.Series(dtype=float))),
    "unrate": latest_valid(unrate),
    "unrate_3mago": value_months_ago(unrate, 3),
    "payroll_3m_avg": latest_valid(payroll_3m),
    "payroll_6m_avg": latest_valid(payroll_6m),
    "real_retail_yoy": latest_valid(real_retail_yoy),
    "real_retail_yoy_3mago": value_months_ago(real_retail_yoy, 3),
    "indpro_yoy": latest_valid(indpro_yoy),
    "indpro_yoy_3mago": value_months_ago(indpro_yoy, 3),
    "us2y": latest_valid(dgs2),
    "us2y_20dago": daily_lookback(dgs2, 20),
    "us10y": latest_valid(dgs10),
    "us10y_20dago": daily_lookback(dgs10, 20),
    "us10y_60dago": daily_lookback(dgs10, 60),
    "us30y": latest_valid(dgs30),
    "us30y_20dago": daily_lookback(dgs30, 20),
    "real10y": latest_valid(real10),
    "real10y_20dago": daily_lookback(real10, 20),
    "hy_oas": latest_valid(hy_oas),
    "hy_oas_20dago": daily_lookback(hy_oas, 20),
}

macro_state, macro_regime, macro_bias, macro_score = make_macro_summary(m)
rate_trend, rate_1m_delta, rate_3m_delta, real_rate_1m_delta = rate_condition(m)

# ============================================================
# BUILD ASSET DECISION TABLE BEFORE UI
# ============================================================
asset_rows = []
asset_metrics_map = {}

if not prices.empty:
    for asset_name, ticker in asset_map.items():
        if ticker in prices.columns:
            met = asset_metrics(prices[ticker])
            if met:
                asset_metrics_map[asset_name] = met
                asset_rows.append({"자산": asset_name, "Ticker": ticker, "분류": ASSET_GROUP[asset_name], **met})

asset_df = pd.DataFrame(asset_rows)

if not asset_df.empty:
    decisions = [entry_decision(r, macro_state, macro_regime, macro_bias, m) for _, r in asset_df.iterrows()]
    decision_df = pd.concat([asset_df.reset_index(drop=True), pd.DataFrame(decisions)], axis=1)
else:
    decision_df = pd.DataFrame()

if macro_score >= 3:
    buy_intensity = "정상~확대 검토"
elif macro_score >= 0:
    buy_intensity = "정상"
elif macro_score >= -2:
    buy_intensity = "축소"
else:
    buy_intensity = "방어"

# ============================================================
# TABS
# ============================================================
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Decision Cockpit",
    "🌐 Macro Trends",
    "📈 Asset Details",
    "🧾 Consensus",
    "🔬 Diagnostics",
])

# ============================================================
# TAB 0: DECISION COCKPIT
# ============================================================
with tab0:
    st.markdown('<div class="section-label">Market regime</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(status_card("거시국면", macro_regime, "regime"), unsafe_allow_html=True)
    with c2:
        st.markdown(status_card("전체 매수강도", buy_intensity, "buy"), unsafe_allow_html=True)
    with c3:
        st.markdown(status_card("성장", macro_state.get("Growth", "N/A"), "growth"), unsafe_allow_html=True)
    with c4:
        st.markdown(status_card("물가", macro_state.get("Inflation", "N/A"), "inflation"), unsafe_allow_html=True)
    with c5:
        st.markdown(status_card("고용", macro_state.get("Employment", "N/A"), "employment"), unsafe_allow_html=True)
    with c6:
        rate_sub = f"10Y 1M {rate_1m_delta:+.2f}%p" if pd.notna(rate_1m_delta) else ""
        st.markdown(status_card("금리 추이", rate_trend, "rates", rate_sub), unsafe_allow_html=True)
    st.caption(f"중단기 Bias: {macro_bias}")

    st.markdown('<div class="section-label">All assets — entry status</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.76rem;color:#777;margin:-2px 0 8px 0;">● <span style="color:#2474d2;font-weight:700;">파랑: 우호</span> &nbsp;&nbsp; ● <span style="color:#e49318;font-weight:700;">주황: 주의/분할</span> &nbsp;&nbsp; ● <span style="color:#d94b4b;font-weight:700;">빨강: 비우호/대기</span> &nbsp;&nbsp; ● <span style="color:#888;font-weight:700;">회색: 미확인</span></div>', unsafe_allow_html=True)

    if decision_df.empty:
        st.warning("시장가격 데이터를 불러오지 못해 자산별 진입판정을 표시할 수 없습니다.")
    else:
        order = list(DEFAULT_ASSETS.keys())
        by_name = {r["자산"]: r for _, r in decision_df.iterrows()}

        for names in [order[:4], order[4:]]:
            cols = st.columns(len(names))
            for col, name in zip(cols, names):
                with col:
                    if name in by_name:
                        st.markdown(card_html(by_name[name]), unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f"""<div class="asset-card"><div class="asset-title">{name}</div>
                            <div class="asset-ticker">{asset_map[name]}</div>
                            <div class="action action-wait">데이터 확인</div>
                            <div class="reason">가격 데이터를 불러오지 못했습니다.</div></div>""",
                            unsafe_allow_html=True,
                        )

        st.markdown('<div class="section-label">Priority board</div>', unsafe_allow_html=True)
        board = decision_df[[
            "자산", "Action", "Entry Score", "Oversold Score", "RSI14", "MA200 Trend", "1M %", "Macro Pts", "Rate Pts"
        ]].copy()
        board.columns = ["자산", "판정", "진입점수", "과매도", "RSI", "MA200", "1개월", "거시적합", "금리적합"]
        board = board.sort_values(["진입점수", "자산"], ascending=[False, True])

        st.dataframe(
            board,
            use_container_width=True,
            hide_index=True,
            column_config={
                "진입점수": st.column_config.ProgressColumn("진입점수", min_value=0, max_value=100, format="%d"),
                "과매도": st.column_config.NumberColumn("과매도", format="%.0f"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                "1개월": st.column_config.NumberColumn("1개월", format="%+.1f%%"),
                "거시적합": st.column_config.ProgressColumn("거시적합", min_value=0, max_value=20, format="%d"),
                "금리적합": st.column_config.ProgressColumn("금리적합", min_value=0, max_value=15, format="%d"),
            },
        )

        top = board.iloc[0]
        a, b, c = st.columns(3)
        with a:
            st.markdown(
                f"""<div class="summary-box"><div class="summary-big">우선 확인: {top['자산']}</div>
                <div class="summary-small">자동 진입점수 {int(top['진입점수'])}/100. 높은 점수부터 상세 탭에서 가격 위치를 확인합니다.</div></div>""",
                unsafe_allow_html=True,
            )
        with b:
            st.markdown(
                f"""<div class="summary-box"><div class="summary-big">거시: {macro_regime}</div>
                <div class="summary-small">성장 {macro_state.get('Growth','N/A')} · 물가 {macro_state.get('Inflation','N/A')} · 고용 {macro_state.get('Employment','N/A')} · 금리 {rate_trend}</div></div>""",
                unsafe_allow_html=True,
            )
        with c:
            st.markdown(
                """<div class="summary-box"><div class="summary-big">판정 원칙</div>
                <div class="summary-small">거시는 매수 강도를 조절하고, 실제 진입은 과매도·MA200 추세·최근 눌림을 함께 확인합니다.</div></div>""",
                unsafe_allow_html=True,
            )

    st.caption(
        "진입점수 = 과매도 35 + MA200 추세 20 + 경기·물가·고용 20 + 자산별 금리조건 15 + 최근 1개월 눌림 10. "
        "RSI≥70 또는 경착륙 국면의 주식은 높은 판정을 제한합니다. KOSPI·Nifty는 미국 거시만으로 완결판정하지 않도록 거시점수 상한을 낮췄습니다."
    )

# ============================================================
# TAB 1: MACRO TRENDS
# ============================================================
with tab1:
    st.subheader("거시 추세 — 12개월 큰 방향 + 최근 3~6개월 모멘텀")

    rows = []
    def add_macro_row(name, series, inverse=False):
        x = series.dropna()
        if len(x) == 0:
            rows.append([name, np.nan, np.nan, np.nan, np.nan, "N/A"])
            return
        now = latest_valid(x)
        v3 = value_months_ago(x, 3)
        v6 = value_months_ago(x, 6)
        v12 = value_months_ago(x, 12)
        rows.append([name, now, v3, v6, v12, slope_label(now, v3, inverse=inverse)])

    add_macro_row("Core CPI YoY", macro_series.get("Core CPI YoY", pd.Series(dtype=float)))
    add_macro_row("Core CPI 3M annualized", macro_series.get("Core CPI 3M Ann.", pd.Series(dtype=float)))
    add_macro_row("Core PCE YoY", macro_series.get("Core PCE YoY", pd.Series(dtype=float)))
    add_macro_row("PPI Final Demand YoY", macro_series.get("PPI Final Demand YoY", pd.Series(dtype=float)))
    add_macro_row("Unemployment Rate", unrate)
    add_macro_row("Wage YoY", wage_yoy)
    add_macro_row("Real Retail Sales YoY", real_retail_yoy)
    add_macro_row("Industrial Production YoY", indpro_yoy)

    macro_table = pd.DataFrame(rows, columns=["지표", "현재", "3M 전", "6M 전", "12M 전", "최근 3M 방향"])
    st.dataframe(
        macro_table.style.format({"현재":"{:.2f}", "3M 전":"{:.2f}", "6M 전":"{:.2f}", "12M 전":"{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    a, b = st.columns(2)
    with a:
        st.plotly_chart(fig_lines({
            "CPI YoY": macro_series.get("CPI YoY", pd.Series(dtype=float)),
            "Core CPI YoY": macro_series.get("Core CPI YoY", pd.Series(dtype=float)),
            "Core PCE YoY": macro_series.get("Core PCE YoY", pd.Series(dtype=float)),
        }, "Inflation — YoY", "%", 36), use_container_width=True)
    with b:
        st.plotly_chart(fig_lines({
            "Core CPI 3M ann.": macro_series.get("Core CPI 3M Ann.", pd.Series(dtype=float)),
            "Core CPI 6M ann.": macro_series.get("Core CPI 6M Ann.", pd.Series(dtype=float)),
        }, "Inflation Momentum", "%", 36), use_container_width=True)

    c, d = st.columns(2)
    with c:
        st.plotly_chart(fig_lines({"Payroll 3M avg": payroll_3m, "Payroll 6M avg": payroll_6m},
                                  "Employment — Payroll Momentum", "천 명", 36), use_container_width=True)
    with d:
        st.plotly_chart(fig_lines({"Unemployment %": unrate}, "Unemployment Rate", "%", 36), use_container_width=True)

    e, f = st.columns(2)
    with e:
        st.plotly_chart(fig_lines({"Real Retail Sales YoY": real_retail_yoy, "Industrial Production YoY": indpro_yoy},
                                  "Growth / Demand", "%", 36), use_container_width=True)
    with f:
        st.plotly_chart(fig_lines({"US 2Y": dgs2, "US 10Y": dgs10, "US 30Y": dgs30, "10Y Real Yield": real10},
                                  "US Treasury & Real Yield", "%", 504), use_container_width=True)

    g, h = st.columns(2)
    with g:
        st.plotly_chart(fig_lines({"Initial Claims 4W avg": claims_4w}, "Initial Jobless Claims", "건", 104), use_container_width=True)
    with h:
        st.plotly_chart(fig_lines({"HY OAS": hy_oas}, "Credit Stress — HY OAS", "%", 504), use_container_width=True)

# ============================================================
# TAB 2: ASSET DETAILS
# ============================================================
with tab2:
    st.subheader("자산별 가격 위치와 진입점수 구성")
    if decision_df.empty:
        st.warning("시장가격 데이터가 없습니다.")
    else:
        selected = st.selectbox("자산 선택", decision_df["자산"].tolist())
        r = decision_df.loc[decision_df["자산"] == selected].iloc[0]

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("현재 판정", r["Action"])
        c2.metric("진입점수", f"{int(r['Entry Score'])}/100")
        c3.metric("과매도", f"{int(r['Oversold Score'])}/4" if pd.notna(r['Oversold Score']) else "N/A")
        c4.metric("RSI14", f"{r['RSI14']:.1f}" if pd.notna(r['RSI14']) else "N/A")
        c5.metric("1M", f"{r['1M %']:+.1f}%" if pd.notna(r['1M %']) else "N/A")
        c6.metric("1Y 고점대비", f"{r['1Y Drawdown %']:+.1f}%" if pd.notna(r['1Y Drawdown %']) else "N/A")

        st.write(
            f"**점수 구성:** 가격 {int(r['Price Pts'])}/35 · 추세 {int(r['Trend Pts'])}/20 · "
            f"거시 {int(r['Macro Pts'])}/20 · 금리 {int(r['Rate Pts'])}/15 · 눌림 {int(r['Pullback Pts'])}/10"
        )
        st.caption(r["Reason"])

        ticker = r["Ticker"]
        if ticker in prices.columns:
            x = prices[ticker].dropna().tail(504)
            ma20 = x.rolling(20).mean(); ma60 = x.rolling(60).mean(); ma200 = x.rolling(200).mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x.index, y=x, name="Price", mode="lines"))
            fig.add_trace(go.Scatter(x=ma20.index, y=ma20, name="MA20", mode="lines"))
            fig.add_trace(go.Scatter(x=ma60.index, y=ma60, name="MA60", mode="lines"))
            fig.add_trace(go.Scatter(x=ma200.index, y=ma200, name="MA200", mode="lines"))
            fig.update_layout(title=f"{selected} — 최근 약 2년", height=470, hovermode="x unified",
                              margin=dict(l=10,r=10,t=45,b=10), legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)

        detail_cols = ["자산","Ticker","Price","1M %","3M %","6M %","1Y %","RSI14","D20 %","D60 %","D200 %","1Y Drawdown %","Oversold Score","MA200 Trend"]
        st.dataframe(pd.DataFrame([r[detail_cols]]), use_container_width=True, hide_index=True)

# ============================================================
# TAB 3: CONSENSUS
# ============================================================
with tab3:
    st.subheader("당월 Actual vs Consensus")
    st.write(
        "FRED는 실제 경제지표 시계열에 사용하고, 시장 컨센서스는 별도 CSV로 관리합니다. "
        "장기 Trend와 단기 Surprise를 섞지 않는 것이 목적입니다."
    )

    sample = pd.DataFrame({
        "release_date": ["2026-08-01"], "indicator": ["Core CPI MoM"],
        "actual": [0.2], "consensus": [0.2], "previous": [0.3],
    })
    st.download_button("컨센서스 CSV 템플릿", data=sample.to_csv(index=False).encode("utf-8-sig"),
                       file_name="consensus_template.csv", mime="text/csv")

    if consensus_file is not None:
        try:
            con = pd.read_csv(consensus_file)
            required = {"release_date","indicator","actual","consensus"}
            if not required.issubset(con.columns):
                st.error(f"필수 열이 없습니다: {sorted(required)}")
            else:
                con["release_date"] = pd.to_datetime(con["release_date"], errors="coerce")
                con["actual"] = pd.to_numeric(con["actual"], errors="coerce")
                con["consensus"] = pd.to_numeric(con["consensus"], errors="coerce")
                con["surprise"] = con["actual"] - con["consensus"]
                con = con.sort_values("release_date", ascending=False)
                st.dataframe(con, use_container_width=True, hide_index=True)
                st.caption("Surprise의 +/− 자체가 주가 호재/악재를 뜻하지는 않습니다. 당시 금리·경기 국면과 함께 해석해야 합니다.")
        except Exception as e:
            st.error(f"CSV 읽기 실패: {e}")
    else:
        st.info("사이드바에서 컨센서스 CSV를 올리면 표시됩니다.")

# ============================================================
# TAB 4: DIAGNOSTICS
# ============================================================
with tab4:
    st.subheader("데이터 상태 / 진단")
    diagnostics = []
    for name, s in fred.items():
        x = s.dropna()
        diagnostics.append({
            "데이터": name, "FRED Series": FRED_SERIES[name],
            "최신 관측일": x.index[-1].date().isoformat() if len(x) else None,
            "최신값": x.iloc[-1] if len(x) else np.nan, "관측수": len(x),
        })
    st.dataframe(pd.DataFrame(diagnostics), use_container_width=True, hide_index=True)

    if not prices.empty:
        md = []
        for name, ticker in asset_map.items():
            if ticker in prices.columns:
                x = prices[ticker].dropna()
                md.append({"자산":name, "Ticker":ticker,
                           "최신 가격일":x.index[-1].date().isoformat() if len(x) else None,
                           "최신값":x.iloc[-1] if len(x) else np.nan, "관측수":len(x)})
        st.dataframe(pd.DataFrame(md), use_container_width=True, hide_index=True)

    st.warning("FRED 일반 시계열은 과거 수정값을 반영할 수 있습니다. 당시 시장이 실제로 알고 있던 값으로 백테스트하려면 ALFRED/vintage 데이터가 필요합니다.")

st.divider()
st.caption("데이터: FRED API(거시) + Yahoo Finance/yfinance(가격). 진입점수는 규칙 기반 의사결정 보조지표이며 미래 수익률 예측값이 아닙니다.")
