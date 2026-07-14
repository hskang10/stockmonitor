import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. 페이지 모바일 최적화 설정
st.set_page_config(page_title="Global Index Monitor", layout="wide")
st.title("🌐 글로벌 지수 및 퀀트 지표 모니터링")

# 2. 분석 대상 지정 (S&P500, 나스닥100, 인도 니프티50, 코스피)
# yfinance 티커: S&P500(^GSPC), 나스닥(^IXIC), 니프티50(^NSEI), 코스피(^KS11)
TARGET_INDICES = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^IXIC",
    "India Nifty 50": "^NSEI",
    "KOSPI": "^KS11"
}

# 3. 보조지표 계산 함수 (RSI 및 200일 이격도)
def calculate_indicators(ticker_symbol):
    # 200일 이동평균선 계산을 위해 여유 있게 1년 반(대략 400영업일) 데이터 수집
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="2y")
    
    if df.empty:
        return None
    
    # 현재가
    current_price = df['Close'].iloc[-1]
    
    # 200일 이격도 계산
    df['MA200'] = df['Close'].rolling(window=200).mean()
    disparity_200 = (current_price / df['MA200'].iloc[-1]) * 100
    
    # 14일 RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9) # 0 나누기 방지
    rsi_14 = 100 - (100 / (1 + rs))
    current_rsi = rsi_14.iloc[-1]
    
    return {
        "현재가": round(current_price, 2),
        "200일 이격도(%)": round(disparity_200, 2),
        "RSI (14)": round(current_rsi, 2)
    }

# 4. 데이터 수집 및 화면 출력
results = {}
with st.spinner('실시간 지수 데이터를 수집하고 지표를 계산 중입니다...'):
    for name, ticker in TARGET_INDICES.items():
        data = calculate_indicators(ticker)
        if data:
            results[name] = data

# 데이터프레임 변환
if results:
    df_res = pd.DataFrame(results).T
    
    # 모바일에서 직관적으로 볼 수 있게 주요 지표를 카드 형태로 상단 배치
    st.subheader("📊 주요 지표 요약")
    cols = st.columns(len(results))
    for idx, (name, metrics) in enumerate(results.items()):
        with cols[idx]:
            st.metric(
                label=name, 
                value=f"{metrics['현재가']:,}", 
                delta=f"RSI: {metrics['RSI (14)']}"
            )
            
    # 전체 데이터 테이블 표기
    st.subheader("📋 정량 데이터 명세")
    st.dataframe(df_res, use_container_width=True)
    
    # 위험 구간 경고 알림 (예시: 이격도 과열 또는 침체)
    st.subheader("⚠️ 퀀트 시그널 모니터링")
    for name, metrics in results.items():
        disp = metrics["200일 이격도(%)"]
        rsi = metrics["RSI (14)"]
        
        if disp >= 108 or rsi >= 70:
            st.error(f"🚨 **{name}** 과열 신호 감지 (이격도: {disp}%, RSI: {rsi})")
        elif disp <= 92 or rsi <= 30:
            st.success(f"🛒 **{name}** 분할 매수 구간 진입 (이격도: {disp}%, RSI: {rsi})")
        else:
            st.info(f"✅ **{name}** 정상 범위 운용 중 (이격도: {disp}%, RSI: {rsi})")
            
else:
    st.error("데이터를 불러오지 못했습니다. 티커 설정을 확인하세요.")
