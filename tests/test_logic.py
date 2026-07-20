from macro.bls_client import parse_bls
from macro.cpi import CPIConsensus, _classify


def test_parse_bls_skips_dash_and_reads_all_series():
    payload = {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": {"series": [
            {"seriesID": "A", "data": [
                {"year": "2026", "period": "M06", "value": "100.0"},
                {"year": "2026", "period": "M05", "value": "-"},
            ]},
            {"seriesID": "B", "data": [
                {"year": "2026", "period": "M06", "value": "200.0"},
            ]},
        ]},
    }
    result = parse_bls(payload)
    assert result == {"A": {"2026-06": 100.0}, "B": {"2026-06": 200.0}}


def test_cpi_classification():
    assert _classify(0.2, 0.0, 0.1, 0.0)[0] == "Shock"
    assert _classify(-0.2, 0.0, -0.1, -0.1)[0] == "Goldilocks"
