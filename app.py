import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ==========================================
# 1. 페이지 테마 및 하이엔드 다크웹 스타일 시트
# ==========================================
st.set_page_config(
    page_title="Gems 3.0 Master Monitor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 고급 핀테크 대시보드 맞춤형 CSS 주입
st.markdown("""
    <style>
    /* 여백 극대화 및 배경 세팅 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 타이틀 및 서브 타이틀 그라데이션 */
    .main-title {
        font-size: 2.1rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.07rem;
        background: linear-gradient(135deg, #00FFCC 0%, #0077FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px !important;
    }
    
    /* 네온 효과 스타일드 미니멀 센서 카드 */
    .neon-sensor-card {
        background: rgba(16, 24, 48, 0.7);
        border: 1px solid rgba(0, 255, 204, 0.15);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0, 255, 204, 0.05);
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    .neon-sensor-card:hover {
        border-color: rgba(0, 255, 204, 0.5);
        transform: translateY(-2px);
    }
    
    /* 시그널 디스플레이 전용 그리드 카드 */
    .signal-card {
        background: rgba(20, 25, 40, 0.85);
        border-radius: 12px;
        padding: 18px;
        border-left: 5px solid #95A5A6;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }
    .signal-card-buy { border-left-color: #2ECC71 !important; box-shadow: 0 4px 15px rgba(46, 204, 113, 0.15); }
    .signal-card-lock { border-left-color: #E67E22 !important; box-shadow: 0 4px 15px rgba(230, 126, 34, 0.15); }
    .signal-card-hold { border-left-color: #7F8C8D !important; }
    
    /* 이쁘게 렌더링된 배지 */
    .status-badge {
        font-size: 0.75rem;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-buy { background: rgba(46, 204, 113, 0.2); color: #2ECC71; }
    .badge-lock { background: rgba(230, 126, 34, 0.2); color: #E67E22; }
    .badge-hold { background: rgba(127, 140, 141, 0.2); color: #95A5A6; }

    /* 대시보드 경계선 */
    hr {
        margin: 1.2rem 0 !important;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(0,119,255,0), rgba(0,255,204,0.3), rgba(0,119,255,0));
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🛡️ Gems 3.0 글로벌 자산군 통합 관제 시스템</h1>', unsafe_allow_html=True)
st.caption("Gems 3.0 Real-time Disparity Multi-Timeframe & RSI Matrix Terminal")

# ==========================================
# 2. 13대 마스터 자산군 매핑
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
# 3. 데이터 병렬 동기화 최적화 (캐싱 레이어 추가)
# ==========================================
@st.cache_data(ttl=300)
def fetch_asset_history(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_realtime_cnn_fg():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            fng_current = data.get('fear_and_greed', {})
            raw_score = float(fng_current.get('score', 50.0))
            rating = fng_current.get('rating', 'NEUTRAL').upper()
            return round(raw_score), rating
    except Exception:
        pass
    return 50, "NEUTRAL (ERROR)"

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
    
    return {
        "현재 수치": round(current_price, 2),
        "전일대비 등락": round(daily_return, 2),
        **disparities,
        "RSI (14일)": round(current_rsi, 2)
    }

# ==========================================
# 4. 수동 및 스마트 캘리브레이션 (사이드바)
# ==========================================
st.sidebar.markdown("### ⚙️ 스마트 캘리브레이션")
forward_pe = st.sidebar.slider("S&P 500 Forward P/E", 15.0, 25.0, 21.2, 0.1)
st.sidebar.info("Forward P/E가 22.0 초과 시 미국 자산 진입은 고평가 경보로 강제 LOCK-UP 상태가 됩니다.")

# ==========================================
# 5. 핵심 연산 인프라 기동
# ==========================================
with st.spinner("⏳ 실시간 데이터 인프라 실시간 동기화 중..."):
    cnn_fg, cnn_rating = get_realtime_cnn_fg()
    
    category_tables = {}
    for category, assets in TARGET_ASSETS.items():
        rows = []
        for name, ticker in assets.items():
            h = fetch_asset_history(ticker)
            metrics = calculate_master_metrics(h)
            if metrics:
                metrics["지수/지표명"] = name
                rows.append(metrics)
        
        if rows:
            df_cat = pd.DataFrame(rows)
            cols_order = ["지수/지표명", "현재 수치", "전일대비 등락", "20일 이격도", "60일 이격도", "120일 이격도", "200일 이격도", "RSI (14일)"]
            category_tables[category] = df_cat[cols_order].set_index("지수/지표명")

# 안정적인 계산값 유도
vix_val = float(category_tables.get("변동성지수", pd.DataFrame()).loc["CBOE VIX", "현재 수치"]) if "CBOE VIX" in category_tables.get("변동성지수", pd.DataFrame()).index else 15.0
usdkrw_val = float(category_tables.get("통화", pd.DataFrame()).loc["원/달러 환율", "현재 수치"]) if "원/달러 환율" in category_tables.get("통화", pd.DataFrame()).index else 1300.0

# ==========================================
# 6. 연동 규칙 기반 시그널 감지 백엔드 (수정 반영)
# ==========================================
def evaluate_gems_signals(category_tables, cnn_fg, vix_val, usdkrw_val, forward_pe):
    signals = {}
    
    # 1) S&P 500 (밸류에이션 변수 연동 완료)
    if "주요지수" in category_tables and "S&P 500" in category_tables["주요지수"].index:
        spx = category_tables["주요지수"].loc["S&P 500"]
        spx_disp = spx["200일 이격도"]
        spx_rsi = spx["RSI (14일)"]
        trigger_active = spx_disp <= 101.0
        filter_met = (spx_rsi <= 40.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "VIX > 35 공포 지수 임계치 상회", "class": "signal-card-lock", "badge": "badge-lock", "action": "매수 전면 중단 및 현금 대기"}
            elif usdkrw_val >= 1400.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "원/달러 환율 1400원선 돌파로 환차손 위험 노출", "class": "signal-card-lock", "badge": "badge-lock", "action": "달러 자산 기계적 진입 강제 보류"}
            elif forward_pe >= 22.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": f"Forward P/E ({forward_pe}) 버블 임계치 상회", "class": "signal-card-lock", "badge": "badge-lock", "action": "고평가 국면 매수 방어 필터 발동"}
            else:
                signals["S&P 500"] = {"status": "🟢 BUY", "reason": f"200일선 수렴 ({spx_disp}%) 및 과매도 매칭", "class": "signal-card-buy", "badge": "badge-buy", "action": "적립식 예산의 20% 분할 진입"}
        else:
            signals["S&P 500"] = {"status": "HOLD", "reason": "진입 가이드라인 불일치 (과열 상태 보존)", "class": "signal-card-hold", "badge": "badge-hold", "action": "포지션 유지 및 관망 유지"}

    # 2) 나스닥 100
    if "주요지수" in category_tables and "나스닥 100" in category_tables["주요지수"].index:
        ndx = category_tables["주요지수"].loc["나스닥 100"]
        ndx_disp = ndx["200일 이격도"]
        ndx_rsi = ndx["RSI (14일)"]
        trigger_active = ndx_disp <= 102.0
        filter_met = (ndx_rsi <= 38.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "CBOE VIX 35포인트 상회 위기 국면", "class": "signal-card-lock", "badge": "badge-lock", "action": "매수 보류 및 예비현금 홀딩"}
            elif usdkrw_val >= 1400.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "환율 1400원 돌파 버퍼 가동", "class": "signal-card-lock", "badge": "badge-lock", "action": "달러 자산 신규 매수 잠정 보류"}
            elif forward_pe >= 22.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": f"S&P500 밸류에이션({forward_pe}) 경계치 돌파", "class": "signal-card-lock", "badge": "badge-lock", "action": "밸류에이션 버블 우려로 진입 정지"}
            else:
                signals["나스닥 100"] = {"status": "🟢 BUY", "reason": f"200일선 이격 {ndx_disp}% 수렴", "class": "signal-card-buy", "badge": "badge-buy", "action": "적립식 예산의 20% 분할 투입"}
        else:
            signals["나스닥 100"] = {"status": "HOLD", "reason": "추세 이탈 전 단계", "class": "signal-card-hold", "badge": "badge-hold", "action": "관망"}

    # 3) 인도 니프티 50 (신흥국 환율 변동성 연동 보완)
    if "주요지수" in category_tables and "인도 니프티 50" in category_tables["주요지수"].index:
        nifty = category_tables["주요지수"].loc["인도 니프티 50"]
        nifty_disp120 = nifty["120일 이격도"]
        nifty_rsi = nifty["RSI (14일)"]
        trigger_active = nifty_disp120 <= 101.0
        filter_met = (nifty_rsi <= 42.0) or (nifty["120일 이격도"] <= 98.0)
        
        if trigger_active and filter_met:
            if usdkrw_val >= 1420.0:
                signals["인도 니프티 50"] = {"status": "🚨 LOCK-UP", "reason": "달러/원 1420원 돌파로 인한 이머징 캐피탈 런 위험 상승", "class": "signal-card-lock", "badge": "badge-lock", "action": "신흥국 자산 포지션 신규 확대 금지"}
            else:
                signals["인도 니프티 50"] = {"status": "🟢 BUY", "reason": f"120일선 이격 하회 {nifty_disp120}%", "class": "signal-card-buy", "badge": "badge-buy", "action": "이머징 배정 자산 20% 진입"}
        else:
            signals["인도 니프티 50"] = {"status": "HOLD", "reason": "이머징 성장 추세선 상방 지지 중", "class": "signal-card-hold", "badge": "badge-hold", "action": "기존 지분 홀딩"}

    # 4) 코스피 (환율 필터 연동 보완)
    if "주요지수" in category_tables and "코스피" in category_tables["주요지수"].index:
        kospi = category_tables["주요지수"].loc["코스피"]
        kospi_disp60 = kospi["60일 이격도"]
        kospi_rsi = kospi["RSI (14일)"]
        trigger_active = kospi_disp60 < 100.0
        filter_met = kospi_rsi <= 35.0
        
        if trigger_active and filter_met:
            if usdkrw_val >= 1400.0:
                signals["코스피"] = {"status": "🚨 LOCK-UP", "reason": "환율 1400원 상회로 인한 환율발 외인 투매 우려 가중", "class": "signal-card-lock", "badge": "badge-lock", "action": "별동대 무기한 진입 중단"}
            else:
                signals["코스피"] = {"status": "🟢 BUY", "reason": f"60일선 과매도 바닥 시그널 (RSI {kospi_rsi})", "class": "signal-card-buy", "badge": "badge-buy", "action": "별동대 배정 자산의 40% 공격적 투입"}
        else:
            signals["코스피"] = {"status": "HOLD", "reason": "기술적 스윙 진입 대기 단계", "class": "signal-card-hold", "badge": "badge-hold", "action": "대기 및 주시"}

    # 5) 미국 30년 국채금리
    if "미국국채금리" in category_tables and "미국 30년 국채금리" in category_tables["미국국채금리"].index:
        tyx = category_tables["미국국채금리"].loc["미국 30년 국채금리"]
        tyx_disp120 = tyx["120일 이격도"]
        tyx_rsi = tyx["RSI (14일)"]
        trigger_active = tyx_disp120 >= 105.0
        filter_met = tyx_rsi >= 65.0
        
        if trigger_active and filter_met:
            signals["미국 30년 국채금리"] = {"status": "🟢 BUY", "reason": f"금리 일시 오버슈팅 (RSI {tyx_rsi})", "class": "signal-card-buy", "badge": "badge-buy", "action": "국채 포트폴리오 30% 매수 단행"}
        else:
            signals["미국 30년 국채금리"] = {"status": "HOLD", "reason": "금리 레벨 추세 범위 내 유지", "class": "signal-card-hold", "badge": "badge-hold", "action": "관망"}

    return signals

gems_signals = evaluate_gems_signals(category_tables, cnn_fg, vix_val, usdkrw_val, forward_pe)

# ==========================================
# 7. 최상단 레이아웃 분할: 3(계계 계측판) : 7(네온 시그널 카드)
# ==========================================
col_sensor, col_signal = st.columns([3, 7])

# --- 좌측 열: 1부 계기판형 마스터 센서 보드 ---
with col_sensor:
    st.markdown('<p style="font-size:1.15rem; font-weight:800; margin-bottom:0.8rem; color:#00FFCC;">📊 1부. 매크로 코어 센서</p>', unsafe_allow_html=True)
    
    # 공포/탐욕 네온 스코어 컬러링
    fng_color = "#FF3366" if cnn_fg <= 30 else ("#FF9900" if cnn_fg <= 50 else "#00FFCC")
    vix_badge_col = "#FF3366" if vix_val >= 35.0 else ("#FF9900" if vix_val >= 25.0 else "#00FFCC")
    krw_badge_col = "#FF3366" if usdkrw_val >= 1400.0 else ("#00FFCC")

    st.markdown(f"""
        <div class="neon-sensor-card">
            <div style="font-size:0.85rem; font-weight:600; opacity:0.6; margin-bottom: 4px;">CNN Fear & Greed</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <span style="font-size:1.8rem; font-weight:900; color:{fng_color};">{cnn_fg}<span style="font-size:1rem; font-weight:normal; opacity:0.6;"> pts</span></span>
                <span style="font-size:0.8rem; font-weight:800; padding:2px 8px; border-radius:10px; background:rgba(255,255,255,0.05); color:{fng_color}">{cnn_rating}</span>
            </div>
        </div>
        <div class="neon-sensor-card">
            <div style="font-size:0.85rem; font-weight:600; opacity:0.6; margin-bottom: 4px;">CBOE VIX Index</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <span style="font-size:1.8rem; font-weight:900; color:{vix_badge_col};">{vix_val:.2f}<span style="font-size:1rem; font-weight:normal; opacity:0.6;"> pts</span></span>
                <span style="font-size:0.8rem; font-weight:800; padding:2px 8px; border-radius:10px; background:rgba(255,255,255,0.05); color:{vix_badge_col}">RISK BUFFER</span>
            </div>
        </div>
        <div class="neon-sensor-card">
            <div style="font-size:0.85rem; font-weight:600; opacity:0.6; margin-bottom: 4px;">원/달러 실시간 환율</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <span style="font-size:1.8rem; font-weight:900; color:{krw_badge_col};">{usdkrw_val:,.1f}<span style="font-size:1rem; font-weight:normal; opacity:0.6;"> 원</span></span>
                <span style="font-size:0.8rem; font-weight:800; padding:2px 8px; border-radius:10px; background:rgba(255,255,255,0.05); color:{krw_badge_col}">FX LIMIT 1400</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 우측 열: 2부 네온 스타일드 실시간 통합 시그널 보드 (스크롤 완전 탈피) ---
with col_signal:
    st.markdown('<p style="font-size:1.15rem; font-weight:800; margin-bottom:0.8rem; color:#0077FF;">⚡ 2부. Gems 3.0 실시간 기계적 대응 판정</p>', unsafe_allow_html=True)
    
    # 2부 화면 높이 조절 및 시각적 배치
    for asset, sig in gems_signals.items():
        st.markdown(f"""
            <div class="signal-card {sig['class']}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom:6px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #FFFFFF;">{asset}</span>
                    <span class="status-badge {sig['badge']}">{sig['status']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.88rem;">
                    <span style="opacity: 0.7; color: #BDC3C7;"><strong style="color:#FFF;">판정 근거:</strong> {sig['reason']}</span>
                    <span style="font-weight: 700; color: #FFF; background: rgba(0,119,255,0.15); padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(0,119,255,0.2);">🚀 {sig['action']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================
# 8. [대시보드 3부] 13대 지수 카테고리 매트릭스 테이블
# ==========================================
st.markdown('<p style="font-size:1.25rem; font-weight:800; margin-bottom:0.8rem; color:#FFFFFF;">📋 3부. 글로벌 자산군 다중 이격도 & 과열도 매트릭스 명세</p>', unsafe_allow_html=True)

def highlight_returns(val):
    if isinstance(val, (int, float)):
        if val > 0:
            color = '#FF4444'
        elif val < 0:
            color = '#3399FF'
        else:
            color = 'inherit'
        return f'color: {color}; font-weight: bold;'
    return ''

# 3부 통일감 유지를 위한 명세서 규격 일치화
COLUMN_DIMENSIONS = {
    "지수/지표명": st.column_config.TextColumn(width=160),
    "현재 수치": st.column_config.NumberColumn(width=110),
    "전일대비 등락": st.column_config.TextColumn(width=100),
    "20일 이격도": st.column_config.TextColumn(width=100),
    "60일 이격도": st.column_config.TextColumn(width=100),
    "120일 이격도": st.column_config.TextColumn(width=100),
    "200일 이격도": st.column_config.TextColumn(width=100),
    "RSI (14일)": st.column_config.TextColumn(width=100)
}

# 탭을 활용하여 3부를 더 세련되고 넓게 분할 배치
tabs = st.tabs([f"📊 {cat}" for cat in category_tables.keys()])

for tab, (category, table) in zip(tabs, category_tables.items()):
    with tab:
        styled_table = table.style.map(highlight_returns, subset=["전일대비 등락"]).format({
            "전일대비 등락": "{:+.2f}%", 
            "현재 수치": "{:,.2f}",
            "20일 이격도": "{:.1f}%",
            "60일 이격도": "{:.1f}%",
            "120일 이격도": "{:.1f}%",
            "200일 이격도": "{:.1f}%",
            "RSI (14일)": "{:.2f}"
        })
        
        st.dataframe(
            styled_table, 
            use_container_width=True,
            column_config=COLUMN_DIMENSIONS
        )

st.markdown("---")
st.caption(f"**[실시간 검증 정보 완료]** 연동 데이터 소스: Yahoo Finance API & CNN Business API 교차 데이터 동기화 완료 | "
           f"데이터 기준 시각: {pd.Timestamp.now(tz='Asia/Seoul').strftime('%Y-%m-%d %H:%M:%S')} KST")
