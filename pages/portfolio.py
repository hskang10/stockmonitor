import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# 1. 페이지 최적화 설정
st.set_page_config(
    page_title="Gems 3.0 Portfolio Monitor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 다크/라이트 하이브리드 고대비 CSS 스타일 인젝션
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    .status-title {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.05rem;
        background: linear-gradient(135deg, #FF8E53 0%, #FF6B6B 50%, #2ECC71 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem !important;
    }
    .metric-box {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    hr {
        margin: 1.2rem 0 !important;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(128,128,128,0), rgba(128,128,128,0.3), rgba(128,128,128,0));
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="status-title">📈 구글 시트 연동 포트폴리오 현황 판넬</h1>', unsafe_allow_html=True)
st.caption("구글 스프레드시트 자산종합 원장의 실시간 데이터 분석 및 비주얼 매트릭스")

# 2. 캐싱 기반 구글 보안 인증 통신 활성화 (Rate Limit 돌파 방지용 ttl 적용)
@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(credentials)

# 3. 데이터 로딩 및 정량 수치 클리닝 프로세스 (1분간 캐싱 보존)
@st.cache_data(ttl=60)
def load_and_clean_portfolio_data():
    gc = get_gspread_client()
    sh = gc.open("자산종합")
    worksheet = sh.worksheet("포트폴리오")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # 공백 행 및 데이터 누락 전면 제거
    df = df[df['종목명'].str.strip() != ''].copy()
    
    # 계좌명 유실 시 기타로 기계적 통합 조율
    df['계좌명'] = df['계좌명'].replace('', '기타/미지정').fillna('기타/미지정')
    
    # 원자재 및 콤마 기호 제거 후 Float 변환을 위한 수리 함수
    def clean_numeric(val):
        if pd.isna(val) or str(val).strip() == "":
            return 0.0
        cleaned = str(val).replace(",", "").replace("%", "").replace("-", "").strip()
        try:
            # 음수 값 복원 판정
            is_negative = '-' in str(val)
            num = float(cleaned)
            return -num if is_negative else num
        except ValueError:
            return 0.0

    # 데이터 정제 집행
    numeric_cols = ['보유수량', '평균단가', '현재가', '매입금액', '평가금액', '손익률', 'MDD']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
            
    return df

try:
    # 데이터 로드
    df_raw = load_and_clean_portfolio_data()
    
    # ==========================================
    # 4. 최상단 실시간 계좌 요약 (Metrics)
    # ==========================================
    total_buy = df_raw['매입금액'].sum()
    total_eval = df_raw['평가금액'].sum()
    total_profit = total_eval - total_buy
    total_return_pct = (total_profit / total_buy * 100) if total_buy > 0 else 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:0.85rem; font-weight:600; opacity:0.7;">총 투자 원금 (매입금액)</span>
                <div style="font-size:1.6rem; font-weight:800; margin-top:5px; color:#58A6FF;">{total_buy:,.0f} 원</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:0.85rem; font-weight:600; opacity:0.7;">총 평가 자산 (평가금액)</span>
                <div style="font-size:1.6rem; font-weight:800; margin-top:5px; color:#2ECC71;">{total_eval:,.0f} 원</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        profit_color = "#FF6B6B" if total_profit >= 0 else "#58A6FF"
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:0.85rem; font-weight:600; opacity:0.7;">총 누적 손익</span>
                <div style="font-size:1.6rem; font-weight:800; margin-top:5px; color:{profit_color};">{total_profit:+,.0f} 원</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        return_color = "#FF6B6B" if total_return_pct >= 0 else "#58A6FF"
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:0.85rem; font-weight:600; opacity:0.7;">총합 손익률</span>
                <div style="font-size:1.6rem; font-weight:800; margin-top:5px; color:{return_color};">{total_return_pct:+.2f} %</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ==========================================
    # 5. [시각화 레이어] 계좌별 및 자산별 다차원 시각화
    # ==========================================
    st.markdown('### 📊 포트폴리오 비주얼 애널리틱스')
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # 계좌별 평가자산 비중 (도넛 차트)
        df_acc_grouped = df_raw.groupby('계좌명')['평가금액'].sum().reset_index()
        fig_acc = px.pie(
            df_acc_grouped, 
            values='평가금액', 
            names='계좌명', 
            hole=0.4,
            title='계좌별 평가금액 비중',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_acc.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='inherit',
            margin=dict(t=50, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_acc, use_container_width=True)
        
    with chart_col2:
        # 전체 자산 트리맵 (계좌명 -> 종목명 계층별 비중 파악에 최적)
        fig_tree = px.treemap(
            df_raw, 
            path=['계좌명', '종목명'], 
            values='평가금액',
            title='전체 포트폴리오 구성 트리맵 (종목명별)',
            color='평가금액',
            color_continuous_scale='YlGnBu'
        )
        fig_tree.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='inherit',
            margin=dict(t=50, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ==========================================
    # 6. 세부 포트폴리오 원장 데이터 그리드 (테이블 정렬)
    # ==========================================
    st.markdown('### 📋 세부 자산 보유 원장')
    
    # 3부 데이터 그리드와 동일한 일관적 칼럼 치수 적용
    COLUMN_DIMENSIONS = {
        "계좌명": st.column_config.TextColumn(width=120),
        "종목명": st.column_config.TextColumn(width=200),
        "티커": st.column_config.TextColumn(width=100),
        "보유수량": st.column_config.NumberColumn(width=90, format="%d"),
        "평균단가": st.column_config.NumberColumn(width=100, format="%d"),
        "현재가": st.column_config.NumberColumn(width=100, format="%d"),
        "매입금액": st.column_config.NumberColumn(width=110, format="%d"),
        "평가금액": st.column_config.NumberColumn(width=110, format="%d"),
        "손익률": st.column_config.NumberColumn(width=90, format="%.2f%%"),
        "MDD": st.column_config.NumberColumn(width=90, format="%.2f%%")
    }
    
    # 수익/하락에 따른 컬러링 포맷 적용
    def highlight_dataframe(val):
        if isinstance(val, (int, float)):
            if val > 0:
                color = '#FF6B6B'
            elif val < 0:
                color = '#58A6FF'
            else:
                color = 'inherit'
            return f'color: {color}; font-weight: bold;'
        return ''

    # 가상 테이블 포맷팅 매칭
    styled_df = df_raw.style.map(highlight_dataframe, subset=["손익률"]).format({
        "평가금액": "{:,.0f}",
        "매입금액": "{:,.0f}",
        "평균단가": "{:,.0f}",
        "현재가": "{:,.0f}"
    })
    
    st.dataframe(
        styled_df, 
        use_container_width=True, 
        height=400,
        column_config=COLUMN_DIMENSIONS
    )

except Exception as e:
    st.error(f"🚨 데이터 수집 및 연산 실패: {e}")
    st.warning("Gems 3.0 Secrets 연동 상태 및 구글 시트 공유 권한 설정을 검증하십시오.")
