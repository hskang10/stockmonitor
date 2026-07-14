import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. 페이지 최적화 설정 (모바일 접속 시 사이드바 자동 개방 상태로 시작)
st.set_page_config(
    page_title="Gems 3.0 Master Monitor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Gems 3.0 매크로 및 글로벌 지수 통합 관제 시스템")
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
    
    # 기간별 이동평균선 및 이격도(Disparity) 동시 연산
    periods = [20, 60, 120, 200]
    disparities = {}
    for p in periods:
        ma = df['Close'].rolling(window=p).mean().iloc[-1]
        disparities[f"{p}일 이격도"] = round((current_price / ma) * 100, 2)
    
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
# 4. 사이드바 수동 보정 매트릭스 (차단 방화벽)
# ==========================================
st.sidebar.header("⚙️ 매크로 수동 캘리브레이션")
st.sidebar.markdown("외부 데이터 보안 규격에 따른 실시간 수동 동기화 필드")

cnn_fg = st.sidebar.slider("CNN Fear & Greed Index", 0, 100, 55, 1)
forward_pe = st.sidebar.slider("S&P 500 Forward P/E", 15.0, 25.0, 21.2, 0.1)

# ==========================================
# 5. 데이터 병렬 동기화 파이프라인 가동
# ==========================================
with st.spinner("⏳ 13대 마스터 지수의 시계열 데이터를 팩팅 중..."):
    category_tables = {}
    
    for category, assets in TARGET_ASSETS.items():
        rows = []
        for name, ticker in assets.items():
            t = yf.Ticker(ticker)
            # 200일 이평선 연산을 위해 안정적으로 1년 반치 소싱
            h = t.history(period="1y")
            metrics = calculate_master_metrics(h)
            if metrics:
                metrics["지수/지표명"] = name
                rows.append(metrics)
        
        if rows:
            df_cat = pd.DataFrame(rows)
            # 열 순서 재정렬
            cols_order = ["지수/지표명", "현재 수치", "전일대비 등락", "20일 이격도", "60일 이격도", "120일 이격도", "200일 이격도", "RSI (14일)"]
            category_tables[category] = df_cat[cols_order].set_index("지수/지표명")

# ==========================================
# 6. [대시보드 1부] 수동 캘리브레이션 지표 최상단 요약 표기
# ==========================================
st.header("1부. 독점 매크로 센서 팩")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("CNN Fear & Greed", f"{cnn_fg} pts")
with col2:
    st.metric("S&P 500 Forward P/E", f"{forward_pe:.1f} 배")
with col3:
    # 7대 선행지표 규격에 따른 환율 리스크 감지 자동 출력
    usdkrw_val = category_tables.get("통화").loc["원/달러 환율", "현재 수치"] if "통화" in category_tables else 0.0
    exchange_status = "🚨 고환율 리스크 국면" if usdkrw_val >= 1400.0 else "✅ 정상 운용 범위"
    st.metric("원/달러 실시간 조율", f"{usdkrw_val:,} 원", exchange_status)

st.markdown("---")

# ==========================================
# 7. [대시보드 2부] 13대 지수 카테고리별 데이터 그리드 렌더링
# ==========================================
st.header("2부. 글로벌 자산군 다중 이격도 & 과열도 매트릭스")

# 스타일링 함수 (전일대비 등락에 따른 색상 시각화 및 양수 기호화)
def highlight_returns(val):
    if isinstance(val, (int, float)):
        color = 'red' if val > 0 else 'blue' if val < 0 else 'black'
        return f'color: {color}; font-weight: bold;'
    return ''

# 카테고리별 아코디언 배치로 모바일 수직 스크롤 압축
for category, table in category_tables.items():
    with st.expander(f"📊 {category} 데이터 명세 보기", expanded=True):
        # 최신 Pandas map() 표준 적용 및 안전한 한 줄 포맷팅 처리
        styled_table = table.style.map(highlight_returns, subset=["전일대비 등락"]).format({"전일대비 등락": "{:+.2f}%", "현재 수치": "{:,.2f}"})
        st.dataframe(styled_table, use_container_width=True)
