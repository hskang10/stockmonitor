from __future__ import annotations

from dataclasses import dataclass, asdict
from decision.oversold_score import TechnicalDecision
from macro.cpi import CPIResult


@dataclass(frozen=True)
class FinalDecision:
    technical_buy_ratio: float
    macro_multiplier: float
    final_buy_ratio: float
    delay_sessions: int
    action: str

    def to_dict(self) -> dict:
        return asdict(self)


def combine(technical: TechnicalDecision, cpi: CPIResult | None) -> FinalDecision:
    multiplier = cpi.multiplier if cpi else 1.0
    delay = cpi.delay_sessions if cpi else 0
    final_ratio = min(1.0, max(0.0, technical.technical_buy_ratio * multiplier))

    if technical.technical_buy_ratio == 0:
        action = "관망"
    elif delay > 0:
        action = f"{delay}개 정규 세션 대기 후 현금의 {final_ratio:.0%} 검토"
    else:
        action = f"현금의 {final_ratio:.0%} 단계 진입 검토"

    return FinalDecision(
        technical_buy_ratio=technical.technical_buy_ratio,
        macro_multiplier=multiplier,
        final_buy_ratio=final_ratio,
        delay_sessions=delay,
        action=action,
    )
