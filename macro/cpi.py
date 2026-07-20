from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

from config.constants import BLS_SERIES
from macro.bls_client import fetch_cpi_payload, parse_bls
from storage.database import save_cpi_release


@dataclass(frozen=True)
class CPIConsensus:
    headline_mom: float | None = None
    headline_yoy: float | None = None
    core_mom: float | None = None
    core_yoy: float | None = None


@dataclass(frozen=True)
class CPIResult:
    reference_month: str
    headline_index: float
    headline_mom: float
    headline_yoy: float
    core_index: float
    core_mom: float
    core_yoy: float
    headline_mom_surprise: float | None
    headline_yoy_surprise: float | None
    core_mom_surprise: float | None
    core_yoy_surprise: float | None
    classification: str
    multiplier: float
    delay_sessions: int
    rationale: str
    source: str = "BLS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _previous_month(yyyy_mm: str) -> str:
    year, month = map(int, yyyy_mm.split("-"))
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


def _year_ago(yyyy_mm: str) -> str:
    year, month = map(int, yyyy_mm.split("-"))
    return f"{year - 1:04d}-{month:02d}"


def _pct_change(current: float, previous: float) -> float:
    return (current / previous - 1) * 100


def _surprise(actual: float, consensus: float | None) -> float | None:
    return None if consensus is None else actual - consensus


def _classify(
    headline_mom_s: float | None,
    headline_yoy_s: float | None,
    core_mom_s: float | None,
    core_yoy_s: float | None,
) -> tuple[str, float, int, str]:
    surprises = [x for x in (headline_mom_s, headline_yoy_s, core_mom_s, core_yoy_s) if x is not None]
    if not surprises:
        return "Neutral", 1.00, 0, "예상치가 없어 CPI 실제값만 저장했습니다."

    core_values = [x for x in (core_mom_s, core_yoy_s) if x is not None]
    max_surprise = max(surprises)
    min_surprise = min(surprises)
    core_hot = any(x >= 0.10 for x in core_values)
    core_cool = bool(core_values) and all(x <= -0.10 for x in core_values)

    if max_surprise >= 0.20 or core_hot:
        return "Shock", 0.70, 1, "예상보다 높은 물가, 특히 근원 CPI 상방 서프라이즈를 감지했습니다."
    if min_surprise <= -0.20 or core_cool:
        return "Goldilocks", 1.30, 0, "예상보다 낮은 물가와 근원 CPI 둔화를 감지했습니다."
    return "Neutral", 1.00, 0, "예상치와 실제치 차이가 중립 범위입니다."


def load_cpi(
    reference_month: str,
    consensus: CPIConsensus,
    force_refresh: bool = False,
) -> CPIResult:
    year = int(reference_month[:4])
    payload = fetch_cpi_payload(year - 1, year, force_refresh=force_refresh)
    parsed = parse_bls(payload)

    current = reference_month
    previous = _previous_month(reference_month)
    year_ago = _year_ago(reference_month)
    headline = parsed.get(BLS_SERIES["headline"], {})
    core = parsed.get(BLS_SERIES["core"], {})

    required = {
        f"headline:{current}": headline.get(current),
        f"headline:{previous}": headline.get(previous),
        f"headline:{year_ago}": headline.get(year_ago),
        f"core:{current}": core.get(current),
        f"core:{previous}": core.get(previous),
        f"core:{year_ago}": core.get(year_ago),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise RuntimeError("BLS에서 예상 기준월을 확인하지 못해 처리를 중단합니다. 누락: " + ", ".join(missing))

    headline_mom = _pct_change(headline[current], headline[previous])
    headline_yoy = _pct_change(headline[current], headline[year_ago])
    core_mom = _pct_change(core[current], core[previous])
    core_yoy = _pct_change(core[current], core[year_ago])

    hm_s = _surprise(headline_mom, consensus.headline_mom)
    hy_s = _surprise(headline_yoy, consensus.headline_yoy)
    cm_s = _surprise(core_mom, consensus.core_mom)
    cy_s = _surprise(core_yoy, consensus.core_yoy)
    classification, multiplier, delay_sessions, rationale = _classify(hm_s, hy_s, cm_s, cy_s)

    result = CPIResult(
        reference_month=current,
        headline_index=headline[current],
        headline_mom=headline_mom,
        headline_yoy=headline_yoy,
        core_index=core[current],
        core_mom=core_mom,
        core_yoy=core_yoy,
        headline_mom_surprise=hm_s,
        headline_yoy_surprise=hy_s,
        core_mom_surprise=cm_s,
        core_yoy_surprise=cy_s,
        classification=classification,
        multiplier=multiplier,
        delay_sessions=delay_sessions,
        rationale=rationale,
    )

    record = result.to_dict() | {
        "headline_mom_consensus": consensus.headline_mom,
        "headline_yoy_consensus": consensus.headline_yoy,
        "core_mom_consensus": consensus.core_mom,
        "core_yoy_consensus": consensus.core_yoy,
    }
    save_cpi_release(record)
    return result
