"""Minimal client for Sleeper's public, read-only draft API (no login or key)."""

import re
import time

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This tool requires the 'requests' library. Install it with:\n"
        "    pip install requests"
    ) from exc

from .config import MAX_BACKOFF_SECONDS, SLEEPER_API_BASE


class SleeperAPIError(Exception):
    pass


def parse_draft_id(url_or_id):
    """Accepts a full Sleeper draft URL or a bare numeric draft ID."""
    s = url_or_id.strip()
    if s.isdigit():
        return s
    m = re.search(r"/draft/(?:[a-z]+/)?(\d+)", s)
    if m:
        return m.group(1)
    m = re.search(r"(\d{10,})", s)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract a draft ID from: {url_or_id!r}")


def _request_with_backoff(url, max_retries=6):
    delay = 2
    last_err = None
    for _ in range(max_retries):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            last_err = SleeperAPIError(f"HTTP {resp.status_code} from {url}")
        except requests.RequestException as e:
            last_err = e
        print(f"  [warn] request failed ({last_err}); retrying in {delay}s...")
        time.sleep(delay)
        delay = min(delay * 2, MAX_BACKOFF_SECONDS)
    raise SleeperAPIError(f"Giving up on {url}: {last_err}")


def get_draft_info(draft_id):
    return _request_with_backoff(f"{SLEEPER_API_BASE}/draft/{draft_id}")


def get_picks(draft_id):
    return _request_with_backoff(f"{SLEEPER_API_BASE}/draft/{draft_id}/picks")
