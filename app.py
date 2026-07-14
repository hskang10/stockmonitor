import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 페이지 기본 설정 (반응형 및 모바일 최적화)
st.set_page_config(page_title="Gems 3.0 Autonomous Controller", layout="wide")
st.title("🛡️ Gems 3.0 무인 통제형 통합 투자 시스템")
st.caption("Wall Street Style Quantitative Portfolio & Risk Controller (Calibration Edition)")

# ==========================================
# 1. 자산 데이터 및 티커 매핑 정의 (Gems 3.0 기준)
# ==========================================
# 7대 선행 지표 티커 (실시간 조회 가능한 자산들)
MACRO_TICKERS = {
    "미 10년물 국채금리": "^TNX",
    "WTI 원유 선물": "CL=F",
    "원/달러 환율": "KRW=X",
    "S&P 500 (SPX)": "^GSPC",
    "나스닥 100 (NDX)": "^IXIC",
    "CBOE VIX": "^VIX"
}

# 자산배분 자산군 (이격도 절대 기준 매핑)
ASSET_ALLOCATION = {
    "미국 나스닥 100 (NDX)": {"ticker": "^IXIC", "overbought": 106.0, "oversold": 94.0},
    "미국 S&P 500 (SPX)": {"ticker": "^GSPC", "overbought": 104.0, "oversold": 96.0},
    "미국 배당 다우존스 (SCHD)": {"ticker": "SCHD", "overbought": 103.0, "oversold": 97.0},
    "인도 Nifty 50 (NSEI)": {"ticker": "^NSEI", "overbought": 106.0, "oversold": 95.0},
    "미국 30년 장기국채 (TLT)": {"ticker": "TLT", "overbought": 103.0, "oversold": 97.0},
    "국제 금 (GOLD)": {"ticker": "GC=F", "overbought": 105.0, "oversold": 95.0}
}

# 국장 스윙 대상 자산
KOREA_SWING = {
    "KODEX 200 (요새군)": {"ticker": "069500.KS"},
    "KODEX 반도체레버리지 (창)": {"ticker": "261240.KS"},
    "KODEX 은행 (철퇴)": {"ticker": "091180.KS"}
}

# ==========================================
# 2. 핵심 계산 보조 함수 (RSI 및 이격도)
# ==========================================
def calculate_indicators(df, window_rsi=14, window_ma=200):
    if df.empty or len(df) < window_ma:
        return None
    
    current_price = df['Close'].iloc[-1]
    
    # 200일 이격도(Disparity) 계산
    df['MA200'] = df['Close'].rolling(window=window_ma).mean()
    disparity = (current_price / df['MA200'].iloc[-1]) * 100
    
    # 14일 RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window_rsi).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window_rsi).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # 고점 대비 하락률 (MDD 연산용 ATH 기준)
    ath = df['Close'].max()
    drawdown = ((current_price - ath) / ath) * 100
    
    return {
        "price": current_price,
        "disparity": disparity,
        "rsi": current_rsi,
        "drawdown": drawdown
    }

# ==========================================
# 3. 데이터 수집 단계 (시각적 스피너 가동)
# ==========================================
with st.spinner("⏳ 글로벌 매크로 및 자산 데이터를 실시간 동기화 중..."):
    # 매크로 지표 로드
    macro_data = {}
    for name, ticker in MACRO_TICKERS.items():
        t = yf.Ticker(ticker)
        h = t.history(period="5d")
        if not h.empty:
            macro_data[name] = h['Close'].iloc[-1]
            # 국채금리의 경우 일간 변동폭(bp) 계산
            if name == "미 10년물 국채금리" and len(h) >= 2:
                macro_data["금리변동폭(bp)"] = (h['Close'].iloc[-1] - h['Close'].iloc[-2]) * 100
    
    # 자산배분 지표 로드
    asset_results = {}
    for name, info in ASSET_ALLOCATION.items():
        t = yf.Ticker(info["ticker"])
        # 이평선 연산을 위해 2년치 데이터 수집
        h = t.history(period="2y")
        metrics = calculate_indicators(h)
        if metrics:
            asset_results[name] = metrics

    # 국장 스윙 지표 로드
    swing_results = {}
    for name, info in KOREA_SWING.items():
        t = yf.Ticker(info["ticker"])
        h = t.history(period="1y")
        # 국장은 20일 이격도를 기준 필터로 사용하므로 custom 계산
        metrics = calculate_indicators(h, window_ma=20)
        if metrics:
            swing_results[name] = metrics

