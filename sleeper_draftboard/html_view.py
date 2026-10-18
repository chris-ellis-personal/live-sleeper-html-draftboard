"""Renders the self-contained, auto-refreshing HTML board."""

import html as html_lib
import os
from datetime import datetime

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{refresh_seconds}">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, Segoe UI, Arial, sans-serif;
    background: #111418;
    color: #e6e6e6;
    margin: 0;
    padding: 24px;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px 0; }}
  .meta {{ color: #9aa4b2; font-size: 13px; margin-bottom: 20px; }}
  .board {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
  }}
  .col {{
    background: #1a1f27;
    border-radius: 8px;
    padding: 12px 14px;
    border: 1px solid #2a303b;
  }}
  .col h2 {{
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8fb3ff;
    margin: 0 0 10px 0;
    border-bottom: 1px solid #2a303b;
    padding-bottom: 6px;
  }}
  ol {{ margin: 0; padding-left: 22px; }}
  li {{ padding: 3px 0; font-size: 13.5px; }}
  li .team {{ color: #8a93a3; font-size: 12px; }}
  li.drafted {{ text-decoration: line-through; color: #566072; }}
  li.drafted .team {{ color: #45505f; }}
  .unmatched {{
    margin-top: 24px;
    background: #241a1a;
    border: 1px solid #4a2a2a;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 13px;
    color: #d99;
    max-height: 160px;
    overflow-y: auto;
  }}
  .unmatched h2 {{
    font-size: 13px; margin: 0 0 8px 0; color: #e79;
    text-transform: uppercase; letter-spacing: 0.06em;
  }}
</style>
<script>
  // The page reloads itself every few seconds; remember the scroll position
  // so a refresh doesn't throw you back to the top of a long list.
  (function () {{
    var KEY = "draftboard-scroll";
    try {{
      window.addEventListener("beforeunload", function () {{
        sessionStorage.setItem(KEY, String(window.scrollY));
      }});
      window.addEventListener("load", function () {{
        var y = parseInt(sessionStorage.getItem(KEY) || "0", 10);
        if (y) window.scrollTo(0, y);
      }});
    }} catch (e) {{ /* storage unavailable: fall back to default behaviour */ }}
  }})();
</script>
</head>
<body>
<h1>{title}</h1>
<div class="meta">Draft {draft_id} &middot; last updated {timestamp} &middot;
auto-refreshes every {refresh_seconds}s &middot; {picks_processed} picks processed</div>
<div class="board">
{columns}
</div>
{unmatched_block}
</body>
</html>
"""

COLUMN_TEMPLATE = """<div class="col">
  <h2>{heading}</h2>
  <ol>
{rows}
  </ol>
</div>
"""

ROW_TEMPLATE = '    <li class="{cls}">{name} <span class="team">{team}</span></li>'
OVERALL_ROW_TEMPLATE = ('    <li class="{cls}">{name} '
                        '<span class="team">{team} &middot; {pos}</span></li>')


def _esc(s):
    return html_lib.escape("" if s is None else str(s))


def render_html(rankings, drafted_master_rows, draft_id, picks_processed,
                unmatched_entries, out_path, refresh_seconds, title="Live Draft Board"):
    """Writes the board: an Overall column (your master order) followed by one
    column per position, with drafted players struck through. Reads straight
    from the master list, which is always populated, unlike spilled formula
    cells that depend on Excel having recalculated."""

    def cls_for(player):
        return "drafted" if player.master_row in drafted_master_rows else ""

    columns = []

    overall = sorted(rankings.players, key=lambda p: p.master_row)
    columns.append(COLUMN_TEMPLATE.format(
        heading="Overall",
        rows="\n".join(OVERALL_ROW_TEMPLATE.format(
            cls=cls_for(p), name=_esc(p.name), team=_esc(p.team), pos=_esc(p.position))
            for p in overall),
    ))

    for pos in rankings.positions:
        players = sorted(rankings.lookup_by_position(pos), key=lambda p: p.master_row)
        columns.append(COLUMN_TEMPLATE.format(
            heading=_esc(pos),
            rows="\n".join(ROW_TEMPLATE.format(
                cls=cls_for(p), name=_esc(p.name), team=_esc(p.team)) for p in players),
        ))

    unmatched_block = ""
    if unmatched_entries:
        items = "".join(
            f"<div>pick {_esc(p)}: {_esc(name)} ({_esc(pos)})</div>"
            for p, name, pos in unmatched_entries[-30:]
        )
        unmatched_block = ('<div class="unmatched"><h2>Unmatched picks '
                           f'(not in your rankings)</h2>{items}</div>')

    page = HTML_TEMPLATE.format(
        title=_esc(title),
        refresh_seconds=refresh_seconds,
        draft_id=_esc(draft_id),
        timestamp=_esc(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        picks_processed=picks_processed,
        columns="\n".join(columns),
        unmatched_block=unmatched_block,
    )

    out_path = str(out_path)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(page)
    os.replace(tmp_path, out_path)  # atomic swap: the browser never sees a half-written file
