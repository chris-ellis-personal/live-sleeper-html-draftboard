# Contributing

Issues and pull requests are welcome.

```bash
git clone https://github.com/chris-ellis-personal/live-sleeper-html-draftboard.git
cd live-sleeper-html-draftboard
pip install -r requirements.txt pytest
python -m pytest -q
```

- Tests never hit the real Sleeper API; it is mocked (see `tests/`).
- Please don't commit personal rankings files. `.gitignore` excludes `*.xlsx` except the sample.
- If you change the spreadsheet layout rules, update the "Rankings spreadsheet format" section of the README and add a test.
