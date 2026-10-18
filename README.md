# Live Sleeper Draft Board

**A live, auto-refreshing HTML draft board for [Sleeper](https://sleeper.com) fantasy football drafts, built from your own rankings spreadsheet.**

Keep one browser tab open on a second monitor and watch players get struck through the moment they're drafted, in your own rankings and tiers, with no closing and reopening Excel.

## Features

- **Live board in your browser.** One self-contained `.html` file, rewritten on every poll and auto-reloaded by the browser. Columns for Overall plus each position, drafted players struck through.
- **Uses *your* rankings.** Point it at any `.xlsx` with a name column and a position column. Columns are found by their headers, not hardcoded letters.
- **Smart name matching.** Handles `Ja'Marr`, `A.J.`, `Jr./III` suffixes, hyphens and small spelling differences. Fuzzy matches are remembered.
- **Optional Excel strikethrough.** Also keeps a `*_LIVE.xlsx` working copy with drafted players struck through, including in per-position tier blocks. Your original file is never modified. Use `--no-excel` to skip it.
- **Resumable.** Stop and restart mid-draft and it picks up where it left off. Detects a reset draft (mock drafts) automatically.
- **No account, no API key.** Uses Sleeper's public read-only draft endpoints. Your credentials are never involved.
- **Unmatched picks are surfaced** on the board (and in a log) so you can spot players missing from your rankings.

## Quick start

Requires Python 3.9+.

```bash
git clone https://github.com/chris-ellis-personal/live-sleeper-html-draftboard.git
cd live-sleeper-html-draftboard
pip install -r requirements.txt

python -m sleeper_draftboard run \
  --file "path/to/your_rankings.xlsx" \
  --draft "https://sleeper.com/draft/nfl/<your-draft-id>" \
  --open-browser
```

Try it without your own file using the bundled template: `--file examples/example_player_rankings.xlsx`. It's also the quickest way to see the expected spreadsheet layout (see [Rankings spreadsheet format](#rankings-spreadsheet-format)).

Optional: `pip install .` installs a `sleeper-draftboard` command, so you can drop the `python -m` part. `pip install rapidfuzz` gives faster fuzzy matching (it falls back to the standard library otherwise).

Run with no arguments (`python -m sleeper_draftboard`) for a guided prompt.

### Windows example

```bat
cd C:\path\to\live-sleeper-html-draftboard
python -m sleeper_draftboard run --file "C:\Drafts\my rankings.xlsx" --draft https://sleeper.com/draft/nfl/1234567890123456789 --open-browser
```

You can run the command from any folder. Nothing depends on where you launch it.

## Rankings spreadsheet format

The tool reads the **first row** (configurable with `--header-row`) to find your columns:

| Column | Recognised headers (case-insensitive) | Required |
|---|---|---|
| Player name | `PLAYER NAME`, `PLAYER`, `NAME` | yes |
| Position | `POS.`, `POS`, `POSITION` | yes |
| Team | `TEAM`, `TM` | no |
| Bye | `BYE`, `BYE WEEK` | no |

Players are listed top to bottom in your ranked order starting on the row under the header. The Overall column follows that order, and each position column keeps it within that position. Use `--sheet` to pick a worksheet other than the active one.

### Template

[`examples/example_player_rankings.xlsx`](examples/example_player_rankings.xlsx) is a ready-made template in exactly this format: a 166-player master list in columns A-D, plus QB/WR/RB/TE tier blocks driven by `FILTER()` formulas. Copy it and replace the players with your own rankings. The rankings in it are the author's own and are included only as an example of the layout, not as advice. Tier blocks use dynamic-array `FILTER()`, which needs Excel 365/2021 or later.

### Optional: tier blocks (for the Excel working copy)

If you maintain per-position panels in the same sheet, the tool will strike players out there too. A block is six columns starting at a header cell reading `QB TIERS`, `WR TIERS`, `RB TIERS`, `TE TIERS`, etc.:

```
| <POS> TIERS | team | bye | pos | Overall rank | Tier rank |
```

Row *n* of a block must mirror the *n*th player of that position in the master list. That is exactly what a formula like this produces (anchored on row 2):

```
=FILTER(A2:D200, D2:D200="QB")
```

No blocks? That's fine. The HTML board and master-list strikethrough work without them.

## Command reference

```
python -m sleeper_draftboard run [options]
python -m sleeper_draftboard revert --draft <url_or_id>
```

| Option | Description |
|---|---|
| `--file PATH` | Your rankings `.xlsx` (prompted for if omitted). |
| `--draft URL_OR_ID` | Sleeper draft URL or numeric ID (prompted for if omitted). |
| `--open-browser` | Open the board in your default browser on start. |
| `--no-excel` | HTML board only; don't create or update an `.xlsx` copy. |
| `--whole-row` | In the Excel copy, strike the whole row, not just the name. |
| `--sheet NAME_OR_INDEX` | Worksheet to read (default: the active sheet). |
| `--header-row N` | Row containing your headers (default `1`). |
| `--output-dir DIR` | Where the HTML and Excel copy are written (default: next to your rankings file). |
| `--title TEXT` | Heading shown on the board. |
| `--poll-interval SECS` | How often to ask Sleeper for new picks (default `5`). |
| `--refresh SECS` | Browser reload interval (default: the poll interval). |
| `--state-dir DIR` | Where progress is stored (see below). |

`revert` deletes the generated `*_LIVE.xlsx` and saved progress for a draft, so the next run starts clean (use it after editing your rankings, since a resumed run keeps using the existing working copy). It never touches your original file.

## What gets written where

| File | Location | Purpose |
|---|---|---|
| `<name>_live_view.html` | `--output-dir` (default: beside your rankings) | The board. Open it in a browser. |
| `<name>_LIVE.xlsx` | `--output-dir` | Excel working copy (skipped with `--no-excel`). |
| `draft_<id>.json`, `.lock`, `_unmatched.log`, `name_aliases.json` | `--state-dir` | Progress, single-instance lock, unmatched-pick log, remembered fuzzy matches. |

The state directory defaults to `~/.sleeper_draftboard` (override with `--state-dir` or the `SLEEPER_DRAFTBOARD_STATE_DIR` environment variable).

## How it works

1. Reads your rankings and builds an index of players (layout detected from headers).
2. Polls `https://api.sleeper.app/v1/draft/<id>/picks` every few seconds.
3. Matches each new pick to your list (alias, then exact, then fuzzy within the same position).
4. Redraws the HTML board (and updates the Excel copy), then repeats until the draft completes.

## Troubleshooting

- **"Could not find a player-name column..."**: check your headers against the table above, or pass `--header-row`.
- **A player isn't struck through**: see the *Unmatched picks* panel on the board or the `_unmatched.log`. The player is probably missing from your sheet, or spelled very differently. Kickers/defenses are ignored silently if your sheet doesn't list them.
- **"Could not save ... open in Excel"**: close the `*_LIVE.xlsx` file. Excel locks it on Windows. Use `--no-excel` if you only want the HTML board.
- **"Another instance appears to be tracking this draft"**: a previous run is still going. If it crashed, delete the `.lock` file in the state directory.
- **The board doesn't update**: it reloads every few seconds; make sure the script is still running in its terminal.

## Development

```bash
pip install -r requirements.txt pytest
python -m pytest -q
```

Tests mock the Sleeper API. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap ideas

- Show tier break lines on the board
- CSV / Google Sheets input
- Highlight which picks belong to *your* team

## Disclaimer

This is an unofficial, community project and is not affiliated with or endorsed by Sleeper. It only reads Sleeper's public draft data.

## License

[MIT](LICENSE)
