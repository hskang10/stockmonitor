from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class ValidationResult:
    status: str
    warnings: list[str]
    errors: list[str]
    latest_date: str
    stale_calendar_days: int
    abnormal_return: bool
    missing_recent_rows: int

    def to_dict(self) -> dict:
        return asdict(self)


def validate_market_data(
    df: pd.DataFrame,
    index_code: str,
    external_close: Optional[float] = None,
    max_stale_calendar_days: int = 7,
) -> ValidationResult:
    warnings: list[str] = []
    errors: list[str] = []

    if df.empty:
        return ValidationResult(
            status="DATA_INVALID",
            warnings=[],
            errors=["데이터가 비어 있습니다."],
            latest_date="",
            stale_calendar_days=999,
            abnormal_return=False,
            missing_recent_rows=0,
        )

    if df.index.duplicated().any():
        errors.append("중복 거래일이 존재합니다.")

    if not df.index.is_monotonic_increasing:
        warnings.append("날짜가 오름차순이 아니어서 정렬이 필요합니다.")

    if df["Close"].isna().any():
        errors.append("종가 결측치가 존재합니다.")

    if (df["Close"].dropna() <= 0).any():
        errors.append("0 이하의 종가가 존재합니다.")

    latest_date = pd.Timestamp(df.index.max()).normalize()
    today = pd.Timestamp.now().normalize()
    stale_days = int((today - latest_date).days)
    if stale_days > max_stale_calendar_days:
        warnings.append(f"최근 데이터가 {stale_days}일 전 값입니다.")

    returns = df["Close"].pct_change()
    abnormal_return = bool(returns.abs().iloc[-1] >= 0.10) if len(returns) else False
    if abnormal_return:
        msg = f"최근 일간 수익률 절댓값이 10% 이상입니다: {returns.iloc[-1] * 100:.2f}%"
        if index_code == "KOSPI":
            errors.append(msg)
        else:
            warnings.append(msg)

    recent = df.tail(20)
    missing_recent_rows = int(recent["Close"].isna().sum())
    if missing_recent_rows > 0:
        warnings.append(f"최근 20거래일 중 종가 결측 {missing_recent_rows}건")

    if len(df) < 346:
        warnings.append("200일 이동평균과 126개 백분위 표본을 동시에 확보하기에 데이터가 부족할 수 있습니다.")

    if external_close is not None and external_close > 0:
        latest_close = float(df["Close"].iloc[-1])
        gap = abs(latest_close / external_close - 1)
        if gap >= 0.02:
            msg = f"외부 검증 종가와 {gap * 100:.2f}% 차이"
            if index_code == "KOSPI":
                errors.append(msg)
            else:
                warnings.append(msg)

    status = "DATA_INVALID" if errors else ("DATA_WARNING" if warnings else "DATA_VALID")
    return ValidationResult(
        status=status,
        warnings=warnings,
        errors=errors,
        latest_date=latest_date.strftime("%Y-%m-%d"),
        stale_calendar_days=stale_days,
        abnormal_return=abnormal_return,
        missing_recent_rows=missing_recent_rows,
    )
