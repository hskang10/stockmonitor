from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from engine.models import CycleState

STATE_FILE = Path(__file__).resolve().parent / "cycle_state.json"
LOG_FILE = Path(__file__).resolve().parent / "signal_log.csv"


def load_states(index_codes: list[str]) -> Dict[str, CycleState]:
    raw = {}
    if STATE_FILE.exists():
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

    states: Dict[str, CycleState] = {}
    for code in index_codes:
        payload = raw.get(code, {})
        allowed = set(CycleState.__dataclass_fields__.keys())
        safe_payload = {k: v for k, v in payload.items() if k in allowed}
        states[code] = CycleState(index_code=code, **{k: v for k, v in safe_payload.items() if k != "index_code"})
    return states


def save_states(states: Dict[str, CycleState]) -> None:
    payload = {code: state.to_dict() for code, state in states.items()}
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_signal_log(row: dict) -> None:
    import pandas as pd
    df = pd.DataFrame([row])
    header = not LOG_FILE.exists()
    df.to_csv(LOG_FILE, mode="a", index=False, header=header, encoding="utf-8-sig")


def load_signal_log():
    import pandas as pd
    if not LOG_FILE.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(LOG_FILE)
    except Exception:
        return pd.DataFrame()
