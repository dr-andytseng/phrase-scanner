# PhraseScanner

A Python tool that crawls websites and scans every accessible page for a custom list of keywords or phrases, then reports where and how often each one appears.

Useful for content audits, SEO tracking, compliance checks, competitive research, or finding where specific terms or phrases live across a site.

The project provides two equally supported interfaces, both built on the same shared scanning engine (`phrase_scanner_app.core`):

1. **Command-line interface (CLI)** — installed by default; see [Command line](#command-line).
2. **Optional Flask web interface** — a local web UI; see [Web interface](#web-interface). The CLI works fully without it.

## Features

- Crawls multiple websites from a simple text file of URLs
- Searches for any number of keywords or multi-word phrases, defined in a text file — whole-word matching
- Respects robots.txt (pages blocked by robots.txt are reported, not silently skipped)
- Detects and handles both HTML and XML/sitemap content
- Configurable crawl depth and max pages per site
- Skips binary files (PDFs, images, archives) and sensitive paths (/admin, /login, etc.)
- Exports results to both CSV and JSON
- Prints a live progress log and a summary report with top matches
- Web interface: minimalist Apple-style UI, Found/Scanned result tables, sortable columns, per-phrase counts, client-side CSV/JSON downloads, and a Stop button (partial results kept)
- Deterministic (sorted) link crawl order — reproducible runs

## Requirements

- Python 3.9+ (tested on 3.9; there is no guarantee of compatibility with unverified versions)
- Dependencies are managed in `pyproject.toml`. Base dependencies (CLI only): requests, beautifulsoup4, lxml. The web interface additionally needs Flask (`.[web]` extra).
- `requirements.txt` is kept as a compatibility entry point (`-e .`) — it installs the CLI and its dependencies, nothing more.

## Setup

1. Clone this repository:
```
   git clone https://github.com/dr-andytseng/phrase-scanner.git
   cd phrase-scanner
```

2. Install — pick one depending on what you want:

CLI only:
```
   python -m pip install -e .
```

CLI plus the optional web interface:
```
   python -m pip install -e ".[web]"
```

(Or, equivalent to the CLI-only install: `pip install -r requirements.txt`, which runs `-e .`.)

3. (CLI only) Run the CLI once to auto-generate sample input files:
```
   phrase-scanner
```
   This creates urls.txt and phrases.txt if they don't already exist. Note: `phrase-scanner` runs the scanner against whatever is in urls.txt — point it at sites you may crawl (see Legal & Ethical Use).

## Command line

### 1. Configure your target URLs

Edit urls.txt — one URL per line, lines starting with # are ignored.

Note: Each URL is a starting point, not a single page. The script crawls outward from it, following internal links within the same domain, up to MAX_CRAWL_DEPTH link-hops and MAX_PAGES_PER_SITE pages. It will never cross onto external domains, even if it encounters outbound links to them.

Example urls.txt:
```
https://example.com
https://blog.example.com
```

### 2. Configure your phrases

Edit phrases.txt — one term per line, single words or multi-word phrases both work. Matching is case-insensitive and whole-word (phrases embedded inside a larger word, e.g. "biology" inside "neurobiology", do not match).

Example phrases.txt:
```
privacy policy
data breach
subscription
free trial
```

### 3. Run the scanner

```
   phrase-scanner
```

Alternatively, without installing:
```
   python phrase_scanner.py
```

The root-level `phrase_scanner.py` is a compatibility launcher that delegates to the packaged CLI. **It requires the project to be installed first** (`python -m pip install -e .` or `python -m pip install -e ".[web]"`); it is not a standalone script and does not duplicate scanner logic.

The scanner will crawl each site, log progress in the terminal, and save results to:
- phrasescanner_results_CSV.csv
- phrasescanner_results_JSON.json

Input files (urls.txt, phrases.txt) are read from the current working directory, and result files are written to the current working directory.

## Web interface

The web interface is a local, single-user Flask UI around the same shared scanning engine. The CLI does not depend on it, and the web interface does not modify the CLI.

Install (if you haven't already):
```
   python -m pip install -e ".[web]"
```

Run the development server from the repository root:
```
   python -m flask --app phrase_scanner_app.web:create_app run
```

Then open http://127.0.0.1:5000 (Flask's default). The server binds to localhost by default; it is for **local development use only** and has no authentication — do not expose it to a network.

Features: paste URLs and phrases (with optional crawl limits), a Stop button that keeps partial results, a results view split into **Found** (pages where ≥1 phrase matched) and **Scanned** (pages scanned with no matches, including pages that failed or were blocked by robots.txt), sortable columns, per-phrase counts, per-table filtering, CSV/JSON downloads (client-side), and an elapsed-time indicator during scans.

Scans run synchronously — large or deep crawls can take many minutes and may time out the browser request. Use the CLI for very large jobs.

## Project layout

```
phrase-scanner/
├── README.md
├── LICENSE
├── pyproject.toml          # package metadata; source of truth for dependencies
├── requirements.txt        # compatibility entry point: "-e ." (CLI install)
├── phrase_scanner.py       # root compatibility launcher → phrase_scanner_app.cli:main
├── src/
│   └── phrase_scanner_app/
│       ├── __init__.py
│       ├── core.py         # shared crawling, matching, results, cancellation — no Flask / CLI
│       ├── cli.py          # CLI: prompts, terminal output, orchestration of core
│       └── web/            # optional Flask interface
│           ├── __init__.py # create_app() factory (importing does not start anything)
│           ├── routes.py   # routes + request validation; calls core
│           ├── templates/index.html
│           └── static/{app.js,style.css}
└── tests/
    ├── test_core.py
    ├── test_cli.py
    └── test_web.py
```

## Usage Examples

Example 1 — Compliance check across a company's site
urls.txt: your company domain. phrases.txt: gdpr, ccpa, cookie consent, data retention. Run the scanner to find which pages mention (or fail to mention) key compliance phrases.

Example 2 — Competitor content audit
urls.txt: a competitor's blog and docs site. phrases.txt: your product category terms, e.g. api, integration, pricing. See how often and where they discuss topics relevant to your market.

Example 3 — Marketing claim audit
urls.txt: your own marketing site. phrases.txt: free trial, no credit card, cancel anytime. Confirm these phrases still appear where you expect them to, after a site redesign.

## Configuration Options

Inside main() (src/phrase_scanner_app/cli.py), you can adjust:

- DELAY_BETWEEN_REQUESTS — seconds to wait between page fetches. Default: 0.5
- MAX_PAGES_PER_SITE — max pages crawled per site before stopping. Default: 5000
- MAX_CRAWL_DEPTH — max link-hops from the starting URL. Default: 5

These three settings control both how thorough the scan is and how long it takes. A full run against a large site with the defaults can take a long time — for example, 5000 pages at a 0.5s delay is at least ~42 minutes of delay alone, before network latency per request.

Note: maximum crawl depth is not a coverage guarantee. Deep pages are only reached if the crawl fits within MAX_PAGES_PER_SITE pages; to guarantee a specific page is scanned, list it directly in urls.txt (it is then scanned at depth 0).

### Tuning for speed vs. thoroughness

If you want a faster, lighter scan (e.g. checking a small marketing site, or doing a quick spot-check):
```
DELAY_BETWEEN_REQUESTS = 0.2
MAX_PAGES_PER_SITE = 100
MAX_CRAWL_DEPTH = 3
```
This is a good default for scanning a single landing page, blog, or small docs site where you don't need to crawl the entire domain.

If you want a deep, exhaustive scan (e.g. a full compliance audit of a large site):
```
DELAY_BETWEEN_REQUESTS = 1.0
MAX_PAGES_PER_SITE = 10000
MAX_CRAWL_DEPTH = 8
```
Expect this to take considerably longer — run it in the background or overnight for large domains.

General guidance: lower MAX_CRAWL_DEPTH first if you just want to check top-level and near-top-level pages, since depth has an exponential effect on pages discovered. Lower MAX_PAGES_PER_SITE as a hard ceiling/safety net regardless of depth, especially on sites you don't control. Only lower DELAY_BETWEEN_REQUESTS if you're scanning a site you own or have permission to hit harder, since reducing delay increases server load per unit time.

## Development

Install development tools (web interface + test/build tooling):
```
   python -m pip install -e ".[web,dev]"
```

Run tests (network access is mocked; no live crawling is performed):
```
   python -m pytest
```

Verify packaging (wheel builds with templates/static included):
```
   python -m build
```

## Output Format

Both CSV and JSON outputs include, per page: URL, number of phrases found, list of matched phrases, per-phrase occurrence counts, scan timestamp, crawl depth, HTTP status code, and an error message if the fetch failed. The web interface's downloads contain the same data, additionally split into Found/Scanned sections (CSV gains a Section column; JSON gains found_results/scanned_results).

## Notes & Limitations

- This is a same-domain crawler — it won't follow external links.
- Respects robots.txt by default; it will skip disallowed pages (and report them as such). A /robots.txt that returns 403 or 401 disallows everything, per the robots.txt specification.
- Crawling follows internal links in sorted order; runs are deterministic but coverage still depends on the page cap.
- The scanner sees only server-delivered HTML; JavaScript-injected content is not searched.
- Large sites with high MAX_PAGES_PER_SITE values can take a long time to run — adjust DELAY_BETWEEN_REQUESTS and depth/page limits accordingly.
- Phrase matching is whole-word and case-insensitive; substrings inside larger words do not match.

## Differences from the original single-file script

- The CLI behaves the same (same flags in `main()`, same sample file generation, same output files, same terminal output), but the implementation now lives in the installable `phrase_scanner_app` package; the root `phrase_scanner.py` is a thin compatibility launcher that requires installation.
- The web interface is new and additive.
- Scan correctness fixes: text extraction no longer glues words across tags and normalizes all whitespace (including &nbsp;); the summary counter no longer counts every page as failed; robots.txt-blocked pages are reported rather than silently dropped; link crawl order is deterministic.
- Matching remains whole-word; the original advertised this but could miss multi-word phrases separated by non-breaking spaces, which is fixed.

## Legal & Ethical Use

This tool is intended for scanning websites you own or have explicit permission to crawl. Before scanning any third-party site, review its Terms of Service and robots.txt, since some sites explicitly prohibit automated crawling regardless of what robots.txt allows. Aggressive crawl settings (high MAX_PAGES_PER_SITE, low DELAY_BETWEEN_REQUESTS) can place meaningful load on a target server — use conservative settings on any site you don't control. You are responsible for how you use this tool and for complying with applicable laws and site policies in your jurisdiction.

## License

MIT — see LICENSE for details.