# ==========================================
# 4. 사용자 입력 인터페이스 (CASH_RATIO 및 실시간 매크로 입력)
# ==========================================
st.sidebar.header("⚙️ Gems 3.0 실시간 계좌 정보 입력")
st.sidebar.markdown("현재 실제 운용 중인 계좌별 현금 비중을 입력하십시오.")

isa_cash = st.sidebar.slider("ISA 계좌 현금 비중 (CASH_RATIO)", 0.0, 1.0, 0.25, 0.01)
pension_cash = st.sidebar.slider("연금 계좌 현금 비중 (CASH_RATIO)", 0.0, 1.0, 0.10, 0.01)
korea_cash = st.sidebar.slider("국장 스윙 계좌 현금 비중 (CASH_RATIO)", 0.0, 1.0, 0.50, 0.01)

st.sidebar.markdown("---")
st.sidebar.header("🔌 실시간 매크로 수동 캘리브레이션")
st.sidebar.markdown("API 미지원 및 차단 리스크가 있는 지표들의 현재 수치를 직접 보정해 주십시오.")

cnn_fg = st.sidebar.slider("CNN Fear & Greed Index 수치", 0, 100, 58, 1)
forward_pe = st.sidebar.slider("S&P 500 Forward P/E 배수", 15.0, 25.0, 21.2, 0.1)

# ==========================================
# 5. [대시보드 1부] 7대 선행 지표 및 매크로 검증
# ==========================================
st.header("1부. 7대 선행 지표 및 매크로 시스템")
col1, col2, col3, col4, col5, col6 = st.columns(6)

# 금리, 유가, 환율, VIX 추출
us10y = macro_data.get("미 10년물 국채금리", 0.0)
us10y_bp = macro_data.get("금리변동폭(bp)", 0.0)
wti = macro_data.get("WTI 원유 선물", 0.0)
usdkrw = macro_data.get("원/달러 환율", 0.0)
vix = macro_data.get("CBOE VIX", 0.0)

# CNN Fear & Greed 레벨 텍스트화
if cnn_fg >= 75:
    fg_text = "Extreme Greed"
elif cnn_fg >= 55:
    fg_text = "Greed"
elif cnn_fg >= 45:
    fg_text = "Neutral"
elif cnn_fg >= 25:
    fg_text = "Fear"
else:
    fg_text = "Extreme Fear"

with col1:
    st.metric("미 10년 국채금리", f"{us10y:.3f}%", f"{us10y_bp:+.1f} bp")
with col2:
    st.metric("WTI 원유 선물", f"${wti:.2f}")
with col3:
    st.metric("원/달러 환율", f"{usdkrw:.1f} 원")
with col4:
    st.metric("CBOE VIX (공포)", f"{vix:.1f}")
with col5:
    pe_status = "고평가 주의" if forward_pe > 20.0 else "정상/저평가"
    st.metric("Forward P/E (S&P500)", f"{forward_pe:.1f}배", pe_status)
with col6:
    st.metric("CNN Fear & Greed", f"{cnn_fg} ({fg_text})")

# ==========================================
# 6. [대시보드 2부] 사각지대 자동 제어 알고리즘 (Fail-Safe)
# ==========================================
st.header("🛡️ AUTONOMOUS FAIL-SAFE 자동화 필터")

filter_1_active = usdkrw >= 1400.0
filter_2_active = (vix > 35.0) 
filter_3_active = True # 인도 필터는 항상 독립 구동

f1_status = "🔴 활성화 (고환율 착시 방어 - 로스컷 기계적 유예)" if filter_1_active else "⚪ 비활성화"
f2_status = "🔴 활성화 (유동성 위기 오버라이드 - 무조건 현금 10% 강제확보)" if filter_2_active else "⚪ 비활성화"
f3_status = "🟢 상시 가동 중 (미국 매크로 경고 무시 및 독립 타점 구동)"

st.info(f"**제1필터 (환율 착시 방어):** {f1_status}")
st.warning(f"**제2필터 (유동성 위기 감지):** {f2_status}")
st.success(f"**제3필터 (인도 디커플링 필터):** {f3_status}")

