from __future__ import annotations

from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.constants import BLS_SERIES
from config.settings import settings
from storage.database import get_cache, set_cache

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def _session() -> requests.Session:
    retry = Retry(
        total=settings.request_retries,
        connect=settings.request_retries,
        read=settings.request_retries,
        status=settings.request_retries,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_cpi_payload(start_year: int, end_year: int, force_refresh: bool = False) -> dict[str, Any]:
    cache_key = f"bls:cpi:{start_year}:{end_year}"
    if not force_refresh:
        cached = get_cache(cache_key)
        if cached:
            return cached

    body: dict[str, Any] = {
        "seriesid": list(BLS_SERIES.values()),
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if settings.bls_api_key:
        body["registrationkey"] = settings.bls_api_key

    try:
        response = _session().post(
            BLS_URL,
            json=body,
            timeout=(settings.request_connect_timeout, settings.request_read_timeout),
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        cached = get_cache(cache_key)
        if cached:
            return cached
        raise RuntimeError("BLS 서버 응답이 지연되었습니다. 잠시 후 다시 조회하세요.") from exc
    except requests.RequestException as exc:
        cached = get_cache(cache_key)
        if cached:
            return cached
        raise RuntimeError(f"BLS 통신 실패: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("BLS 응답을 JSON으로 해석하지 못했습니다.") from exc

    if payload.get("status") != "REQUEST_SUCCEEDED":
        messages = "; ".join(payload.get("message") or [])
        raise RuntimeError(f"BLS API 요청 실패: {messages or '알 수 없는 오류'}")

    set_cache(cache_key, payload)
    return payload


def parse_bls(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    if payload.get("status") != "REQUEST_SUCCEEDED":
        messages = "; ".join(payload.get("message") or [])
        raise RuntimeError(f"BLS API 요청 실패: {messages}")

    result: dict[str, dict[str, float]] = {}
    for series in payload.get("Results", {}).get("series", []):
        series_id = series.get("seriesID")
        if not series_id:
            continue
        values: dict[str, float] = {}
        for item in series.get("data", []):
            period = str(item.get("period", ""))
            if not period.startswith("M") or period == "M13":
                continue
            value = item.get("value")
            if value in (None, "", "-"):
                continue
            try:
                key = f"{int(item['year']):04d}-{int(period[1:]):02d}"
                values[key] = float(value)
            except (ValueError, TypeError, KeyError):
                continue
        result[series_id] = values
    return result
