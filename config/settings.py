from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("GOD_DB_PATH", "data/dashboard.db")
    bls_api_key: str = os.getenv("BLS_API_KEY", "")
    request_connect_timeout: int = int(os.getenv("REQUEST_CONNECT_TIMEOUT", "10"))
    request_read_timeout: int = int(os.getenv("REQUEST_READ_TIMEOUT", "90"))
    request_retries: int = int(os.getenv("REQUEST_RETRIES", "3"))


settings = Settings()
