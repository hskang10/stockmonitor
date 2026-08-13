
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
    page_title="Macro & Multi-Asset Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Macro & Multi-Asset Dashboard")
st.caption(
    "중·단기: 최근 모멘텀·서프라이즈·금리·가격신호 | "
    "장기: 6~18개월 거시 추세·경기국면·장기추세"
)

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
if not api_key:
    st.sidebar.warning("FRED_API_KEY가 없습니다.")
    api_key_input = st.sidebar.text_input("FRED API Key", type="password")
    if api_key_input:
        api_key = api_key_input
else:
    st.sidebar.success("FRED API Key 연결됨")

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
    "us10y": latest_valid(dgs10),
    "us10y_20dago": daily_lookback(dgs10, 20),
    "hy_oas": latest_valid(hy_oas),
    "hy_oas_20dago": daily_lookback(hy_oas, 20),
}

macro_state, macro_regime, macro_bias, macro_score = make_macro_summary(m)

# ============================================================
# TOP SUMMARY
# ============================================================
st.subheader("1. 현재 거시환경 요약")
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("경기국면(휴리스틱)", macro_regime)
c2.metric("중단기 Risk Bias", macro_bias)
c3.metric("물가", macro_state.get("Inflation", "N/A"))
c4.metric("고용", macro_state.get("Employment", "N/A"))
c5.metric("성장", macro_state.get("Growth", "N/A"))

st.caption(
    "※ 위 판정은 자동화된 휴리스틱입니다. 공식 경기침체 판정이나 수익률 예측이 아닙니다. "
    "특히 한국·인도 주식에는 각국 경기·금리·환율이 추가로 중요합니다."
)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Macro Regime",
    "📈 Multi-Asset",
    "🎯 Entry Signals",
    "🧾 Consensus",
    "🔬 Raw / Diagnostics",
])

