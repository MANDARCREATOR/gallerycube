"""
Update Checker Module for Gallery Cube (RMSCUBE Ecosystem).
Checks rmscube.com/version.json quietly in the background without blocking the UI.
"""

import json
import threading
import urllib.request
from typing import Optional, Dict, Any, Callable

CURRENT_VERSION = "1.0.0"
VERSION_CHECK_URL = "https://rmscube.com/version.json"


def parse_version(ver_str: str) -> tuple:
    """Parse version string like '1.2.3' into (1, 2, 3) for clean numeric comparison."""
    try:
        clean = ver_str.strip().lstrip("vV")
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts)
    except Exception:
        return (0, 0, 0)


def is_newer_version(latest_str: str, current_str: str = CURRENT_VERSION) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    return parse_version(latest_str) > parse_version(current_str)


def check_for_updates_sync(url: str = VERSION_CHECK_URL, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """
    Synchronously fetches version.json from rmscube.com.
    Returns update info dict if a newer version is available, else None.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"GalleryCube/{CURRENT_VERSION} (Windows NT)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                latest_ver = data.get("latest_version", "")
                if is_newer_version(latest_ver, CURRENT_VERSION):
                    return data
    except Exception:
        # Fails silently if offline or network unreachable
        pass
    return None


def check_for_updates_async(
    on_update_found: Callable[[Dict[str, Any]], None],
    on_up_to_date: Optional[Callable[[], None]] = None,
    url: str = VERSION_CHECK_URL
) -> threading.Thread:
    """
    Spawns a background thread to check for updates.
    Invokes on_update_found(data) if a newer version exists.
    Invokes on_up_to_date() if current version is already the latest.
    """
    def _worker():
        data = check_for_updates_sync(url=url)
        if data:
            if on_update_found:
                on_update_found(data)
        else:
            if on_up_to_date:
                on_up_to_date()

    t = threading.Thread(target=_worker, daemon=True, name="GalleryCube-Updater")
    t.start()
    return t

