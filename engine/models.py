from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CycleState:
    index_code: str
    cycle_id: str = ""
    cycle_start_date: str = ""
    cycle_active: bool = False
    initial_score: int = 0
    current_score: int = 0
    highest_score: int = 0
    last_purchased_score: int = -1
    last_buy_date: str = ""
    days_since_last_buy: int = 9999
    cycle_invested_pct: float = 0.0
    cycle_limit_pct: float = 0.0
    manual_close: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EntryDecision:
    action_code: str
    recommended_cash_pct: float
    reason: str
    order_allowed: bool
    cycle_limit_pct: float
    remaining_capacity_pct: float
    projected_cash_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)