# ============================================================
# TAB 1: MACRO
# ============================================================
with tab1:
    st.subheader("거시 추세: 12개월 큰 방향 + 최근 3~6개월 모멘텀")

    # Summary table
    rows = []

    def add_macro_row(name, series, fmt=".2f", inverse=False):
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

    macro_table = pd.DataFrame(
        rows,
        columns=["지표", "현재", "3M 전", "6M 전", "12M 전", "최근 3M 방향"],
    )
    st.dataframe(
        macro_table.style.format({
            "현재": "{:.2f}",
            "3M 전": "{:.2f}",
            "6M 전": "{:.2f}",
            "12M 전": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    colA, colB = st.columns(2)
    with colA:
        inf_fig = fig_lines(
            {
                "CPI YoY": macro_series.get("CPI YoY", pd.Series(dtype=float)),
                "Core CPI YoY": macro_series.get("Core CPI YoY", pd.Series(dtype=float)),
                "Core PCE YoY": macro_series.get("Core PCE YoY", pd.Series(dtype=float)),
            },
            "Inflation — YoY",
            "%",
            last_n=36,
        )
        st.plotly_chart(inf_fig, use_container_width=True)

    with colB:
        mom_fig = fig_lines(
            {
                "Core CPI 3M ann.": macro_series.get("Core CPI 3M Ann.", pd.Series(dtype=float)),
                "Core CPI 6M ann.": macro_series.get("Core CPI 6M Ann.", pd.Series(dtype=float)),
                "Core PCE 3M ann.": macro_series.get("Core PCE 3M Ann.", pd.Series(dtype=float)),
            },
            "Inflation Momentum — Annualized",
            "%",
            last_n=36,
        )
        st.plotly_chart(mom_fig, use_container_width=True)

    colC, colD = st.columns(2)
    with colC:
        emp_fig = fig_lines(
            {
                "Payroll 3M avg (k)": payroll_3m,
                "Payroll 6M avg (k)": payroll_6m,
            },
            "Employment — Payroll Monthly Change",
            "천 명",
            last_n=36,
        )
        st.plotly_chart(emp_fig, use_container_width=True)

    with colD:
        emp2_fig = fig_lines(
            {
                "Unemployment %": unrate,
            },
            "Employment — Unemployment Rate",
            "%",
            last_n=36,
        )
        st.plotly_chart(emp2_fig, use_container_width=True)

    colE, colF = st.columns(2)
    with colE:
        growth_fig = fig_lines(
            {
                "Real Retail Sales YoY": real_retail_yoy,
                "Industrial Production YoY": indpro_yoy,
            },
            "Growth / Demand",
            "%",
            last_n=36,
        )
        st.plotly_chart(growth_fig, use_container_width=True)

    with colF:
        rates_fig = fig_lines(
            {
                "US 2Y": dgs2,
                "US 10Y": dgs10,
                "US 30Y": dgs30,
            },
            "US Treasury Yields",
            "%",
            last_n=504,
        )
        st.plotly_chart(rates_fig, use_container_width=True)

    colG, colH = st.columns(2)
    with colG:
        claims_fig = fig_lines(
            {"Initial Claims 4W avg": claims_4w},
            "Initial Jobless Claims — 4W Average",
            "건",
            last_n=104,
        )
        st.plotly_chart(claims_fig, use_container_width=True)

    with colH:
        credit_fig = fig_lines(
            {
                "HY OAS": hy_oas,
            },
            "Credit Stress — High Yield OAS",
            "%",
            last_n=504,
        )
        st.plotly_chart(credit_fig, use_container_width=True)

# ============================================================
# TAB 2: MULTI-ASSET
# ============================================================
asset_rows = []
asset_metrics_map = {}

if not prices.empty:
    for asset_name, ticker in asset_map.items():
        if ticker in prices.columns:
            met = asset_metrics(prices[ticker])
            if met:
                asset_metrics_map[asset_name] = met
                row = {"자산": asset_name, "Ticker": ticker, "분류": ASSET_GROUP[asset_name], **met}
                asset_rows.append(row)

asset_df = pd.DataFrame(asset_rows)

with tab2:
    st.subheader("자산별 가격·추세·과매도 상태")

    if asset_df.empty:
        st.warning("시장가격 데이터를 불러오지 못했습니다.")
    else:
        show_cols = [
            "자산", "Ticker", "Price", "1M %", "3M %", "6M %", "1Y %",
            "RSI14", "1Y Drawdown %", "Oversold Score", "MA200 Trend"
        ]
        st.dataframe(
            asset_df[show_cols].style.format({
                "Price": "{:,.2f}",
                "1M %": "{:+.2f}%",
                "3M %": "{:+.2f}%",
                "6M %": "{:+.2f}%",
                "1Y %": "{:+.2f}%",
                "RSI14": "{:.1f}",
                "1Y Drawdown %": "{:+.2f}%",
                "Oversold Score": "{:.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Oversold Score: 최근 252거래일 기준 D20·D60 하위 20%, D200 하위 25%, RSI≤35를 각각 1점으로 합산(0~4). "
            "표본 126일 미만이면 계산하지 않습니다."
        )

        normalized = pd.DataFrame()
        for asset_name, ticker in asset_map.items():
            if ticker in prices.columns:
                s = prices[ticker].dropna()
                s = s[s.index >= s.index.max() - pd.Timedelta(days=365)]
                if len(s):
                    normalized[asset_name] = s / s.iloc[0] * 100

        if not normalized.empty:
            fig = go.Figure()
            for c in normalized.columns:
                fig.add_trace(go.Scatter(x=normalized.index, y=normalized[c], name=c, mode="lines"))
            fig.update_layout(
                title="최근 1년 상대성과 (시작=100)",
                height=430,
                hovermode="x unified",
                legend=dict(orientation="h"),
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 3: ENTRY SIGNALS
# ============================================================
with tab3:
    st.subheader("중단기 / 장기 투자 참고판")

    if asset_df.empty:
        st.warning("가격 데이터가 없어 진입환경을 계산할 수 없습니다.")
    else:
        signal_rows = []
        for _, r in asset_df.iterrows():
            group = r["분류"]
            sig = price_signal_text(r, group)
            rec = recommendation_text(r["자산"], group, r, macro_bias, macro_regime)

            # Different interpretation horizons
            if group == "Equity":
                long_view = (
                    "장기추세 유지" if r["MA200 Trend"] == "상승"
                    else "장기추세 약화/미확인"
                )
            elif group == "Bond":
                long_view = (
                    "채권가격 장기추세 우호" if r["MA200 Trend"] == "상승"
                    else "채권가격 장기추세 약세/미확인"
                )
            else:
                long_view = (
                    "금 장기추세 우호" if r["MA200 Trend"] == "상승"
                    else "금 장기추세 약세/미확인"
                )

            signal_rows.append({
                "자산": r["자산"],
                "거시국면": macro_regime,
                "중단기 Macro Bias": macro_bias,
                "가격신호": sig,
                "Oversold": r["Oversold Score"],
                "RSI": r["RSI14"],
                "장기관점": long_view,
                "현재 참고": rec,
            })

        signal_df = pd.DataFrame(signal_rows)
        st.dataframe(
            signal_df.style.format({"Oversold": "{:.0f}", "RSI": "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            "해석 원칙: 거시는 '매수 강도/리스크 예산'을 조절하고, 실제 진입은 가격·추세 신호로 확인합니다. "
            "단일 지표 또는 자동 판정만으로 매수·매도를 결정하지 않는 구조입니다."
        )

        st.markdown("#### 자산별 거시 민감도")
        sensitivity = pd.DataFrame([
            ["S&P 500", "성장·기업이익", "10Y 금리, 신용스프레드", "연착륙·이익증가"],
            ["Nasdaq 100", "성장·장기 실적", "실질/장기금리", "물가둔화 + 금리안정"],
            ["Nifty 50", "인도 성장·유동성", "USD/INR, RBI, 유가", "미국 거시만으로 불충분"],
            ["KOSPI", "수출·반도체·글로벌 경기", "USD/KRW, 외국인 수급, 한국 금리", "미국 거시 + 한국 변수 필요"],
            ["US 10Y Treasury ETF", "디스인플레이션·성장둔화", "10Y 수익률", "금리 고점/하락"],
            ["US Long Treasury ETF", "침체·디스인플레이션", "30Y 수익률·기간프리미엄", "금리 하락 시 민감도 큼"],
            ["Gold", "실질금리·달러·불확실성", "실질금리·USD", "실질금리 하락/위험회피"],
        ], columns=["자산", "주요 동력", "핵심 확인", "유리한 전형적 환경"])
        st.dataframe(sensitivity, use_container_width=True, hide_index=True)

# ============================================================
# TAB 4: CONSENSUS
# ============================================================
with tab4:
    st.subheader("컨센서스 서프라이즈 — 선택 입력")

    st.write(
        "FRED는 실제 경제지표 시계열에 강하지만 시장 컨센서스 데이터는 제공하지 않습니다. "
        "신뢰할 수 있는 별도 소스에서 받은 컨센서스를 CSV로 넣어 단기 서프라이즈를 관리합니다."
    )

    sample = pd.DataFrame({
        "release_date": ["2026-08-01"],
        "indicator": ["Core CPI MoM"],
        "actual": [0.2],
        "consensus": [0.2],
        "previous": [0.3],
    })
    st.download_button(
        "컨센서스 CSV 예시 다운로드",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="consensus_template.csv",
        mime="text/csv",
    )

    if consensus_file is not None:
        try:
            con = pd.read_csv(consensus_file)
            required = {"release_date", "indicator", "actual", "consensus"}
            if not required.issubset(con.columns):
                st.error(f"필수 열이 없습니다: {sorted(required)}")
            else:
                con["release_date"] = pd.to_datetime(con["release_date"], errors="coerce")
                con["surprise"] = pd.to_numeric(con["actual"], errors="coerce") - pd.to_numeric(con["consensus"], errors="coerce")
                con = con.sort_values("release_date", ascending=False)
                st.dataframe(con, use_container_width=True, hide_index=True)

                # Simple recent surprise breadth; sign is not automatically "good/bad"
                recent = con.head(12).copy()
                st.caption(
                    "주의: Surprise의 +/−는 '시장에 좋다/나쁘다'가 아닙니다. "
                    "예: CPI 상방 surprise와 고용 상방 surprise는 시기별 시장 해석이 다를 수 있습니다."
                )
        except Exception as e:
            st.error(f"CSV 읽기 실패: {e}")
    else:
        st.info("좌측 사이드바에서 컨센서스 CSV를 올리면 이 탭에서 Actual vs Consensus를 함께 볼 수 있습니다.")

# ============================================================
# TAB 5: RAW / DIAGNOSTICS
# ============================================================
with tab5:
    st.subheader("데이터 진단")

    diagnostics = []
    for name, s in fred.items():
        x = s.dropna()
        diagnostics.append({
            "데이터": name,
            "FRED Series": FRED_SERIES[name],
            "최신 관측일": x.index[-1].date().isoformat() if len(x) else None,
            "최신값": x.iloc[-1] if len(x) else np.nan,
            "관측수": len(x),
        })
    st.dataframe(pd.DataFrame(diagnostics), use_container_width=True, hide_index=True)

    if not prices.empty:
        md = []
        for name, ticker in asset_map.items():
            if ticker in prices.columns:
                x = prices[ticker].dropna()
                md.append({
                    "자산": name,
                    "Ticker": ticker,
                    "최신 가격일": x.index[-1].date().isoformat() if len(x) else None,
                    "최신값": x.iloc[-1] if len(x) else np.nan,
                    "관측수": len(x),
                })
        st.dataframe(pd.DataFrame(md), use_container_width=True, hide_index=True)

    st.warning(
        "경제 데이터는 발표 후 수정될 수 있습니다. FRED의 최신 시계열은 수정된 과거값을 포함할 수 있으므로, "
        "'당시 시장이 실제로 알고 있던 값(vintage)'을 엄밀히 백테스트하려면 ALFRED/real-time vintage 데이터가 필요합니다."
    )

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "데이터: FRED API(거시) + yfinance/Yahoo Finance 공개 시장데이터(가격). "
    "이 앱의 자동 판정은 정보 정리용 휴리스틱이며 투자성과를 보장하지 않습니다."
)
