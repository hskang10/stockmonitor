import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==========================================
# 1. 페이지 및 스타일 최적화 설정
# ==========================================
st.set_page_config(
    page_title="Gems 3.0 Market Entry Matrix", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .main-title { font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -0.05rem; }
    
    /* 18. 색상 규칙 적용을 위한 CSS 클래스 */
    .card-score-01 { background: rgba(128,128,128,0.05); }
    .card-score-2 { background: rgba(241,196,15,0.1); }
    .card-score-3 { background: rgba(230,126,34,0.1); }
    .card-score-4 { background: rgba(231,76,60,0.1); }
    
    .border-trend-up { border: 2px solid #2ECC71; }
    .border-trend-down { border: 2px solid #E74C3C; }
    
    .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .metric-table { font-size: 0.85rem; }
    
    hr { margin: 1.2rem 0 !important; border: 0; height: 1px; background: linear-gradient(to right, rgba(128,128,128,0), rgba(128,128,128,0.3), rgba(128,128,128,0)); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🛡️ Gems 3.0 글로벌 지수 과매도 진입 대시보드</h1>', unsafe_allow_html=True)
st.caption("SYSTEM_STATUS = CONDITIONALLY_APPROVED | 用途: CASH_DEPLOYMENT_TIMING_ASSISTANT")

# ==========================================
# 2. 마스터 자산 매핑 및 환경 변수
# ==========================================
INDEX_MAP = {
    "S&P 500": "^GSPC",
    "Nasdaq-100": "^NDX",
    "Nifty 50": "^NSEI",
    "KOSPI": "^KS11"
}

# 시뮬레이션을 위한 사이드바 파라미터 (DB 대체용)
st.sidebar.header("⚙️ 14. 현금 및 사이클 상태 주입")
st.sidebar.caption("실제 운용 시 데이터베이스 상태값과 연동됩니다.")
sim_cash_ratio = st.sidebar.slider("현재 가용 현금비중 (CashRatio)", 0.0, 1.0, 1.0, 0.05)
sim_days_since_buy = st.sidebar.number_input("마지막 매수 후 경과일 (DaysSinceLastBuy)", 0, 200, 15)
sim_cycle_invested = st.sidebar.number_input("현재 사이클 누적 투입비중 (%)", 0, 100, 0)
sim_last_score = st.sidebar.slider("마지막 진입 점수", -1, 4, -1)
kospi_auto_enabled = st.sidebar.checkbox("KOSPI 자동매수 활성화", value=False)

# ==========================================
# 3. 데이터 로딩 및 지표 연산 엔진
# ==========================================
@st.cache_data(ttl=300)
def fetch_and_calculate_indicators(name, ticker):
    # 최소 1년(252일) + 200일 이동평균 계산을 위해 3년치 데이터 확보
    df = yf.download(ticker, period="3y", progress=False)
    if df.empty or len(df) < 252:
        return {"상태": "INSUFFICIENT_DATA"}
    
    df = df.copy()
    # 4.1 기본 데이터 무결성 정렬
    df = df[~df.index.duplicated(keep='last')].sort_index()
    
    # 5. 기술적 지표 계산
    df['Ret'] = df['Close'].pct_change()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA200'] = df['Close'].rolling(200).mean()
    
    df['Disp20'] = (df['Close'] / df['MA20']) * 100
    df['Disp60'] = (df['Close'] / df['MA60']) * 100
    df['Disp200'] = (df['Close'] / df['MA200']) * 100
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI14'] = 100 - (100 / (1 + rs))
    
    # 6. 최근 1년 백분위 임계값 (미래정보 방지를 위해 shift(1) 적용)
    df['D20_Q20'] = df['Disp20'].shift(1).rolling(252).quantile(0.20)
    df['D60_Q20'] = df['Disp60'].shift(1).rolling(252).quantile(0.20)
    df['D200_Q25'] = df['Disp200'].shift(1).rolling(252).quantile(0.25)
    
    # 8. 장기 추세 필터
    df['MA200_Slope20'] = (df['MA200'] / df['MA200'].shift(20)) - 1
    df['TrendState'] = np.where(df['MA200_Slope20'] > 0, 'TREND_UP', 'TREND_DOWN')
    
    curr = df.iloc[-1].copy()
    prev = df.iloc[-2].copy()
    
    # 7. 과매도 점수
    p20 = 1 if curr['Disp20'] <= curr['D20_Q20'] else 0
    p60 = 1 if curr['Disp60'] <= curr['D60_Q20'] else 0
    p200 = 1 if curr['Disp200'] <= curr['D200_Q25'] else 0
    prsi = 1 if curr['RSI14'] <= 35 else 0
    
    score = p20 + p60 + p200 + prsi
    
    # 반등 확인 조건 (하락 추세용)
    reversal_confirmed = (curr['RSI14'] > prev['RSI14']) and \
                         (curr['Close'] > curr['MA20']) and \
                         (curr['Close'] > prev['Close'])
                         
    # 4.2 데이터 상태 판정
    data_status = "DATA_VALID"
    if abs(curr['Ret']) >= 0.10:
        data_status = "DATA_INVALID" if name == "KOSPI" else "DATA_WARNING"
        
    return {
        "IndexCode": name,
        "Date": df.index[-1].strftime("%Y-%m-%d"),
        "Close": float(curr['Close']),
        "Ret": float(curr['Ret']) * 100,
        "MA20": float(curr['MA20']),
        "MA60": float(curr['MA60']),
        "MA200": float(curr['MA200']),
        "Disp20": float(curr['Disp20']),
        "Disp60": float(curr['Disp60']),
        "Disp200": float(curr['Disp200']),
        "RSI14": float(curr['RSI14']),
        "D20_Q20": float(curr['D20_Q20']),
        "D60_Q20": float(curr['D60_Q20']),
        "D200_Q25": float(curr['D200_Q25']),
        "P20": p20,
        "P60": p60,
        "P200": p200,
        "PRSI": prsi,
        "OversoldScore": int(score),
        "MA200_Slope20": float(curr['MA200_Slope20']) * 100,
        "TrendState": str(curr['TrendState']),
        "DataStatus": data_status,
        "ReversalConfirmed": reversal_confirmed
    }

# ==========================================
# 4. 권장 주문 비중 결정 알고리즘 (사양서 16항)
# ==========================================
def determine_entry(score, trend, index_code, cash_ratio, cycle_invested_pct, 
                    last_purchased_score, days_since_last_buy, data_status, 
                    reversal_confirmed, kospi_auto):
    
    if index_code == "KOSPI" and not kospi_auto:
        return "AUTOTRADE_DISABLED", 0, "KOSPI 데이터 검증 전 자동매수 금지", False
        
    if data_status == "DATA_INVALID":
        return "DATA_INVALID", 0, "데이터 무효 판정으로 주문 차단", False

    if cash_ratio <= 0.05:
        return "CASH_LOCK", 0, "가용 현금 부족 (5% 이하)", False

    if score <= 1:
        return "NO_SIGNAL", 0, "과매도 점수 1점 이하 (정상 궤도)", False

    if score <= last_purchased_score:
        return "SAME_LEVEL_LOCK", 0, f"동일 점수({score}점) 재진입 금지 규칙 작동", False

    if days_since_last_buy < 10:
        return "COOLDOWN", 0, f"최소 쿨다운 미달 (잔여 {10 - days_since_last_buy}일)", False

    is_kospi = (index_code == "KOSPI")

    if trend == "TREND_UP":
        cycle_limit = 15 if is_kospi else 30
        if score == 2:
            buy_pct = 5 if is_kospi else 10
            action = "RECON"
            reason = "상승 추세 내 2점 초기 과매도 도달 (정찰 매수)"
        elif score == 3:
            buy_pct = 5 if is_kospi else 10
            action = "MAIN_ENTRY"
            reason = "상승 추세 내 3점 강한 과매도 도달 (본 매수)"
        else:
            buy_pct = 5 if is_kospi else 10
            action = "EXTREME_ENTRY"
            reason = "상승 추세 내 4점 극단적 과매도 도달 (리스크 감수 추가 진입)"
    else:
        cycle_limit = 5 if is_kospi else 10
        if score <= 2:
            return "NO_SIGNAL", 0, "장기 하락 추세 중 2점 이하 관망 유지", False
            
        if score == 3 and not reversal_confirmed:
            return "WAIT_REVERSAL", 0, "하락 추세 3점 도달, 반등 시그널 대기 중", False
            
        if score == 3:
            buy_pct = 5
            action = "EXTREME_RECON"
            reason = "하락 추세 3점 도달 및 단기 반등 시그널 확인"
        else:
            buy_pct = 5
            action = "EXTREME_RECON"
            reason = "하락 추세 4점 도달, 제한적 극단 정찰 매수"

    remaining = cycle_limit - cycle_invested_pct
    buy_pct = min(buy_pct, remaining)

    if buy_pct <= 0:
        return "CYCLE_LIMIT", 0, f"사이클 최대 한도({cycle_limit}%) 소진", False

    if cash_ratio <= 0.20:
        buy_pct = min(buy_pct, 10)
        reason += " (LOW_CASH 룰에 의해 10% 한도 적용)"

    return action, buy_pct, reason, True

# ==========================================
# 5. 병렬 데이터 수집 및 판정
# ==========================================
master_data = []
with st.spinner("⏳ 글로벌 지수 원천 데이터 분석 중..."):
    for name, ticker in INDEX_MAP.items():
        metrics = fetch_and_calculate_indicators(name, ticker)
        if metrics.get("상태") == "INSUFFICIENT_DATA":
            continue
            
        action, rec_pct, reason, allowed = determine_entry(
            metrics['OversoldScore'],
            metrics['TrendState'],
            metrics['IndexCode'],
            sim_cash_ratio,
            sim_cycle_invested,
            sim_last_score,
            sim_days_since_buy,
            metrics['DataStatus'],
            metrics['ReversalConfirmed'],
            kospi_auto_enabled
        )
        
        metrics['ActionCode'] = action
        metrics['RecommendedCashPct'] = rec_pct
        metrics['Reason'] = reason
        metrics['OrderAllowed'] = allowed
        master_data.append(metrics)

# ==========================================
# 6. [대시보드 UI 1부] 전체 시장 요약 카드
# ==========================================
st.markdown("### ⚡ 17.1 전체 시장 요약 카드 (진입 시그널)")

cols = st.columns(4)
for i, m in enumerate(master_data):
    with cols[i]:
        # 색상 규칙 (18항)
        score = m['OversoldScore']
        bg_class = f"card-score-{score}" if score > 1 else "card-score-01"
        if score == 4: bg_class = "card-score-4" # 4점은 붉은색
        
        border_class = "border-trend-up" if m['TrendState'] == 'TREND_UP' else "border-trend-down"
        
        # 권장 매수 렌더링
        act_color = "#2ECC71" if m['OrderAllowed'] else "#95A5A6"
        if m['DataStatus'] != "DATA_VALID": act_color = "#9B59B6" # 보라색 경고
        if m['ActionCode'] == "AUTOTRADE_DISABLED": act_color = "#34495E" # 진회색
        
        st.markdown(f"""
        <div style="border-radius: 10px; padding: 15px; margin-bottom: 10px; {border_class}" class="{bg_class}">
            <h4 style="margin:0; font-weight:800;">{m['IndexCode']}</h4>
            <div style="font-size:0.8rem; opacity:0.7;">{m['Date']} | {m['Close']:,.2f} ({m['Ret']:+.2f}%)</div>
            <hr style="margin: 10px 0 !important;">
            <div style="display:flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size:0.9rem; font-weight:700;">과매도 점수</span>
                <strong style="font-size:1.1rem;">{score} 점</strong>
            </div>
            <div style="display:flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-size:0.9rem; font-weight:700;">장기 추세</span>
                <span>{'🟢 상승' if m['TrendState']=='TREND_UP' else '🔴 하락'}</span>
            </div>
            <div style="background:{act_color}; color:white; text-align:center; padding:5px; border-radius:5px; font-weight:bold; font-size:0.9rem;">
                {m['ActionCode']} | 현금 {m['RecommendedCashPct']}%
            </div>
            <div style="font-size:0.75rem; margin-top:8px; line-height:1.3; opacity:0.8; height: 50px; overflow:hidden;">
                <b>근거:</b> {m['Reason']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 7. [대시보드 UI 2/3부] 상세 데이터 테이블
# ==========================================
st.markdown("---")
st.markdown("### 📋 17.2 & 17.3 지표 상세 및 사이클 팩트체크")

if master_data:
    df_display = pd.DataFrame(master_data)
    
    # 필요한 열만 추출 및 재정렬
    display_cols = [
        "IndexCode", "Close", "MA200_Slope20", "TrendState", "OversoldScore", 
        "Disp20", "D20_Q20", "Disp60", "D60_Q20", "Disp200", "D200_Q25", "RSI14",
        "ActionCode", "DataStatus"
    ]
    df_table = df_display[display_cols].copy()
    
    # 렌더링 포맷 최적화
    format_dict = {
        "Close": "{:,.1f}", "MA200_Slope20": "{:+.2f}%", 
        "Disp20": "{:.1f}%", "D20_Q20": "{:.1f}%", 
        "Disp60": "{:.1f}%", "D60_Q20": "{:.1f}%", 
        "Disp200": "{:.1f}%", "D200_Q25": "{:.1f}%", "RSI14": "{:.1f}"
    }
    
    st.dataframe(df_table.style.format(format_dict), use_container_width=True)