# ==========================================
# 7. [대시보드 3부] 계좌별 최종 실행 가이드 (Decision Matrix)
# ==========================================
st.header("2부. 3대 계좌 통합 의사결정 매트릭스")

tab1, tab2, tab3 = st.tabs(["🔒 ISA 중단기 계좌", "📈 연금저축 계좌", "🇰🇷 국장 스윙 계좌"])

# --- TAB 1: ISA 계좌 ---
with tab1:
    st.subheader("ISA 자산군 모니터링 명세")
    
    isa_summary = []
    for name, metrics in asset_results.items():
        limits = ASSET_ALLOCATION[name]
        disp = metrics["disparity"]
        
        # 상태 판정
        if disp >= limits["overbought"]:
            status = "🔥 과매수 (익절 검토)"
        elif disp <= limits["oversold"]:
            status = "🛒 과매도 (진입 가능)"
        else:
            status = "🟢 정상 범위"
            
        isa_summary.append({
            "자산명": name,
            "현재가": f"{metrics['price']:,}",
            "200일 이격도": f"{disp:.2f}%",
            "일봉 RSI (14)": f"{metrics['rsi']:.1f}",
            "ATH 대비 하락률": f"{metrics['drawdown']:.2f}%",
            "Gems 3.0 밴드 현황": status
        })
    
    st.table(pd.DataFrame(isa_summary).set_index("자산명"))
    
    # 기계적 액션 스크립트 도출
    st.subheader("🤖 ISA 최종 실행 스크립트")
    
    # 최우선 타격 대상 판정 (이격도 최하위 자산 도출)
    oversold_assets = [a for a in asset_results.keys() if asset_results[a]["disparity"] <= ASSET_ALLOCATION[a]["oversold"]]
    
    if isa_cash > 0.20:
        st.markdown("**계좌 상태:** 🟢 고현금 상태 (CASH_RATIO > 0.20)")
        if oversold_assets:
            target_asset = min(oversold_assets, key=lambda a: asset_results[a]["disparity"])
            st.success(f"💥 **[매수 집행]** 가용 현금의 **30%**를 분량으로 **'{target_asset}'** 기계적 진입!")
        else:
            st.info("ℹ️ **[보유 및 관망]** 모든 자산이 정상 혹은 과열 상태에 있습니다. 추가 매수 집행을 전면 금지합니다.")
    else:
        st.markdown("**계좌 상태:** 🔴 저현금 및 고갈 상태")
        if filter_1_active:
            st.warning("⚠️ **[Fail-Safe 제1필터 작동]** 로스컷 방어선 이탈 감지 시에도 환율 착시 방어가 적용되므로 기계적 로스컷은 일시 유예됩니다.")
        else:
            st.error("⚠️ **[행동 동결 및 락업]** 추가 매수 절대 불가. 보유 자산 익절을 통한 현금 확보 마일스톤에 강제 진입합니다.")

# --- TAB 2: 연금저축 계좌 ---
with tab2:
    st.subheader("연금저축 장기 자산군 모니터링")
    st.table(pd.DataFrame(isa_summary).set_index("자산명")) # 자산배분 지표 공유
    
    st.subheader("🤖 연금저축 최종 실행 스크립트")
    if pension_cash > 0.05:
        st.markdown("**계좌 상태:** 🟢 현금 보유 상태 (손절 불가 계좌)")
        if oversold_assets:
            target_asset = min(oversold_assets, key=lambda a: asset_results[a]["disparity"])
            st.success(f"💥 **[기계적 수량 매집]** 평단가 하락을 위해 가용 현금의 **30%**를 **'{target_asset}'**에 투입합니다.")
        else:
            st.info("ℹ️ **[수량 보존]** 현재 밴드 하단에 도달한 자산이 없습니다. 기존 수량을 그대로 홀딩하며 복리 우상향을 관망합니다.")
    else:
        st.error("🔒 **[시스템 락업]** 계좌 자금이 고갈되었습니다. 자본주의의 영구적 우상향을 신뢰하며 추가 행동 없이 무조건 관망합니다. (손절 절대 불가)")

