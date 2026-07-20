from __future__ import annotations

from datetime import date
import streamlit as st

from macro.cpi import CPIConsensus, CPIResult, load_cpi


def _default_reference_month() -> str:
    today = date.today()
    # 일반적으로 가장 최근 완료월을 기본값으로 한다.
    year, month = today.year, today.month - 1
    if month == 0:
        year, month = year - 1, 12
    return f"{year:04d}-{month:02d}"


def render_macro_panel() -> CPIResult | None:
    st.subheader("Macro Engine v1 · CPI")
    st.caption("BLS 계절조정 CPI 지수로 MoM·YoY를 계산하고 컨센서스 대비 서프라이즈를 판정합니다.")

    with st.form("cpi_form"):
        c1, c2, c3 = st.columns(3)
        reference_month = c1.text_input("CPI 기준월 (YYYY-MM)", value=_default_reference_month())
        force_refresh = c2.checkbox("BLS 강제 새로고침", value=False)
        c3.write("")

        st.markdown("**시장 예상치(%, 선택)**")
        a, b, c, d = st.columns(4)
        hm = a.number_input("Headline MoM", value=0.0, step=0.1, format="%.2f")
        hy = b.number_input("Headline YoY", value=0.0, step=0.1, format="%.2f")
        cm = c.number_input("Core MoM", value=0.0, step=0.1, format="%.2f")
        cy = d.number_input("Core YoY", value=0.0, step=0.1, format="%.2f")
        use_consensus = st.checkbox("입력한 예상치를 판정에 사용", value=True)
        submitted = st.form_submit_button("BLS 조회 및 CPI 판정", width="stretch")

    if submitted:
        try:
            consensus = CPIConsensus(
                headline_mom=hm if use_consensus else None,
                headline_yoy=hy if use_consensus else None,
                core_mom=cm if use_consensus else None,
                core_yoy=cy if use_consensus else None,
            )
            result = load_cpi(reference_month.strip(), consensus, force_refresh=force_refresh)
            st.session_state["cpi_result"] = result
        except Exception as exc:
            st.error(str(exc))

    result = st.session_state.get("cpi_result")
    if not result:
        st.info("CPI를 조회하면 기술적 신호에 매크로 배수가 결합됩니다.")
        return None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Headline MoM", f"{result.headline_mom:.2f}%", _fmt_surprise(result.headline_mom_surprise))
    c2.metric("Headline YoY", f"{result.headline_yoy:.2f}%", _fmt_surprise(result.headline_yoy_surprise))
    c3.metric("Core MoM", f"{result.core_mom:.2f}%", _fmt_surprise(result.core_mom_surprise))
    c4.metric("Core YoY", f"{result.core_yoy:.2f}%", _fmt_surprise(result.core_yoy_surprise))

    level = {"Shock": "error", "Goldilocks": "success", "Neutral": "warning"}[result.classification]
    getattr(st, level)(
        f"판정: {result.classification} · 배수 {result.multiplier:.2f}x · 지연 {result.delay_sessions}세션 — {result.rationale}"
    )
    return result


def _fmt_surprise(value: float | None) -> str | None:
    return None if value is None else f"예상 대비 {value:+.2f}%p"
