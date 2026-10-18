"""Persistent run state (resume support), lock file, and safe workbook saving."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def state_paths(state_dir, draft_id):
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    base = state_dir / f"draft_{draft_id}"
    return {
        "dir": state_dir,
        "state": Path(f"{base}.json"),
        "lock": Path(f"{base}.lock"),
        "unmatched_log": Path(f"{base}_unmatched.log"),
        "aliases": state_dir / "name_aliases.json",
    }


def new_state():
    return {
        "processed_pick_nos": [],
        "struck_coords": [],
        "drafted_master_rows": [],
        "unmatched_entries": [],
        "working_copy": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def load_state(path):
    path = Path(path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            state = new_state()
            state.update(json.load(f))
            return state
    return new_state()


def save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# -- lock file: prevents two concurrent runs against the same draft ----------

def _pid_alive(pid):
    if sys.platform == "win32":
        # os.kill(pid, 0) is NOT a harmless liveness check on Windows (signal 0
        # maps to CTRL_C_EVENT), so ask the Win32 API instead.
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False
    return True


def acquire_lock(lock_path):
    lock_path = Path(lock_path)
    if lock_path.exists():
        try:
            old_pid = int(lock_path.read_text().strip())
        except ValueError:
            old_pid = None
        if old_pid and old_pid != os.getpid() and _pid_alive(old_pid):
            raise RuntimeError(
                f"Another instance (PID {old_pid}) appears to already be tracking "
                f"this draft. If that's not true (stale lock), delete: {lock_path}"
            )
    lock_path.write_text(str(os.getpid()))


def release_lock(lock_path):
    try:
        Path(lock_path).unlink()
    except OSError:
        pass


def save_workbook_safely(wb, path, retries=3, wait_seconds=5):
    """Save, retrying if the file is open in Excel (which locks it on Windows)."""
    for attempt in range(retries):
        try:
            wb.save(path)
            return True
        except PermissionError:
            print(f"\n  [!] Could not save '{path}' -- it looks like the file is open "
                  f"in Excel. Please close it.")
            if attempt < retries - 1:
                print(f"      Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
    print(f"  [!] Giving up trying to save '{path}' after {retries} attempts.")
    return False
