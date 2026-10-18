"""Name normalisation and fuzzy matching of Sleeper picks to your rankings."""

import json
import re
from pathlib import Path

from .config import FUZZY_MATCH_THRESHOLD, OPTIONAL_POSITIONS

try:  # prefer rapidfuzz, fall back to the standard library
    from rapidfuzz import fuzz as _rf_fuzz

    def fuzzy_score(a, b):
        return _rf_fuzz.ratio(a, b)

    FUZZY_BACKEND = "rapidfuzz"
except ImportError:  # pragma: no cover - depends on environment
    import difflib

    def fuzzy_score(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio() * 100

    FUZZY_BACKEND = "difflib"

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name):
    """Lowercase, drop punctuation and generational suffixes, collapse spaces.

    "Ja'Marr Chase" -> "jamarr chase"; "Harold Fannin Jr." -> "harold fannin".
    """
    if not name:
        return ""
    n = name.strip().lower()
    n = n.replace("\u2019", "'").replace("\u2018", "'")
    for ch in ("'", ".", ","):
        n = n.replace(ch, "")
    n = re.sub(r"\s+", " ", n).strip()
    tokens = n.split(" ")
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def build_player_full_name(first_name, last_name):
    return f"{first_name or ''} {last_name or ''}".strip()


class NameMatcher:
    """Matches a Sleeper pick to a Player in your rankings.

    Order of attempts: saved alias -> exact normalised name -> fuzzy match
    (restricted to the same position). Confirmed fuzzy matches are saved to
    an alias file so they resolve instantly next time.
    """

    def __init__(self, rankings, alias_path=None):
        self.rankings = rankings
        self.alias_path = Path(alias_path) if alias_path else None
        self.aliases = {}
        if self.alias_path and self.alias_path.exists():
            with open(self.alias_path, "r", encoding="utf-8") as f:
                self.aliases = json.load(f)

    def _save_aliases(self):
        if self.alias_path:
            self.alias_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alias_path, "w", encoding="utf-8") as f:
                json.dump(self.aliases, f, indent=2, sort_keys=True)

    def match(self, sleeper_name, sleeper_pos, sleeper_team=None):
        """Returns (player_or_None, match_type): 'alias', 'exact', 'fuzzy(NN)' or 'none'."""
        norm = normalize_name(sleeper_name)

        if norm in self.aliases:
            players = self.rankings.lookup_exact(self.aliases[norm])
            if players:
                return self._disambiguate(players, sleeper_pos), "alias"

        players = self.rankings.lookup_exact(norm)
        if players:
            return self._disambiguate(players, sleeper_pos), "exact"

        # Positions like K/DEF that your sheet doesn't contain can't match
        # anything; skip rather than risk a bogus fuzzy hit on another player.
        if sleeper_pos in OPTIONAL_POSITIONS and sleeper_pos not in self.rankings.positions:
            return None, "none"

        candidates = self.rankings.lookup_by_position(sleeper_pos) if sleeper_pos else []
        if not candidates:
            candidates = self.rankings.players

        best_score, best = -1, None
        for p in candidates:
            score = fuzzy_score(norm, normalize_name(p.name))
            if score > best_score:
                best_score, best = score, p

        if best is not None and best_score >= FUZZY_MATCH_THRESHOLD:
            self.aliases[norm] = normalize_name(best.name)
            self._save_aliases()
            return best, f"fuzzy({best_score:.0f})"
        return None, "none"

    @staticmethod
    def _disambiguate(players, sleeper_pos):
        if len(players) == 1:
            return players[0]
        for p in players:
            if sleeper_pos and p.position == sleeper_pos:
                return p
        return players[0]