# --- TAB 3: 국장 스윙 계좌 ---
with tab3:
    st.subheader("대한민국 요새군 & 별동대 모니터링")
    
    swing_summary = []
    for name, metrics in swing_results.items():
        rsi = metrics["rsi"]
        if rsi >= 60.0:
            status = "🔥 극단적 과열 (약탈적 청산 타점)"
        elif name == "KODEX 반도체레버리지 (창)" and rsi <= 38.0:
            status = "🛒 진성 과매도 (창 타격 트리거)"
        elif name == "KODEX 은행 (철퇴)" and rsi <= 40.0:
            status = "🛒 진성 과매도 (철퇴 타격 트리거)"
        else:
            status = "🟢 정상 전술 구역"
            
        swing_summary.append({
            "종목명": name,
            "현재가": f"{int(metrics['price']):,} 원",
            "20일 이격도": f"{metrics['disparity']:.2f}%",
            "일봉 RSI (14)": f"{rsi:.1f}",
            "상태 판정": status
        })
    st.table(pd.DataFrame(swing_summary).set_index("종목명"))
    
    st.subheader("🤖 국장 스윙 실행 스크립트")
    
    if korea_cash > 0.40:
        st.markdown("**계좌 상태:** 🟢 고현금 상태 (CASH_RATIO > 0.40)")
        
        # ⚠️ 수동 입력 데이터 연동형: KODEX 200 최초 진입 필터 검증 ⚠️
        # 조건 1: CNN Fear & Greed < 80 이고 미국 주력 지수 RSI가 둘 다 65 이하인가?
        spx_rsi = asset_results["미국 S&P 500 (SPX)"]["rsi"]
        ndx_rsi = asset_results["미국 나스닥 100 (NDX)"]["rsi"]
        
        macro_heat_pass = (cnn_fg < 80) and (spx_rsi <= 65.0) and (ndx_rsi <= 65.0)
        
        # 조건 2: KODEX 200의 20일선 이격도가 +3.5% 미만인가? (즉, 103.5% 미만)
        k200_disp = swing_results["KODEX 200 (요새군)"]["disparity"]
        price_gap_pass = k200_disp < 103.5
        
        if macro_heat_pass and price_gap_pass:
            st.success("🏰 **[요새군 최초 진입 적합]** 미국 매크로 과열 필터와 국장 가격 유격 필터를 모두 통과했습니다. KODEX 200 최초 비중(60%) 진입을 정상 개방합니다.")
        else:
            st.warning("⏳ **[요새군 진입 보류]** 진입 불충분 조건 감지:")
            if not macro_heat_pass:
                st.write(f"- 글로벌 매크로 과열 필터 미충족 (CNN F&G: {cnn_fg}, SPX RSI: {spx_rsi:.1f}, NDX RSI: {ndx_rsi:.1f})")
            if not price_gap_pass:
                st.write(f"- 국장 단기 급등 과열 필터 미충족 (KODEX 200 20일선 이격도: {k200_disp:.2f}%)")
            
        # 별동대 타격 트리거 검증
        semi_rsi = swing_results["KODEX 반도체레버리지 (창)"]["rsi"]
        bank_rsi = swing_results["KODEX 은행 (철퇴)"]["rsi"]
        
        if semi_rsi <= 38.0:
            st.success("⚔️ **[오른손 창 격발]** 반도체 레버리지 RSI 38 이하 도달! 가용 현금의 **40%** 1차 공격 개시 (MTS 자동 스톱로스 설정 필수)")
        elif bank_rsi <= 40.0:
            st.success("🔨 **[왼손 철퇴 격발]** 은행 ETF RSI 40 미만 도달! 가용 현금의 **40%** 1차 공격 개시 (MTS 스톱로스 연동 필수)")
        else:
            st.info("ℹ️ **[전술적 인내]** 별동대 타격 기준(RSI 38/40)에 도달한 주도 우량 ETF가 없습니다. 불필요한 매몰 비용 발생을 차단합니다.")
            
    else:
        st.markdown("**계좌 상태:** 🔴 저현금 및 고갈 국면")
        st.error("🔒 **[국장 스윙 연산 셧다운]** 현금 비중 방화벽에 도달했습니다. 추가 매수는 전면 금지되며, 목표가 도달 시 전량 강제 익절하여 즉시 고현금 상태(40% 이상)로 회군하십시오.")
