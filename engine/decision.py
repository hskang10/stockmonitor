from __future__ import annotations

from engine.models import EntryDecision


def cash_state(cash_ratio: float) -> str:
    if cash_ratio > 0.20:
        return "HIGH_CASH"
    if cash_ratio > 0.05:
        return "LOW_CASH"
    return "NO_CASH"


def determine_entry(
    score: int,
    trend: str,
    index_code: str,
    cash_ratio: float,
    cycle_invested_pct: float,
    last_purchased_score: int,
    days_since_last_buy: int,
    data_status: str,
    reversal_confirmed: bool,
    kospi_auto_enabled: bool,
) -> EntryDecision:
    is_kospi = index_code == "KOSPI"
    cstate = cash_state(cash_ratio)

    def result(action: str, pct: float, reason: str, allowed: bool, limit: float = 0.0):
        remaining = max(limit - cycle_invested_pct, 0.0)
        projected = max(cash_ratio * (1 - pct / 100), 0.0)
        return EntryDecision(action, pct, reason, allowed, limit, remaining, projected)

    if data_status == "DATA_INVALID":
        return result("DATA_INVALID", 0, "데이터 무효 상태이므로 주문을 차단합니다.", False)

    if data_status == "DATA_WARNING":
        return result("DATA_WARNING", 0, "데이터 경고가 해소될 때까지 자동 주문을 보류합니다.", False)

    if is_kospi and not kospi_auto_enabled:
        return result("AUTOTRADE_DISABLED", 0, "KOSPI 데이터 검증 전 자동매수를 금지합니다.", False)

    if cash_ratio <= 0.05:
        return result("CASH_LOCK", 0, "현금비중이 5% 이하이므로 신규 매수를 금지합니다.", False)

    if score <= 1:
        return result("NO_SIGNAL", 0, "과매도 점수가 1점 이하입니다.", False)

    if score <= last_purchased_score:
        return result(
            "SAME_LEVEL_LOCK",
            0,
            f"현재 {score}점은 이미 진입한 점수 이하이므로 중복 매수를 금지합니다.",
            False,
        )

    # 첫 매수는 즉시 가능. 이미 매수 이력이 있을 때만 쿨다운 적용.
    if last_purchased_score >= 0 and days_since_last_buy < 10:
        return result(
            "COOLDOWN",
            0,
            f"마지막 매수 후 {days_since_last_buy}거래일 경과. 최소 10거래일이 필요합니다.",
            False,
        )

    if trend == "TREND_UP":
        cycle_limit = 15.0 if is_kospi else 30.0
        step = 5.0 if is_kospi else 10.0

        if score == 2:
            action = "RECON"
            reason = "상승 추세에서 초기 과매도 2점이 확인되었습니다."
        elif score == 3:
            action = "MAIN_ENTRY"
            reason = "상승 추세에서 강한 과매도 3점이 확인되었습니다."
        else:
            action = "EXTREME_ENTRY"
            reason = "상승 추세에서 극단 과매도 4점이 확인되었습니다."

    else:
        cycle_limit = 5.0 if is_kospi else 10.0

        if score <= 2:
            return result("NO_SIGNAL", 0, "장기 하락 추세에서는 2점 이하 자동매수를 하지 않습니다.", False)

        if not reversal_confirmed:
            return result(
                "WAIT_REVERSAL",
                0,
                "장기 하락 추세이므로 RSI 반등·5일선 상향 돌파·양봉 조건을 기다립니다.",
                False,
                cycle_limit,
            )

        step = 5.0
        action = "EXTREME_RECON"
        reason = "장기 하락 추세에서 제한적 반등 확인 후 정찰매수만 허용합니다."

    remaining = max(cycle_limit - cycle_invested_pct, 0.0)
    if remaining <= 0:
        return result(
            "CYCLE_LIMIT",
            0,
            f"사이클 최대 투입한도 {cycle_limit:.0f}%를 소진했습니다.",
            False,
            cycle_limit,
        )

    buy_pct = min(step, remaining)

    if cstate == "LOW_CASH":
        if score == 2:
            return result(
                "CASH_LOCK",
                0,
                "LOW_CASH 상태에서는 2점 정찰매수를 금지합니다.",
                False,
                cycle_limit,
            )
        buy_pct = min(buy_pct, 10.0)
        reason += " LOW_CASH 한도를 적용했습니다."

    projected_cash_ratio = cash_ratio * (1 - buy_pct / 100)
    if projected_cash_ratio <= 0.05:
        return result(
            "CASH_LOCK",
            0,
            "주문 후 현금비중이 5% 이하가 되므로 주문을 금지합니다.",
            False,
            cycle_limit,
        )

    return result(action, buy_pct, reason, True, cycle_limit)
