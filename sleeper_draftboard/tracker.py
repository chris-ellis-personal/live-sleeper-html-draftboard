"""The polling loop: fetch picks from Sleeper, update state, redraw the board."""

import time
from datetime import datetime

from . import sleeper
from .config import OPTIONAL_POSITIONS
from .html_view import render_html
from .names import FUZZY_BACKEND, NameMatcher, build_player_full_name
from .rankings import strike_player
from .state import save_state, save_workbook_safely


class DraftTracker:
    def __init__(self, draft_id, rankings, paths, state, html_path, *, wb=None,
                 working_copy=None, whole_row=False, refresh=5, poll_interval=5,
                 title="Live Draft Board"):
        self.draft_id = draft_id
        self.rankings = rankings
        self.paths = paths
        self.state = state
        self.html_path = html_path
        self.wb = wb                      # None => HTML-only mode (no Excel writes)
        self.ws = rankings.ws
        self.working_copy = working_copy
        self.whole_row = whole_row
        self.refresh = refresh
        self.poll_interval = poll_interval
        self.title = title
        self.matcher = NameMatcher(rankings, alias_path=paths["aliases"])

        self.processed = set(state.get("processed_pick_nos", []))
        self.struck_coords = set(state.get("struck_coords", []))
        self.drafted_rows = set(state.get("drafted_master_rows", []))
        self.unmatched = list(state.get("unmatched_entries", []))

    # -- helpers ---------------------------------------------------------

    def reset(self):
        self.processed.clear()
        self.struck_coords.clear()
        self.drafted_rows.clear()
        self.unmatched.clear()

    def render(self):
        render_html(self.rankings, self.drafted_rows, self.draft_id, len(self.processed),
                    self.unmatched, self.html_path, self.refresh, self.title)

    def persist(self):
        self.state["processed_pick_nos"] = sorted(self.processed)
        self.state["struck_coords"] = sorted(self.struck_coords)
        self.state["drafted_master_rows"] = sorted(self.drafted_rows)
        self.state["unmatched_entries"] = self.unmatched
        save_state(self.paths["state"], self.state)
        if self.wb is not None:
            save_workbook_safely(self.wb, self.working_copy)

    # -- core ------------------------------------------------------------

    def process_picks(self, picks):
        """Applies any picks not yet seen. Returns True if anything changed."""
        if len(picks) < len(self.processed):
            print("  [!] Detected fewer picks than previously recorded -- this draft "
                  "appears to have been reset. Clearing processed-pick state.")
            self.reset()

        changed = False
        new_picks = [p for p in picks if p.get("pick_no") not in self.processed]
        for pick in sorted(new_picks, key=lambda p: p.get("pick_no", 0)):
            pick_no = pick.get("pick_no")
            meta = pick.get("metadata") or {}
            pos = (meta.get("position") or "").strip().upper()
            full_name = build_player_full_name(meta.get("first_name", ""),
                                               meta.get("last_name", ""))

            if not full_name.strip():
                self.processed.add(pick_no)
                continue

            player, match_type = self.matcher.match(full_name, pos, meta.get("team"))

            if player is None:
                self.processed.add(pick_no)
                if pos in OPTIONAL_POSITIONS and pos not in self.rankings.positions:
                    continue  # e.g. kickers/defenses your sheet doesn't track
                print(f"  Pick {pick_no}: UNMATCHED -- '{full_name}' ({pos})")
                self.unmatched.append([pick_no, full_name, pos])
                with open(self.paths["unmatched_log"], "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat(timespec='seconds')}\t"
                            f"pick={pick_no}\tname={full_name}\tpos={pos}\n")
                changed = True
                continue

            self.drafted_rows.add(player.master_row)
            if self.wb is not None:
                self.struck_coords.update(strike_player(
                    self.ws, self.rankings.layout, player, strike=True,
                    whole_row=self.whole_row))

            tag = "" if match_type in ("exact", "alias") else (
                f" [{match_type} match: '{full_name}' -> '{player.name}']")
            print(f"  Pick {pick_no}: {player.name} ({player.position}){tag}")
            self.processed.add(pick_no)
            changed = True
        return changed

    def run(self, open_browser_fn=None):
        print(f"Indexed {len(self.rankings.players)} players "
              f"({self.rankings.layout.describe()}).")
        print(f"Tracking draft {self.draft_id}. Polling every {self.poll_interval}s. "
              f"Press Ctrl+C to stop and save.")
        print(f"(fuzzy-match backend: {FUZZY_BACKEND})")
        print(f"HTML view: {self.html_path}")
        if self.wb is not None:
            print(f"Excel working copy: {self.working_copy}")
        print()

        self.render()  # something to look at before the first pick lands
        if open_browser_fn:
            open_browser_fn()

        while True:
            try:
                info = sleeper.get_draft_info(self.draft_id)
                picks = sleeper.get_picks(self.draft_id)
            except sleeper.SleeperAPIError as e:
                print(f"  [error] {e} -- will retry next cycle.")
                time.sleep(self.poll_interval)
                continue

            if self.process_picks(picks):
                self.persist()
            self.render()  # every cycle, so the timestamp stays alive

            if self.is_complete(info, picks):
                print(f"\nDraft {self.draft_id} is complete ({len(picks)} picks processed).")
                print(f"Final HTML view: {self.html_path}")
                if self.wb is not None:
                    print(f"Final workbook: {self.working_copy}")
                if self.unmatched:
                    print(f"{len(self.unmatched)} pick(s) could not be matched -- see "
                          f"{self.paths['unmatched_log']}")
                break
            time.sleep(self.poll_interval)

    @staticmethod
    def is_complete(info, picks):
        settings = info.get("settings") or {}
        rounds = settings.get("rounds")
        teams = settings.get("teams") or len(info.get("draft_order") or {})
        total = rounds * teams if rounds and teams else None
        return info.get("status") == "complete" or bool(total and len(picks) >= total)
