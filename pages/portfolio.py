import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# 1. 페이지 최적화 설정
st.set_page_config(
    page_title="Gems 3.0 Portfolio Monitor", 
    layout="wide",
    initial_sidebar_state="expanded"
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

# 2. 캐싱 기반 구글 보안 인증 통신 활성화
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

# 3. 데이터 로딩 및 정량 수치 클리닝 프로세스
def load_and_clean_portfolio_data():
    gc = get_gspread_client()
    sh = gc.open_by_key("1NRqjEcEE9Wls2Um4C1sgYxGJLgfZkS_iy9SNXDIryKw")[span_1](start_span)[span_1](end_span)
    worksheet = sh.worksheet("포트폴리오")[span_2](start_span)[span_2](end_span)
    
    raw_values = worksheet.get_all_values()[span_3](start_span)[span_3](end_span)
    if not raw_values or len(raw_values) < 2:
        return pd.DataFrame()
        
    headers = raw_values[0][span_4](start_span)[span_4](end_span)
    rows = raw_values[1:][span_5](start_span)[span_5](end_span)
    
    df = pd.DataFrame(rows, columns=headers)[span_6](start_span)[span_6](end_span)
    
    # [오타 복구 프로토콜] 시트의 '펑가금액'을 '평가금액'으로 완전 교정[span_7](start_span)[span_7](end_span)
    if '펑가금액' in df.columns:[span_8](start_span)[span_8](end_span)
        df = df.rename(columns={'펑가금액': '평가금액'})[span_9](start_span)[span_9](end_span)
    
    # 공백 행 및 데이터 누락 전면 제거
    df = df[df['종목명'].str.strip() != ''].copy()[span_10](start_span)[span_10](end_span)
    df['계좌명'] = df['계좌명'].replace('', '기타/미지정').fillna('기타/미지정')[span_11](start_span)[span_11](end_span)
    
    # 수치 정량 클리닝 함수
    def clean_numeric(val):
        if pd.isna(val) or str(val).strip() == "":
            return 0.0
        val_str = str(val).strip()
        
        if val_str in ["-", "\\-", ""]:[span_12](start_span)[span_12](end_span)
            return 0.0
            
        is_negative = val_str.startswith('-') or val_str.startswith('\\-')[span_13](start_span)[span_13](end_span)
        cleaned = val_str.replace(",", "").replace("%", "").replace("-", "").replace("\\", "").strip()[span_14](start_span)[span_14](end_span)
        try:
            num = float(cleaned)
            return -num if is_negative else num
        except ValueError:
            return 0.0

    numeric_cols = ['보유수량', '평균단가', '현재가', '매입금액', '평가금액', '손익률', 'MDD'][span_15](start_span)[span_15](end_span)
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
            
    return df

try:
    df_raw = load_and_clean_portfolio_data()
    
    if df_raw.empty:
        st.warning("⚠️ 원장에서 자산 데이터를 팩팅하지 못했습니다. 포트폴리오 탭의 구조를 확인하십시오.")[span_16](start_span)[span_16](end_span)
    else:
        # ==========================================
        # 4. 최상단 실시간 계좌 요약 (Metrics)
        # ==========================================
        total_buy = df_raw['매입금액'].sum()[span_17](start_span)[span_17](end_span)
        total_eval = df_raw['평가금액'].sum()[span_18](start_span)[span_18](end_span)
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
            df_acc_grouped = df_raw.groupby('계좌명')['평가금액'].sum().reset_index()[span_19](start_span)[span_19](end_span)
            fig_acc = px.pie(
                df_acc_grouped, 
                values='평가금액', 
                names='계좌명', 
                hole=0.4,
                title='계좌별 평가금액 비중',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            # [교정] font_color를 'inherit' 대신 표준 컬러 코드인 '#888888'로 안전 락인하여 충돌 차단
            fig_acc.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#888888',
                margin=dict(t=50, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_acc, use_container_width=True)
            
        with chart_col2:
            fig_tree = px.treemap(
                df_raw, 
                path=['계좌명', '종목명'],[span_20](start_span)[span_20](end_span)
                values='평가금액',[span_21](start_span)[span_21](end_span)
                title='전체 포트폴리오 구성 트리맵 (종목명별)',
                color='평가금액',[span_22](start_span)[span_22](end_span)
                color_continuous_scale='YlGnBu'
            )
            # [교정] font_color를 '#888888'로 안전 락인하여 수치 연산 마비 차단
            fig_tree.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#888888',
                margin=dict(t=50, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_tree, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ==========================================
        # 6. 세부 포트폴리오 원장 데이터 그리드
        # ==========================================
        st.markdown('### 📋 세부 자산 보유 원장')
        
        COLUMN_DIMENSIONS = {
            "계좌명": st.column_config.TextColumn(width=120),[span_23](start_span)[span_23](end_span)
            "종목명": st.column_config.TextColumn(width=200),[span_24](start_span)[span_24](end_span)
            "티커": st.column_config.TextColumn(width=100),[span_25](start_span)[span_25](end_span)
            "보유수량": st.column_config.NumberColumn(width=90, format="%d"),[span_26](start_span)[span_26](end_span)
            "평균단가": st.column_config.NumberColumn(width=100, format="%d"),[span_27](start_span)[span_27](end_span)
            "현재가": st.column_config.NumberColumn(width=100, format="%d"),[span_28](start_span)[span_28](end_span)
            "매입금액": st.column_config.NumberColumn(width=110, format="%d"),[span_29](start_span)[span_29](end_span)
            "평가금액": st.column_config.NumberColumn(width=110, format="%d"),[span_30](start_span)[span_30](end_span)
            "손익률": st.column_config.NumberColumn(width=90, format="%.2f%%"),[span_31](start_span)[span_31](end_span)
            "MDD": st.column_config.NumberColumn(width=90, format="%.2f%%")[span_32](start_span)[span_32](end_span)
        }
        
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

        styled_df = df_raw.style.map(highlight_dataframe, subset=["손익률"]).format({
            "평가금액": "{:,.0f}",[span_33](start_span)[span_33](end_span)
            "매입금액": "{:,.0f}",[span_34](start_span)[span_34](end_span)
            "평균단가": "{:,.0f}",[span_35](start_span)[span_35](end_span)
            "현재가": "{:,.0f}[span_36](start_span)"[span_36](end_span)
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
