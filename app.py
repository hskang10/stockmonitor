import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# 1. 페이지 최적화 설정
st.set_page_config(
    page_title="Gems 3.0 Master Monitor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 현대적이고 세련된 UI 스타일 인젝션 (다크/라이트 하이브리드 가독성 최적화)
st.markdown("""
    <style>
    /* 전체 대시보드 백그라운드 폰트 두께 조율 */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* 헤더 스타일 고도화 */
    .main-title {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.05rem;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 50%, #2ECC71 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem !important;
    }
    
    /* 세련된 메트릭 카드 */
    .metric-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        border-color: rgba(128, 128, 128, 0.25);
    }
    
    /* 섹션 가로 절취선 고도화 */
    hr {
        margin: 1.5rem 0 !important;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(128,128,128,0), rgba(128,128,128,0.4), rgba(128,128,128,0));
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
    
    # 전일 종가 대비 상승률 (%)
    daily_return = ((current_price - previous_price) / previous_price) * 100
    
    # 기간별 이동평균선 및 이격도(Disparity) 동시 연산 (소수점 첫째 자리 제한)
    periods = [20, 60, 120, 200]
    disparities = {}
    for p in periods:
        ma = df['Close'].rolling(window=p).mean().iloc[-1]
        disparities[f"{p}일 이격도"] = round((current_price / ma) * 100, 1)
    
    # 14일 RSI 연산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi_14 = 100 - (100 / (1 + rs))
    current_rsi = rsi_14.iloc[-1]
    
    # 마스터 딕셔너리 구조화 출력
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
    return 50, "NEUTRAL (ERROR OVERRIDE)"

# ==========================================
# 5. 수동 설정 사이드바 최적화 (S&P 500 Forward P/E만 보존)
# ==========================================
st.sidebar.header("⚙️ 매크로 수동 캘리브레이션")
st.sidebar.markdown("외부 데이터 보안 규격에 따른 실시간 수동 동기화 필드")
forward_pe = st.sidebar.slider("S&P 500 Forward P/E", 15.0, 25.0, 21.2, 0.1)

# ==========================================
# 6. 데이터 병렬 동기화 및 CNN 크롤링 파이프라인 가동
# ==========================================
with st.spinner("⏳ 실시간 연동 데이터 팩킹 및 연산 엔진 예열 중..."):
    # CNN 실시간 동기화
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

# ==========================================
# 7. Gems 3.0 규칙 기반 진입 조건 판정 백엔드 엔진
# ==========================================
def evaluate_gems_signals(category_tables, cnn_fg):
    signals = {}
    
    vix_val = category_tables.get("변동성지수").loc["CBOE VIX", "현재 수치"] if "변동성지수" in category_tables else 0.0
    usdkrw_val = category_tables.get("통화").loc["원/달러 환율", "현재 수치"] if "통화" in category_tables else 0.0
    
    # 1) S&P 500 판정
    if "주요지수" in category_tables and "S&P 500" in category_tables["주요지수"].index:
        spx = category_tables["주요지수"].loc["S&P 500"]
        spx_disp = spx["200일 이격도"]
        spx_rsi = spx["RSI (14일)"]
        
        trigger_active = spx_disp <= 101.0
        filter_met = (spx_rsi <= 40.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "유동성 위기 오버라이드 (VIX > 35)", "color": "#E67E22", "action": "매수 보류 & 예비현금 확보"}
            elif usdkrw_val >= 1400.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "고환율 방어 버퍼 작동 (환율 >= 1400)", "color": "#E67E22", "action": "기계적 매수 1회 강제 지연"}
            else:
                signals["S&P 500"] = {"status": "🟢 BUY", "reason": f"200일 이격도 {spx_disp}% / RSI {spx_rsi}", "color": "#2ECC71", "action": "가용 현금의 20% 집행"}
        else:
            signals["S&P 500"] = {"status": "⚪ HOLD", "reason": "진입 조건 영역 미달 (상단 대기)", "color": "#95A5A6", "action": "관망 및 비중 유지"}

    # 2) 나스닥 100 판정
    if "주요지수" in category_tables and "나스닥 100" in category_tables["주요지수"].index:
        ndx = category_tables["주요지수"].loc["나스닥 100"]
        ndx_disp = ndx["200일 이격도"]
        ndx_rsi = ndx["RSI (14일)"]
        
        trigger_active = ndx_disp <= 102.0
        filter_met = (ndx_rsi <= 38.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "유동성 위기 오버라이드 (VIX > 35)", "color": "#E67E22", "action": "매수 보류 & 예비현금 확보"}
            elif usdkrw_val >= 1400.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "고환율 방어 버퍼 작동 (환율 >= 1400)", "color": "#E67E22", "action": "기계적 매수 1회 강제 지연"}
            else:
                signals["나스닥 100"] = {"status": "🟢 BUY", "reason": f"200일 이격도 {ndx_disp}% / RSI {ndx_rsi}", "color": "#2ECC71", "action": "가용 현금의 20% 집행"}
        else:
            signals["나스닥 100"] = {"status": "⚪ HOLD", "reason": "진입 조건 영역 미달 (상단 대기)", "color": "#95A5A6", "action": "관망 및 비중 유지"}

    # 3) 인도 니프티 50 판정 (독립 필터)
    if "주요지수" in category_tables and "인도 니프티 50" in category_tables["주요지수"].index:
        nifty = category_tables["주요지수"].loc["인도 니프티 50"]
        nifty_disp120 = nifty["120일 이격도"]
        nifty_rsi = nifty["RSI (14일)"]
        
        trigger_active = nifty_disp120 <= 101.0
        filter_met = (nifty_rsi <= 42.0) or (nifty["120일 이격도"] <= 98.0)
        
        if trigger_active and filter_met:
            signals["인도 니프티 50"] = {"status": "🟢 BUY", "reason": f"인도 독립 필터 (이격 {nifty_disp120}% / RSI {nifty_rsi})", "color": "#2ECC71", "action": "가용 현금의 20% 즉각 진입"}
        else:
            signals["인도 니프티 50"] = {"status": "⚪ HOLD", "reason": "인도 고성장 추세선 지지 중", "color": "#95A5A6", "action": "관망 및 비중 유지"}

    # 4) 코스피 판정
    if "주요지수" in category_tables and "코스피" in category_tables["주요지수"].index:
        kospi = category_tables["주요지수"].loc["코스피"]
        kospi_disp60 = kospi["60일 이격도"]
        kospi_rsi = kospi["RSI (14일)"]
        
        trigger_active = kospi_disp60 < 100.0
        filter_met = kospi_rsi <= 35.0
        
        if trigger_active and filter_met:
            signals["코스피"] = {"status": "🟢 BUY", "reason": f"60일선 붕괴 역추세 바닥 (RSI {kospi_rsi})", "color": "#2ECC71", "action": "별동대 예산 40% 투입 & 스톱로스"}
        else:
            signals["코스피"] = {"status": "⚪ HOLD", "reason": "스윙 과매도 바닥 미충족", "color": "#95A5A6", "action": "관망 (잡거래 철저 금지)"}

    # 5) 미국 30년 국채금리 기반 판정
    if "미국국채금리" in category_tables and "미국 30년 국채금리" in category_tables["미국국채금리"].index:
        tyx = category_tables["미국국채금리"].loc["미국 30년 국채금리"]
        tyx_disp120 = tyx["120일 이격도"]
        tyx_rsi = tyx["RSI (14일)"]
        
        trigger_active = tyx_disp120 >= 105.0
        filter_met = tyx_rsi >= 65.0
        
        if trigger_active and filter_met:
            signals["미국 30년 국채금리"] = {"status": "🟢 BUY", "reason": f"30년 금리 발작 (이격 {tyx_disp120}% / RSI {tyx_rsi})", "color": "#2ECC71", "action": "국채 배정 예산 30% 실행"}
        else:
            signals["미국 30년 국채금리"] = {"status": "⚪ HOLD", "reason": "금리 추세 영역 내 정상 궤적", "color": "#95A5A6", "action": "관망 및 국채 배당 재투자"}

    return signals

# ==========================================
# 8. [대시보드 1부] 수동 캘리브레이션 지표 및 실시간 경보 표기 (CSS 입체 카드 개편)
# ==========================================
st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-top:1rem; margin-bottom:0.5rem;">📊 1부. 실시간 독점 매크로 센서</p>', unsafe_allow_html=True)

vix_val = category_tables.get("변동성지수").loc["CBOE VIX", "현재 수치"] if "변동성지수" in category_tables else 0.0
usdkrw_val = category_tables.get("통화").loc["원/달러 환율", "현재 수치"] if "통화" in category_tables else 0.0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <span style="font-size:0.9rem; font-weight:600; opacity:0.7;">CNN Fear & Greed Index</span>
            <div style="font-size:1.8rem; font-weight:800; margin-top:5px;">{cnn_fg} <span style="font-size:1rem; font-weight:600; color:#FFA500;">pts</span></div>
            <span style="font-size:0.8rem; font-weight:500; opacity:0.6;">상태: {cnn_rating}</span>
        </div>
    """, unsafe_allow_html=True)

with col2:
    vix_badge = "🚨 과열 공포" if vix_val >= 35.0 else "✅ 정상 변동성"
    vix_badge_color = "#E74C3C" if vix_val >= 35.0 else "#2ECC71"
    st.markdown(f"""
        <div class="metric-card">
            <span style="font-size:0.9rem; font-weight:600; opacity:0.7;">CBOE VIX Index</span>
            <div style="font-size:1.8rem; font-weight:800; margin-top:5px;">{vix_val:.2f} <span style="font-size:1rem; font-weight:600; color:#FFA500;">pts</span></div>
            <span style="font-size:0.8rem; font-weight:700; color:{vix_badge_color};">{vix_badge}</span>
        </div>
    """, unsafe_allow_html=True)

with col3:
    exchange_badge = "🚨 고환율 위험" if usdkrw_val >= 1400.0 else "✅ 정상 환율 범위"
    exchange_badge_color = "#E74C3C" if usdkrw_val >= 1400.0 else "#2ECC71"
    st.markdown(f"""
        <div class="metric-card">
            <span style="font-size:0.9rem; font-weight:600; opacity:0.7;">원/달러 실시간 조율</span>
            <div style="font-size:1.8rem; font-weight:800; margin-top:5px;">{usdkrw_val:,.1f} <span style="font-size:1rem; font-weight:600; color:#FFA500;">원</span></div>
            <span style="font-size:0.8rem; font-weight:700; color:{exchange_badge_color};">{exchange_badge}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================
# 9. [대시보드 2부] 5대 마스터 자산 기계적 진입 가이드 (글래스모피즘 아우라 광원 카드 개편)
# ==========================================
st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:1rem;">⚡ 2부. Gems 3.0 실시간 통합 실행 시그널</p>', unsafe_allow_html=True)

gems_signals = evaluate_gems_signals(category_tables, cnn_fg)

card_cols = st.columns(5)
for i, (asset_name, sig) in enumerate(gems_signals.items()):
    with card_cols[i]:
        # 기계적 액션 시그널(BUY)일 경우 테두리에 녹색 아우라 발광 효과(Glow) 적용하여 직관성 극대화
        shadow_style = f"box-shadow: 0 0 20px rgba(46, 204, 113, 0.35);" if sig['status'] == "🟢 BUY" else "box-shadow: 0 4px 12px rgba(0,0,0,0.1);"
        st.markdown(
            f"""
            <div style="
                border: 2px solid {sig['color']}; 
                border-radius: 14px; 
                padding: 18px; 
                text-align: center; 
                background: rgba(128,128,128,0.06);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                min-height: 230px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                {shadow_style}
                transition: all 0.3s ease;
            ">
                <div>
                    <h5 style="margin: 0; font-size: 1.1rem; font-weight: 700; opacity: 0.95;">{asset_name}</h5>
                    <div style="font-size: 1.7rem; font-weight: 900; color: {sig['color']}; margin-top: 10px; letter-spacing: -0.05rem;">
                        {sig['status']}
                    </div>
                    <p style="font-size: 0.8rem; margin-top: 12px; line-height: 1.4; opacity: 0.75; font-weight: 500; height: 45px; overflow: hidden;">
                        <b>근거:</b> {sig['reason']}
                    </p>
                </div>
                <div style="
                    font-size: 0.85rem; 
                    font-weight: 700; 
                    background-color: {sig['color']}; 
                    color: #FFFFFF; 
                    padding: 8px 5px; 
                    border-radius: 8px;
                    margin-top: 15px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                ">
                    {sig['action']}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

st.markdown("<br><hr>", unsafe_allow_html=True)

# ==========================================
# 10. [대시보드 3부] 13대 지수 카테고리별 데이터 그리드 렌더링
# ==========================================
st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:1rem;">📋 3부. 글로벌 자산군 다중 이격도 & 과열도 매트릭스</p>', unsafe_allow_html=True)

def highlight_returns(val):
    if isinstance(val, (int, float)):
        if val > 0:
            color = '#FF6B6B'  # 다크/라이트 하이브리드 고대비 로즈 레드
        elif val < 0:
            color = '#58A6FF'  # 가시성 높은 형광 스카이 블루
        else:
            color = 'inherit'
        return f'color: {color}; font-weight: bold;'
    return ''

for category, table in category_tables.items():
    with st.expander(f"📊 {category} 데이터 명세 보기", expanded=True):
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
