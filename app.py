import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# 1. 페이지 설정 및 초기화 (가로 넓게 쓰기 적용)
st.set_page_config(
    page_title="Gems 3.0 Master Monitor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 고급 가독성 향상 스타일 인젝션
st.markdown("""
    <style>
    /* 여백 극단적 최적화 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 통합 타이틀 미니멀화 */
    .main-title {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.05rem;
        background: linear-gradient(135deg, #FF6B6B 0%, #2ECC71 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem !important;
    }
    
    /* 초소형 사이드바형 센서 보드 */
    .sensor-box {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 12px 15px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* 컴팩트 구분선 */
    hr {
        margin: 1rem 0 !important;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(128,128,128,0), rgba(128,128,128,0.3), rgba(128,128,128,0));
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🛡️ Gems 3.0 매크로 및 글로벌 지수 통합 관제 시스템</h1>', unsafe_allow_html=True)
st.caption("Gems 3.0 Quantitative Multi-Timeframe Disparity & RSI Matrix")

# ==========================================
# 2. 사령관 지정 13대 마스터 자산군 티커 매핑
# ==========================================
TARGET_ASSETS = {
    "변동성지수": {
        "CBOE VIX": "^VIX",
        "CBOE SKEW": "^SKEW"
    },
    "주요지수": {
        "S&P 500": "^GSPC",
        "나스닥 100": "^NDX",
        "인도 니프티 50": "^NSEI",
        "코스피": "^KS11",
        "필라델피아 반도체": "^SOX"
    },
    "미국국채금리": {
        "미국 10년 국채금리": "^TNX",
        "미국 30년 국채금리": "^TYX"
    },
    "통화": {
        "달러 인덱스": "DX-Y.NYB",
        "원/달러 환율": "KRW=X"
    },
    "기타 매크로": {
        "국제 금 선물": "GC=F",
        "WTI 원유 선물": "CL=F"
    }
}

# ==========================================
# 3. 다중 타임프레임 이격도 및 RSI 통합 연산 엔진
# ==========================================
def calculate_master_metrics(df):
    if df.empty or len(df) < 200:
        return None
    
    current_price = df['Close'].iloc[-1]
    previous_price = df['Close'].iloc[-2]
    daily_return = ((current_price - previous_price) / previous_price) * 100
    
    periods = [20, 60, 120, 200]
    disparities = {}
    for p in periods:
        ma = df['Close'].rolling(window=p).mean().iloc[-1]
        disparities[f"{p}일 이격도"] = round((current_price / ma) * 100, 1)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi_14 = 100 - (100 / (1 + rs))
    current_rsi = rsi_14.iloc[-1]
    
    res = {
        "현재 수치": round(current_price, 2),
        "전일대비 등락": round(daily_return, 2),
        **disparities,
        "RSI (14일)": round(current_rsi, 2)
    }
    return res

# ==========================================
# 4. 실시간 CNN Fear & Greed API 크롤링 엔진
# ==========================================
def get_realtime_cnn_fg():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            fng_current = data.get('fear_and_greed', {})
            raw_score = float(fng_current.get('score', 50.0))
            score = round(raw_score)
            rating = fng_current.get('rating', 'NEUTRAL').upper()
            return score, rating
    except Exception:
        pass
    return 50, "NEUTRAL (ERROR)"

# ==========================================
# 5. 수동 설정 사이드바 최적화 (S&P 500 Forward P/E만 보존)
# ==========================================
st.sidebar.header("⚙️ 매크로 수동 캘리브레이션")
forward_pe = st.sidebar.slider("S&P 500 Forward P/E", 15.0, 25.0, 21.2, 0.1)

# ==========================================
# 6. 데이터 병렬 동기화 및 크롤링 (변수 배치 선언 최상단으로 수정)
# ==========================================
with st.spinner("⏳ 실시간 데이터 인프라 튜닝 중..."):
    cnn_fg, cnn_rating = get_realtime_cnn_fg()
    
    category_tables = {}
    for category, assets in TARGET_ASSETS.items():
        rows = []
        for name, ticker in assets.items():
            t = yf.Ticker(ticker)
            h = t.history(period="1y")
            metrics = calculate_master_metrics(h)
            if metrics:
                metrics["지수/지표명"] = name
                rows.append(metrics)
        
        if rows:
            df_cat = pd.DataFrame(rows)
            cols_order = ["지수/지표명", "현재 수치", "전일대비 등락", "20일 이격도", "60일 이격도", "120일 이격도", "200일 이격도", "RSI (14일)"]
            category_tables[category] = df_cat[cols_order].set_index("지수/지표명")

# --- 에러 원천 차단: 연산 및 화면 렌더링 전에 핵심 데이터 변수 선언 락인(Lock-in) ---
try:
    vix_val = float(category_tables.get("변동성지수").loc["CBOE VIX", "현재 수치"])
except Exception:
    vix_val = 0.0

try:
    usdkrw_val = float(category_tables.get("통화").loc["원/달러 환율", "현재 수치"])
except Exception:
    usdkrw_val = 0.0


# ==========================================
# 7. Gems 3.0 규칙 기반 진입 조건 판정 백엔드 엔진
# ==========================================
def evaluate_gems_signals(category_tables, cnn_fg, vix_val, usdkrw_val):
    signals = {}
    
    # 1) S&P 500
    if "주요지수" in category_tables and "S&P 500" in category_tables["주요지수"].index:
        spx = category_tables["주요지수"].loc["S&P 500"]
        spx_disp = spx["200일 이격도"]
        spx_rsi = spx["RSI (14일)"]
        trigger_active = spx_disp <= 101.0
        filter_met = (spx_rsi <= 40.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "VIX > 35 위기 오버라이드", "color": "#E67E22", "action": "매수 보류 및 예비현금 대기"}
            elif usdkrw_val >= 1400.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "환율 >= 1400원 방어 버퍼", "color": "#E67E22", "action": "기계적 매수 1회 강제 유예"}
            else:
                signals["S&P 500"] = {"status": "🟢 BUY", "reason": f"200일 이격 {spx_disp}% / RSI {spx_rsi}", "color": "#2ECC71", "action": "가용 현금의 20% 진입"}
        else:
            signals["S&P 500"] = {"status": "HOLD", "reason": "진입 기준 미달", "color": "#95A5A6", "action": "관망"}

    # 2) 나스닥 100
    if "주요지수" in category_tables and "나스닥 100" in category_tables["주요지수"].index:
        ndx = category_tables["주요지수"].loc["나스닥 100"]
        ndx_disp = ndx["200일 이격도"]
        ndx_rsi = ndx["RSI (14일)"]
        trigger_active = ndx_disp <= 102.0
        filter_met = (ndx_rsi <= 38.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "VIX > 35 위기 오버라이드", "color": "#E67E22", "action": "매수 보류 및 예비현금 대기"}
            elif usdkrw_val >= 1400.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "환율 >= 1400원 방어 버퍼", "color": "#E67E22", "action": "기계적 매수 1회 강제 유예"}
            else:
                signals["나스닥 100"] = {"status": "🟢 BUY", "reason": f"200일 이격 {ndx_disp}% / RSI {ndx_rsi}", "color": "#2ECC71", "action": "가용 현금의 20% 진입"}
        else:
            signals["나스닥 100"] = {"status": "HOLD", "reason": "진입 기준 미달", "color": "#95A5A6", "action": "관망"}

    # 3) 인도 니프티 50
    if "주요지수" in category_tables and "인도 니프티 50" in category_tables["주요지수"].index:
        nifty = category_tables["주요지수"].loc["인도 니프티 50"]
        nifty_disp120 = nifty["120일 이격도"]
        nifty_rsi = nifty["RSI (14일)"]
        trigger_active = nifty_disp120 <= 101.0
        filter_met = (nifty_rsi <= 42.0) or (nifty["120일 이격도"] <= 98.0)
        
        if trigger_active and filter_met:
            signals["인도 니프티 50"] = {"status": "🟢 BUY", "reason": f"인도 독립 필터 (이격 {nifty_disp120}%)", "color": "#2ECC71", "action": "가용 현금의 20% 즉각 진입"}
        else:
            signals["인도 니프티 50"] = {"status": "HOLD", "reason": "인도 성장추세선 지지 중", "color": "#95A5A6", "action": "관망"}

    # 4) 코스피
    if "주요지수" in category_tables and "코스피" in category_tables["주요지수"].index:
        kospi = category_tables["주요지수"].loc["코스피"]
        kospi_disp60 = kospi["60일 이격도"]
        kospi_rsi = kospi["RSI (14일)"]
        trigger_active = kospi_disp60 < 100.0
        filter_met = kospi_rsi <= 35.0
        
        if trigger_active and filter_met:
            signals["코스피"] = {"status": "🟢 BUY", "reason": f"60일선 붕괴 과매도 (RSI {kospi_rsi})", "color": "#2ECC71", "action": "별동대 40% 투입 & 로스컷"}
        else:
            signals["코스피"] = {"status": "HOLD", "reason": "스윙 과매도 바닥 미충족", "color": "#95A5A6", "action": "관망"}

    # 5) 미국 30년 국채금리
    if "미국국채금리" in category_tables and "미국 30년 국채금리" in category_tables["미국국채금리"].index:
        tyx = category_tables["미국국채금리"].loc["미국 30년 국채금리"]
        tyx_disp120 = tyx["120일 이격도"]
        tyx_rsi = tyx["RSI (14일)"]
        trigger_active = tyx_disp120 >= 105.0
        filter_met = tyx_rsi >= 65.0
        
        if trigger_active and filter_met:
            signals["미국 30년 국채금리"] = {"status": "🟢 BUY", "reason": f"30년 금리 오버슈팅 (RSI {tyx_rsi})", "color": "#2ECC71", "action": "국채 배정 예산 30% 실행"}
        else:
            signals["미국 30년 국채금리"] = {"status": "HOLD", "reason": "금리 추세 영역 정상 유지", "color": "#95A5A6", "action": "관망"}

    return signals


# ==========================================
# 8. [통합 리뉴얼] 최상단 3:7 컴팩트 레이아웃 분할 (구조 정상화 완료)
# ==========================================
left_col, right_col = st.columns([3, 7])

# --- 좌측 열: 1부 초압축 매크로 센서 ---
with left_col:
    st.markdown('<p style="font-size:1.1rem; font-weight:700; margin-bottom:0.8rem;">📊 1부. 매크로 센서 보드</p>', unsafe_allow_html=True)
    
    # 원달러 및 VIX 위험 상태에 따른 컬러 변동 로직
    ex_color = "#E74C3C" if usdkrw_val >= 1400.0 else "#2ECC71"
    vix_color = "#E74C3C" if vix_val >= 35.0 else "#2ECC71"
    
    st.markdown(f"""
        <div class="sensor-box">
            <span style="font-size:0.85rem; font-weight:600; opacity:0.8;">CNN Fear & Greed</span>
            <span style="font-size:1rem; font-weight:800; color:#FFA500;">{cnn_fg} pts <span style="font-size:0.75rem; opacity:0.7;">({cnn_rating})</span></span>
        </div>
        <div class="sensor-box">
            <span style="font-size:0.85rem; font-weight:600; opacity:0.8;">CBOE VIX Index</span>
            <span style="font-size:1rem; font-weight:800; color:{vix_color};">{vix_val:.2f} pts</span>
        </div>
        <div class="sensor-box">
            <span style="font-size:0.85rem; font-weight:600; opacity:0.8;">원/달러 실시간 환율</span>
            <span style="font-size:1rem; font-weight:800; color:{ex_color};">{usdkrw_val:,.1f} 원</span>
        </div>
    """, unsafe_allow_html=True)

# --- 우측 열: 2부 가로형 초슬림 시그널 그리드 (Table화) ---
with right_col:
    st.markdown('<p style="font-size:1.1rem; font-weight:700; margin-bottom:0.8rem;">⚡ 2부. Gems 3.0 실시간 통합 실행 시그널</p>', unsafe_allow_html=True)
    
    # 상단에서 이미 정의 완료된 vix_val, usdkrw_val 주입 연산
    gems_signals = evaluate_gems_signals(category_tables, cnn_fg, vix_val, usdkrw_val)
    
    # 테이블 표출을 위한 Pandas DataFrame 구조화 개편
    signal_rows = []
    for asset, sig in gems_signals.items():
        signal_rows.append({
            "투자 자산군": asset,
            "실행 판정": sig["status"],
            "매칭 근거": sig["reason"],
            "기계적 액션": sig["action"]
        })
    df_signals = pd.DataFrame(signal_rows).set_index("투자 자산군")
    
    # 테이블 셀 스타일링 (BUY에 고대비 연두색 라벨 매핑)
    def style_signal_grid(row):
        color_map = {
            "🟢 BUY": "background-color: rgba(46, 204, 113, 0.25); color: #2ECC71; font-weight: bold; text-align: center;",
            "🚨 LOCK-UP": "background-color: rgba(230, 126, 34, 0.25); color: #E67E22; font-weight: bold; text-align: center;",
            "HOLD": "opacity: 0.6; text-align: center;"
        }
        val = row["실행 판정"]
        return [color_map.get(val, "")] * len(row)
        
    styled_grid = df_signals.style.apply(style_signal_grid, axis=1)
    st.dataframe(styled_grid, use_container_width=True, height=185)

st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================
# 11. [대시보드 3부] 13대 지수 카테고리별 데이터 그리드 렌더링
# ==========================================
st.markdown('<p style="font-size:1.2rem; font-weight:700; margin-bottom:0.8rem;">📋 3부. 글로벌 자산군 다중 이격도 & 과열도 매트릭스</p>', unsafe_allow_html=True)

def highlight_returns(val):
    if isinstance(val, (int, float)):
        if val > 0:
            color = '#FF6B6B'
        elif val < 0:
            color = '#58A6FF'
        else:
            color = 'inherit'
        return f'color: {color}; font-weight: bold;'
    return ''

for category, table in category_tables.items():
    with st.expander(f"📊 {category} 데이터 명세", expanded=True):
        styled_table = table.style.map(highlight_returns, subset=["전일대비 등락"]).format({
            "전일대비 등락": "{:+.2f}%", 
            "현재 수치": "{:,.2f}",
            "20일 이격도": "{:.1f}%",
            "60일 이격도": "{:.1f}%",
            "120일 이격도": "{:.1f}%",
            "200일 이격도": "{:.1f}%",
            "RSI (14일)": "{:.2f}"
        })
        st.dataframe(styled_table, use_container_width=True)

st.markdown("---")
st.caption(f"**[데이터 교차 검증 정보]** 실시간 소스: Yahoo Finance API & CNN Business API 동기화 | "
           f"기준 시각: {pd.Timestamp.now(tz='Asia/Seoul').strftime('%Y-%m-%d %H:%M:%S')} KST")
