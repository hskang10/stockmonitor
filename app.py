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
# 6. Gems 3.0 규칙 기반 진입 조건 판정 백엔드 엔진
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
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "유동성 위기 오버라이드 작동 (VIX > 35)", "color": "#FFA500", "action": "매수 보류 및 예비현금 10% 확보 대기"}
            elif usdkrw_val >= 1400.0:
                signals["S&P 500"] = {"status": "🚨 LOCK-UP", "reason": "고환율 방어 버퍼 작동 (환율 >= 1400원)", "color": "#FFA500", "action": "기계적 매수 1회 강제 지연 (FX Buffer)"}
            else:
                signals["S&P 500"] = {"status": "🟢 BUY", "reason": f"200일 이격도({spx_disp}%) 및 필터 통과 (RSI: {spx_rsi} / CNN: {cnn_fg})", "color": "#2ECC71", "action": "가용 현금의 20% 기계적 집행"}
        else:
            signals["S&P 500"] = {"status": "⚪ HOLD", "reason": "진입 기준 미도달 (추세 지지선 위 위치)", "color": "#7F8C8D", "action": "관망 및 기존 비중 유지"}

    # 2) 나스닥 100 판정
    if "주요지수" in category_tables and "나스닥 100" in category_tables["주요지수"].index:
        ndx = category_tables["주요지수"].loc["나스닥 100"]
        ndx_disp = ndx["200일 이격도"]
        ndx_rsi = ndx["RSI (14일)"]
        
        trigger_active = ndx_disp <= 102.0
        filter_met = (ndx_rsi <= 38.0) or (cnn_fg <= 25)
        
        if trigger_active and filter_met:
            if vix_val > 35.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "유동성 위기 오버라이드 작동 (VIX > 35)", "color": "#FFA500", "action": "매수 보류 및 예비현금 10% 확보 대기"}
            elif usdkrw_val >= 1400.0:
                signals["나스닥 100"] = {"status": "🚨 LOCK-UP", "reason": "고환율 방어 버퍼 작동 (환율 >= 1400원)", "color": "#FFA500", "action": "기계적 매수 1회 강제 지연 (FX Buffer)"}
            else:
                signals["나스닥 100"] = {"status": "🟢 BUY", "reason": f"200일 이격도({ndx_disp}%) 및 필터 통과 (RSI: {ndx_rsi} / CNN: {cnn_fg})", "color": "#2ECC71", "action": "가용 현금의 20% 기계적 집행"}
        else:
            signals["나스닥 100"] = {"status": "⚪ HOLD", "reason": "진입 기준 미도달 (추세 지지선 위 위치)", "color": "#7F8C8D", "action": "관망 및 기존 비중 유지"}

    # 3) 인도 니프티 50 판정 (독립 필터 가동)
    if "주요지수" in category_tables and "인도 니프티 50" in category_tables["주요지수"].index:
        nifty = category_tables["주요지수"].loc["인도 니프티 50"]
        nifty_disp120 = nifty["120일 이격도"]
        nifty_rsi = nifty["RSI (14일)"]
        
        trigger_active = nifty_disp120 <= 101.0
        filter_met = (nifty_rsi <= 42.0) or (nifty["120일 이격도"] <= 98.0)
        
        if trigger_active and filter_met:
            signals["인도 니프티 50"] = {"status": "🟢 BUY", "reason": f"인도 독립 필터 만족 (120일 이격도: {nifty_disp120}% / RSI: {nifty_rsi})", "color": "#2ECC71", "action": "독립적으로 가용 현금의 20% 즉각 진입"}
        else:
            signals["인도 니프티 50"] = {"status": "⚪ HOLD", "reason": "인도 고성장 추세 유지 중", "color": "#7F8C8D", "action": "관망 및 기존 비중 유지"}

    # 4) 코스피 판정
    if "주요지수" in category_tables and "코스피" in category_tables["주요지수"].index:
        kospi = category_tables["주요지수"].loc["코스피"]
        kospi_disp60 = kospi["60일 이격도"]
        kospi_rsi = kospi["RSI (14일)"]
        
        trigger_active = kospi_disp60 < 100.0
        filter_met = kospi_rsi <= 35.0
        
        if trigger_active and filter_met:
            signals["코스피"] = {"status": "🟢 BUY", "reason": f"60일선 붕괴 역추세 바닥 확인 (60일 이격도: {kospi_disp60}% / RSI: {kospi_rsi})", "color": "#2ECC71", "action": "별동대 예산의 40% 투입 & MTS 기술적 스톱로스 동시 가동"}
        else:
            signals["코스피"] = {"status": "⚪ HOLD", "reason": "스윙 바닥 구간 미충족", "color": "#7F8C8D", "action": "관망 (불필요한 국장 잡거래 원천 금지)"}

    # 5) 미국 30년 국채금리 기반 판정 (TYX 금리 데이터 기반 역연산)
    if "미국국채금리" in category_tables and "미국 30년 국채금리" in category_tables["미국국채금리"].index:
        tyx = category_tables["미국국채금리"].loc["미국 30년 국채금리"]
        tyx_disp120 = tyx["120일 이격도"]
        tyx_rsi = tyx["RSI (14일)"]
        
        trigger_active = tyx_disp120 >= 105.0
        filter_met = tyx_rsi >= 65.0
        
        if trigger_active and filter_met:
            signals["미국 30년 국채금리"] = {"status": "🟢 BUY", "reason": f"30년 금리 오버슈팅 발작 (120일 이격: {tyx_disp120}% / 금리 RSI: {tyx_rsi})", "color": "#2ECC71", "action": "ACE 미국30년국채액티브(H) 예산의 30% 분할 매수 실행"}
        else:
            signals["미국 30년 국채금리"] = {"status": "⚪ HOLD", "reason": "안정적 금리 추세 범위 내 위치", "color": "#7F8C8D", "action": "관망 및 국채 보유 분 배당 자동 재투자"}

    return signals

