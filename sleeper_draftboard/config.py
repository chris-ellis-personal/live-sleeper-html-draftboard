"""Defaults and tunables. Nothing in here depends on where the project lives."""

import os
from pathlib import Path

SLEEPER_API_BASE = "https://api.sleeper.app/v1"

POLL_INTERVAL_SECONDS = 5      # conservative; well under Sleeper's published limit
MAX_BACKOFF_SECONDS = 60
FUZZY_MATCH_THRESHOLD = 88     # 0-100; below this a pick is logged as unmatched

# Positions Sleeper drafts that most rankings sheets don't include. If your
# sheet has no row with this position, picks at it are skipped silently
# instead of being reported as "unmatched".
OPTIONAL_POSITIONS = {"K", "DEF"}

# Display order for position columns in the HTML view; any other positions
# found in your sheet are appended after these in the order they appear.
PREFERRED_POSITION_ORDER = ["QB", "RB", "WR", "TE"]

STATE_DIR_ENV_VAR = "SLEEPER_DRAFTBOARD_STATE_DIR"


def default_state_dir() -> Path:
    """Where progress / lock / alias files live.

    Order of precedence: --state-dir flag (handled by the CLI), then the
    SLEEPER_DRAFTBOARD_STATE_DIR environment variable, then a hidden folder
    in the user's home directory. It is deliberately *not* relative to the
    current working directory, so it doesn't matter where you launch from.
    """
    env = os.environ.get(STATE_DIR_ENV_VAR)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".sleeper_draftboard"
