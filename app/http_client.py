"""Shared HTTP client with retry logic.

Replaces duplicated requests.Session() + User-Agent setup in
stock_service, ihsg_service, foreign_flow_service.
"""

import time
import logging
from typing import Optional

import requests

from app.constants import HEADERS

logger = logging.getLogger(__name__)


def get_http_client(timeout: int = 15) -> requests.Session:
    """Return a pre-configured requests.Session with standard headers."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.timeout = timeout
    return session


def fetch_with_retry(
    url: str,
    params: Optional[dict] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    session: Optional[requests.Session] = None,
) -> Optional[requests.Response]:
    """Fetch a URL with exponential backoff.

    Args:
        url: Target URL
        params: Optional query parameters
        max_retries: Number of retries on failure (default 3)
        base_delay: Initial delay in seconds, doubles each retry
        session: Optional pre-configured session, created fresh if omitted

    Returns:
        Response on success, None on repeated failure
    """
    if session is None:
        session = get_http_client()

    for attempt in range(max_retries):
        try:
            resp = session.get(url, params=params)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning(
                "HTTP error %s (attempt %d/%d): %s",
                url, attempt + 1, max_retries, e,
            )
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2**attempt))
    return None