# ==========================================
# 7. [대시보드 1부] 수동 캘리브레이션 지표 및 실시간 경보 표기
# ==========================================
st.header("1부. 독점 매크로 센서 팩")
col1, col2, col3 = st.columns(3)

vix_val = category_tables.get("변동성지수").loc["CBOE VIX", "현재 수치"] if "변동성지수" in category_tables else 0.0
usdkrw_val = category_tables.get("통화").loc["원/달러 환율", "현재 수치"] if "통화" in category_tables else 0.0

with col1:
    st.metric("CNN Fear & Greed", f"{cnn_fg} pts", "25 이하 극단 공포 시 필터 프리패스")
with col2:
    vix_status = "🚨 유동성 공포 과열 (VIX > 35)" if vix_val >= 35.0 else "✅ 정상 변동성 영역"
    st.metric("CBOE VIX Index", f"{vix_val:.2f} pts", vix_status)
with col3:
    exchange_status = "🚨 고환율 리스크 국면" if usdkrw_val >= 1400.0 else "✅ 정상 운용 범위"
    st.metric("원/달러 실시간 조율", f"{usdkrw_val:,} 원", exchange_status)

st.markdown("---")

# ==========================================
# 8. [대시보드 2부] 5대 마스터 자산 기계적 진입 가이드 (다크 테마 최적화)
# ==========================================
st.header("2부. Gems 3.0 실시간 통합 실행 가이드 시그널")

gems_signals = evaluate_gems_signals(category_tables, cnn_fg)

# 수평형 시그널 카드 배치
card_cols = st.columns(5)
for i, (asset_name, sig) in enumerate(gems_signals.items()):
    with card_cols[i]:
        st.markdown(
            f"""
            <div style="
                border: 2px solid {sig['color']}; 
                border-radius: 10px; 
                padding: 15px; 
                text-align: center; 
                background-color: rgba(128,128,128,0.08);
                min-height: 200px;
            ">
                <h4 style="margin: 0; font-weight: 700;">{asset_name}</h4>
                <hr style="margin: 8px 0; border: 0; border-top: 1px dashed {sig['color']}; opacity: 0.5;">
                <span style="
                    font-size: 24px; 
                    font-weight: 800; 
                    color: {sig['color']};
                ">{sig['status']}</span>
                <p style="font-size: 11px; margin-top: 10px; height: 40px; overflow: hidden; opacity: 0.8;">
                    <b>근거:</b> {sig['reason']}
                </p>
                <div style="
                    font-size: 12px; 
                    font-weight: 700; 
                    background-color: {sig['color']}; 
                    color: white; 
                    padding: 5px; 
                    border-radius: 5px;
                    margin-top: 10px;
                ">
                    {sig['action']}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 9. [대시보드 3부] 13대 지수 카테고리별 데이터 그리드 렌더링
# ==========================================
st.header("3부. 글로벌 자산군 다중 이격도 & 과열도 매트릭스")

# 다크 모드와 라이트 모드 테마에 맞춰 가독성을 자동 보정하는 폰트 색상 하이라이트 매직 함수
def highlight_returns(val):
    if isinstance(val, (int, float)):
        if val > 0:
            # 상승 시: 다크/라이트 공용 고대비 Coral Red 적용
            color = '#FF6B6B'
        elif val < 0:
            # 하락 시: 다크 모드에서도 쨍하게 선명한 형광 하늘색(Neon Blue) 적용
            color = '#58A6FF'
        else:
            color = 'inherit'
        return f'color: {color}; font-weight: bold;'
    return ''

# 카테고리별 아코디언 배치로 모바일 수직 스크롤 압축
for category, table in category_tables.items():
    with st.expander(f"📊 {category} 데이터 명세 보기", expanded=True):
        # 최신 Pandas map() 표준 적용 및 안전한 한 줄 포맷팅 처리 (이격도는 소수점 첫째 자리, 등락률/RSI는 둘째 자리 유지)
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

# 하단에 실시간 기준시각 자동 동기화 출력 (교차 검증 및 투명성 보장)
st.markdown("---")
st.caption(f"**[데이터 교차 검증 정보]** 실시간 소스: Yahoo Finance API 동기화 | "
           f"기준 시각: {pd.Timestamp.now(tz='Asia/Seoul').strftime('%Y-%m-%d %H:%M:%S')} KST")
