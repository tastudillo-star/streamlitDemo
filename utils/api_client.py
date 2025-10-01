from __future__ import annotations
import os, time
from typing import Any, Dict, Optional
import requests
from requests import Response
from dotenv import load_dotenv

load_dotenv()
DEFAULT_TIMEOUT = float(os.getenv("API_TIMEOUT", "8"))
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN", "")

def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    if extra:
        h.update(extra)
    return h

def _request_with_retry(method: str, path: str, *, params=None, json=None, data=None,
                        timeout: float = DEFAULT_TIMEOUT, retries: int = 1, backoff: float = 0.5,
                        headers: Optional[Dict[str, str]] = None) -> Response:
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return requests.request(
                method=method.upper(), url=url, params=params, json=json, data=data,
                headers=_headers(headers), timeout=timeout
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise
    assert last_exc is not None
    raise last_exc

def get(path: str, **kwargs) -> Response:    return _request_with_retry("GET", path, **kwargs)
def post(path: str, **kwargs) -> Response:   return _request_with_retry("POST", path, **kwargs)
def put(path: str, **kwargs) -> Response:    return _request_with_retry("PUT", path, **kwargs)
def delete(path: str, **kwargs) -> Response: return _request_with_retry("DELETE", path, **kwargs)
