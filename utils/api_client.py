"""
Utilities to make simple HTTP requests to a configured API server with retries.

Env:
- API_BASE_URL: base URL for the API (default: http://localhost:8000)
- API_TOKEN: optional Bearer token to include initially (e.g., from secrets)
- API_TIMEOUT: default request timeout in seconds (default: 8)
"""

from __future__ import annotations
import os
import time
from typing import Dict, Optional
import requests
from requests import Response

class AuthError(Exception):
    """Indica que la autenticación es necesaria (token inválido/expirado)."""
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEFAULT_TIMEOUT = float(os.getenv("API_TIMEOUT", "8"))
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Token en memoria del proceso. No persistente.
_API_TOKEN = os.getenv("API_TOKEN", "").strip()

def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Headers básicos + Authorization si hay token en memoria."""
    h = {"Accept": "application/json"}
    if _API_TOKEN:
        h["Authorization"] = f"Bearer {_API_TOKEN}"
    if extra:
        h.update(extra)
    return h

def set_token(token: Optional[str]) -> None:
    """Configura el token en memoria. None/"" lo limpian."""
    global _API_TOKEN
    _API_TOKEN = (token or "").strip()

def get_token() -> Optional[str]:
    return _API_TOKEN or None

def _request_with_retry(
    method: str,
    path: str,
    *,
    params=None,
    json=None,
    data=None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 1,
    backoff: float = 0.5,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Request con reintentos para timeouts/conexión. Lanza AuthError en 401/403."""
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=_headers(headers),
                timeout=timeout,
            )

            if resp.status_code in (401, 403):
                # Limpiar token local
                try:
                    set_token(None)
                finally:
                    # Señalar a la UI (si existe) que debe re-autenticar
                    try:
                        import streamlit as st  # type: ignore
                        st.session_state["reauth_needed"] = True
                    except Exception:
                        pass
                raise AuthError(f"Authentication required ({resp.status_code})")

            return resp

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue
            raise
        except AuthError:
            # No reintentar sobre credenciales inválidas
            raise

    assert last_exc is not None
    raise last_exc

def get(path: str, **kwargs) -> Response:
    return _request_with_retry("GET", path, **kwargs)

def post(path: str, **kwargs) -> Response:
    return _request_with_retry("POST", path, **kwargs)

def put(path: str, **kwargs) -> Response:
    return _request_with_retry("PUT", path, **kwargs)

def delete(path: str, **kwargs) -> Response:
    return _request_with_retry("DELETE", path, **kwargs)
