from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from config import CYCLE_EXPIRY_DAYS
from engine.models import CycleState


def business_days_between(start_date: str, end_date: str) -> int:
    if not start_date:
        return 9999
    import pandas as pd
    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    if end < start:
        return 0
    return max(len(pd.bdate_range(start=start, end=end)) - 1, 0)


def update_cycle_state(
    state: CycleState,
    current_score: int,
    previous_score: int,
    market_date: str,
    data_status: str,
) -> CycleState:
    state.current_score = current_score

    should_close = (
        current_score <= 1
        or data_status == "DATA_INVALID"
        or state.manual_close
        or (state.days_since_last_buy >= CYCLE_EXPIRY_DAYS and bool(state.last_buy_date))
    )

    if state.cycle_active and should_close:
        return CycleState(index_code=state.index_code)

    can_start = (
        not state.cycle_active
        and previous_score <= 1
        and current_score >= 2
        and data_status == "DATA_VALID"
    )

    if can_start:
        state.cycle_active = True
        state.cycle_start_date = market_date
        state.cycle_id = f"{state.index_code}_{market_date.replace('-', '')}"
        state.initial_score = current_score
        state.highest_score = current_score
        state.last_purchased_score = -1
        state.cycle_invested_pct = 0.0

    if state.cycle_active:
        state.highest_score = max(state.highest_score, current_score)
        state.days_since_last_buy = business_days_between(state.last_buy_date, market_date)

    return state
