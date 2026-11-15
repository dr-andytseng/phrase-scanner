# Testing

Testing is split into automated tests (mocked network; no external crawls) and
user-reported manual checks. Manual checks are not re-verified automatically
and should not be treated as independent confirmation.

## Automated tests

`tests/test_core.py`, `tests/test_cli.py`, `tests/test_web.py` — run with:

    python -m pytest

Current status: **19 passed**, verified in:

- Python 3.15.2 (Homebrew) — editable install `pip install -e ".[web,dev]"`
- Python 3.9.6 (macOS command line tools) — regular install `pip install ".[web]" pytest`
  (the 3.9 pip cannot install in editable mode; upgrade pip with
  `python -m pip install --upgrade pip` first if you want editable on 3.9)

Coverage includes: URL normalization and validation, `/robots.txt` handling
(blocked pages are reported), text extraction, phrase counting, result
formatting and summary statistics, BFS crawl order, the stop/cancel path,
CLI smoke tests (`--help`, `main()` with a stubbed scanner, output-file
generation), and web routes via Flask's test client (`GET /`, static assets,
input validation, stubbed scan, `/api/stop`).

Crawling is mocked throughout; no live network access is used by the suite.

## Manual checks (user-reported; not independently re-verified)

- Both CLI help commands (`phrase-scanner --help`, `python phrase_scanner.py --help`)
- A quick scan through the web interface

The manual web scan created no additional repository artifacts: the web
interface writes results only to the browser's download mechanism; the
repository working tree contains only the committed-source changes listed in
`git status` (i.e. cleanup artifacts such as `.venv/`, `__pycache__/`,
`*.egg-info/`, `.pytest_cache/` remain ignored and untracked).

No verification of the manual scan's results (counts, matching decisions,
ordering) has been performed by the author. When manually testing changes,
record: input URLs/phrases, limits used, and the expected vs observed
behavior.
