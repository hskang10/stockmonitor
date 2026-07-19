from __future__ import annotations

from datetime import datetime
import math

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APP_TITLE,
    CACHE_TTL_SECONDS,
    DEFAULT_TARGET_WEIGHTS,
    INDEX_CONFIG,
    LOOKBACK_PERIOD,
    SYSTEM_STATUS,
    SYSTEM_USE,
)
from engine.cycle import update_cycle_state
from engine.data_loader import fetch_market_data
from engine.decision import cash_state, determine_entry
from engine.indicators import calculate_indicators
from engine.models import CycleState
from engine.validator import validate_market_data
from storage.state_store import append_signal_log, load_signal_log, load_states, save_states
from ui.components import decision_card, heatmap_chart, sparkline
from ui.theme import apply_theme


st.set_page_config(
    page_title="Gems 3.0 Market Entry Matrix",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_index_data(ticker: str, index_code: str, external_close: float | None):
    raw = fetch_market_data(ticker, LOOKBACK_PERIOD)
    raw = raw[~raw.index.duplicated(keep="last")].sort_index()
    validation = validate_market_data(raw, index_code, external_close)
    calc = calculate_indicators(raw)
    return calc, validation.to_dict()


def safe_float(value, default=np.nan):
    try:
        v = float(value)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def build_metric_row(
    name: str,
    cfg: dict,
    df: pd.DataFrame,
    validation: dict,
    state: CycleState,
    decision,
    current_weight: float,
) -> dict:
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    return {
        "DisplayName": name,
        "IndexCode": cfg["code"],
        "Ticker": cfg["ticker"],
        "Date": df.index[-1].strftime("%Y-%m-%d"),
        "Close": safe_float(curr["Close"], 0),
        "Ret": safe_float(curr["Ret"], 0) * 100,
        "MA5": safe_float(curr["MA5"]),
        "MA20": safe_float(curr["MA20"]),
        "MA60": safe_float(curr["MA60"]),
        "MA200": safe_float(curr["MA200"]),
        "Disparity20": safe_float(curr["Disparity20"]),
        "Disparity60": safe_float(curr["Disparity60"]),
        "Disparity200": safe_float(curr["Disparity200"]),
        "RSI14": safe_float(curr["RSI14"]),
        "D20_Q20": safe_float(curr["D20_Q20"]),
        "D60_Q20": safe_float(curr["D60_Q20"]),
        "D200_Q25": safe_float(curr["D200_Q25"]),
        "P20": int(curr["P20"]) if pd.notna(curr["P20"]) else 0,
        "P60": int(curr["P60"]) if pd.notna(curr["P60"]) else 0,
        "P200": int(curr["P200"]) if pd.notna(curr["P200"]) else 0,
        "PRSI": int(curr["PRSI"]) if pd.notna(curr["PRSI"]) else 0,
        "OversoldScore": int(curr["OversoldScore"]),
        "PreviousScore": int(prev["OversoldScore"]),
        "MA200_Slope20": safe_float(curr["MA200_Slope20"], 0) * 100,
        "TrendState": str(curr["TrendState"]),
        "ReversalConfirmed": bool(curr["ReversalConfirmed"]),
        "PctRank20": safe_float(curr["PctRank20"], 100),
        "PctRank60": safe_float(curr["PctRank60"], 100),
        "PctRank200": safe_float(curr["PctRank200"], 100),
        "PctRankRSI": safe_float(curr["PctRankRSI"], 100),
        "CompositePercentile": safe_float(curr["CompositePercentile"], 100),
        "DataStatus": validation["status"],
        "DataWarnings": " | ".join(validation["warnings"]),
        "DataErrors": " | ".join(validation["errors"]),
        "ActionCode": decision.action_code,
        "RecommendedCashPct": decision.recommended_cash_pct,
        "Reason": decision.reason,
        "OrderAllowed": decision.order_allowed,
        "CycleID": state.cycle_id,
        "CycleStartDate": state.cycle_start_date,
        "CycleActive": state.cycle_active,
        "InitialScore": state.initial_score,
        "HighestScore": state.highest_score,
        "LastPurchasedScore": state.last_purchased_score,
        "LastBuyDate": state.last_buy_date,
        "DaysSinceLastBuy": state.days_since_last_buy,
        "CycleInvestedPct": state.cycle_invested_pct,
        "CycleLimitPct": decision.cycle_limit_pct,
        "RemainingCapacityPct": max(decision.cycle_limit_pct - state.cycle_invested_pct, 0),
        "ProjectedCashRatio": decision.projected_cash_ratio,
        "TargetWeight": DEFAULT_TARGET_WEIGHTS.get(cfg["code"], 0),
        "CurrentWeight": current_weight,
        "WeightGap": DEFAULT_TARGET_WEIGHTS.get(cfg["code"], 0) - current_weight,
    }


st.markdown(f'<div class="main-title">🛡️ {APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">SYSTEM_STATUS = {SYSTEM_STATUS} · 用途 = {SYSTEM_USE} · 전액 자동매매 금지</div>',
    unsafe_allow_html=True,
)

codes = [cfg["code"] for cfg in INDEX_CONFIG.values()]
states = load_states(codes)

with st.sidebar:
    st.header("운용 상태")
    cash_ratio = st.slider("현재 현금비중", 0.0, 1.0, 0.35, 0.01)
    st.caption(f"현금 상태: **{cash_state(cash_ratio)}**")
    kospi_auto = st.checkbox("KOSPI 자동매수 활성화", False)
    st.warning("KOSPI 자동매수는 외부 종가 검증과 데이터 제공처 교차검증이 완료된 경우에만 켜십시오.")

    st.divider()
    st.subheader("포트폴리오 현재 비중")
    current_weights = {}
    for name, cfg in INDEX_CONFIG.items():
        current_weights[cfg["code"]] = st.number_input(
            f"{name} 현재비중",
            min_value=0.0,
            max_value=1.0,
            value=float(DEFAULT_TARGET_WEIGHTS[cfg["code"]]),
            step=0.01,
            key=f"weight_{cfg['code']}",
        )

    st.divider()
    st.subheader("외부 종가 검증")
    st.caption("0은 미입력. 입력하면 최근 종가와 2% 차이를 검사합니다.")
    external_closes = {}
    for name, cfg in INDEX_CONFIG.items():
        value = st.number_input(
            f"{name} 외부 검증 종가",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=f"external_{cfg['code']}",
        )
        external_closes[cfg["code"]] = value if value > 0 else None

    st.divider()
    if st.button("데이터 캐시 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

master_rows: list[dict] = []
series_store: dict[str, pd.DataFrame] = {}
load_errors: list[str] = []

with st.spinner("글로벌 지수 데이터와 진입조건을 계산하고 있습니다..."):
    for name, cfg in INDEX_CONFIG.items():
        try:
            df, validation = load_index_data(
                cfg["ticker"], cfg["code"], external_closes[cfg["code"]]
            )
            if len(df) < 2:
                raise RuntimeError("계산 가능한 데이터가 부족합니다.")

            curr_score = int(df.iloc[-1]["OversoldScore"])
            prev_score = int(df.iloc[-2]["OversoldScore"])
            state = states[cfg["code"]]
            state = update_cycle_state(
                state=state,
                current_score=curr_score,
                previous_score=prev_score,
                market_date=df.index[-1].strftime("%Y-%m-%d"),
                data_status=validation["status"],
            )

            decision = determine_entry(
                score=curr_score,
                trend=str(df.iloc[-1]["TrendState"]),
                index_code=cfg["code"],
                cash_ratio=cash_ratio,
                cycle_invested_pct=state.cycle_invested_pct,
                last_purchased_score=state.last_purchased_score,
                days_since_last_buy=state.days_since_last_buy,
                data_status=validation["status"],
                reversal_confirmed=bool(df.iloc[-1]["ReversalConfirmed"]),
                kospi_auto_enabled=kospi_auto,
            )
            state.cycle_limit_pct = decision.cycle_limit_pct
            states[cfg["code"]] = state
            row = build_metric_row(
                name, cfg, df, validation, state, decision, current_weights[cfg["code"]]
            )
            master_rows.append(row)
            series_store[cfg["code"]] = df
        except Exception as exc:
            load_errors.append(f"{name}: {exc}")

save_states(states)

if load_errors:
    st.error("일부 데이터를 불러오지 못했습니다.\n\n" + "\n".join(f"- {x}" for x in load_errors))

if not master_rows:
    st.stop()

master_rows.sort(
    key=lambda r: (
        -r["OversoldScore"],
        r["CompositePercentile"],
        -r["WeightGap"],
        0 if r["TrendState"] == "TREND_UP" else 1,
    )
)

allowed_rows = [r for r in master_rows if r["OrderAllowed"]]
top_action = allowed_rows[0] if allowed_rows else master_rows[0]

st.markdown("### 오늘의 행동 센터")
k1, k2, k3, k4 = st.columns(4)
k1.metric("최우선 지수", top_action["DisplayName"])
k2.metric("액션", top_action["ActionCode"])
k3.metric("권장 신규 투입", f"{top_action['RecommendedCashPct']:.0f}%")
k4.metric("현재 현금 상태", cash_state(cash_ratio))

if top_action["OrderAllowed"]:
    st.success(
        f"{top_action['DisplayName']}이 우선순위 1위입니다. "
        f"{top_action['Reason']} 권장 주문은 현재 가용 현금의 "
        f"{top_action['RecommendedCashPct']:.0f}%입니다."
    )
else:
    st.info(f"현재 즉시 주문 허용 신호가 없습니다. 최상위 상태: {top_action['ActionCode']}")

st.markdown("### 시장 요약 카드")
cols = st.columns(4)
by_name = {r["DisplayName"]: r for r in master_rows}
for i, name in enumerate(INDEX_CONFIG.keys()):
    with cols[i]:
        decision_card(by_name[name])
        sparkline(series_store[by_name[name]["IndexCode"]]["Close"].tail(126), "최근 6개월")

st.markdown("### 진입 우선순위")
rank_df = pd.DataFrame(master_rows)[
    [
        "DisplayName",
        "OversoldScore",
        "CompositePercentile",
        "TrendState",
        "WeightGap",
        "ActionCode",
        "RecommendedCashPct",
        "DataStatus",
    ]
].copy()
rank_df.insert(0, "Rank", range(1, len(rank_df) + 1))
rank_df["CompositePercentile"] = rank_df["CompositePercentile"].round(1)
rank_df["WeightGap"] = (rank_df["WeightGap"] * 100).round(1)
st.dataframe(
    rank_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": "순위",
        "DisplayName": "지수",
        "OversoldScore": "점수",
        "CompositePercentile": st.column_config.NumberColumn("종합 백분위", format="%.1f"),
        "TrendState": "추세",
        "WeightGap": st.column_config.NumberColumn("목표 대비 부족분", format="%.1f%%"),
        "ActionCode": "액션",
        "RecommendedCashPct": st.column_config.NumberColumn("신규 현금 투입", format="%.0f%%"),
        "DataStatus": "데이터",
    },
)

left, right = st.columns([1.2, 1])
with left:
    st.markdown("### 과매도 히트맵")
    heatmap_chart(master_rows)
with right:
    st.markdown("### 현금 배치 시뮬레이션")
    sim_df = pd.DataFrame(
        {
            "지수": [r["DisplayName"] for r in master_rows],
            "현재 현금비중": [cash_ratio * 100] * len(master_rows),
            "권장 주문": [r["RecommendedCashPct"] for r in master_rows],
            "주문 후 현금비중": [r["ProjectedCashRatio"] * 100 for r in master_rows],
        }
    )
    st.dataframe(
        sim_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "현재 현금비중": st.column_config.ProgressColumn(
                "현재 현금비중", min_value=0, max_value=100, format="%.1f%%"
            ),
            "권장 주문": st.column_config.NumberColumn("권장 주문", format="%.0f%%"),
            "주문 후 현금비중": st.column_config.ProgressColumn(
                "주문 후 현금비중", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )

tabs = st.tabs(["지표 상세", "사이클 관리", "신호 로그", "운용 설명"])

with tabs[0]:
    detail_cols = [
        "DisplayName", "Date", "Close", "MA5", "MA20", "MA60", "MA200",
        "Disparity20", "D20_Q20", "Disparity60", "D60_Q20",
        "Disparity200", "D200_Q25", "RSI14",
        "P20", "P60", "P200", "PRSI", "OversoldScore",
        "MA200_Slope20", "TrendState", "ReversalConfirmed",
        "DataStatus",
    ]
    detail_df = pd.DataFrame(master_rows)[detail_cols]
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

with tabs[1]:
    st.caption("실제 매수를 실행한 뒤 아래 버튼으로 사이클 상태를 기록하십시오.")
    for row in master_rows:
        code = row["IndexCode"]
        state = states[code]
        with st.expander(f"{row['DisplayName']} · {row['CycleID'] or '비활성 사이클'}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재 점수", row["OversoldScore"])
            c2.metric("마지막 매수 점수", state.last_purchased_score)
            c3.metric("누적 투입", f"{state.cycle_invested_pct:.0f}%")
            c4.metric("남은 한도", f"{row['RemainingCapacityPct']:.0f}%")

            amount = st.number_input(
                "기록할 현금 투입비율(%)",
                0.0,
                30.0,
                float(row["RecommendedCashPct"]),
                5.0,
                key=f"amount_{code}",
            )

            b1, b2 = st.columns(2)
            if b1.button(
                "매수 실행 기록",
                key=f"buy_{code}",
                disabled=not row["OrderAllowed"],
                use_container_width=True,
            ):
                state.last_purchased_score = row["OversoldScore"]
                state.last_buy_date = row["Date"]
                state.days_since_last_buy = 0
                state.cycle_invested_pct += amount
                state.highest_score = max(state.highest_score, row["OversoldScore"])
                states[code] = state
                save_states(states)
                append_signal_log(
                    {
                        "Timestamp": datetime.now().isoformat(timespec="seconds"),
                        "MarketDate": row["Date"],
                        "IndexCode": code,
                        "DisplayName": row["DisplayName"],
                        "Score": row["OversoldScore"],
                        "ActionCode": row["ActionCode"],
                        "InvestedCashPct": amount,
                        "CycleID": state.cycle_id,
                        "CycleInvestedPct": state.cycle_invested_pct,
                        "Reason": row["Reason"],
                    }
                )
                st.success("매수 실행 상태를 기록했습니다.")
                st.rerun()

            if b2.button("사이클 수동 종료", key=f"close_{code}", use_container_width=True):
                states[code] = CycleState(index_code=code)
                save_states(states)
                st.warning("사이클을 종료했습니다.")
                st.rerun()

with tabs[2]:
    log_df = load_signal_log()
    if log_df.empty:
        st.info("아직 기록된 매수 로그가 없습니다.")
    else:
        st.dataframe(log_df.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "신호 로그 CSV 다운로드",
            data=log_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="signal_log.csv",
            mime="text/csv",
        )

with tabs[3]:
    st.markdown(
        """
        **판정 순서**

        1. 데이터 무결성을 먼저 검사합니다.
        2. 20일·60일·200일 이격도와 Wilder RSI14를 계산합니다.
        3. 당일을 제외한 이전 252거래일 분포로 백분위 임계값을 계산합니다.
        4. 과매도 점수와 200일 이동평균 추세를 분리합니다.
        5. 사이클 중복 진입, 쿨다운, 현금상태, KOSPI 예외를 적용합니다.
        6. 여러 지수가 동시에 충족되면 점수 → 종합 백분위 → 목표비중 부족분 → 상승추세 순으로 정렬합니다.

        **주의**

        이 앱은 주문을 직접 전송하지 않습니다. 실제 주문 전 데이터 제공처, 환율, 계좌별 세금,
        ETF 추적오차와 체결가격을 별도로 확인해야 합니다.
        """
    )
