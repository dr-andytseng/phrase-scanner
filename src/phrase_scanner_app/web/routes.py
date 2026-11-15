"""
Web routes for the PhraseScanner Flask interface.

Validates requests and delegates scanning to phrase_scanner_app.core.
No scanning logic is duplicated here.
"""

import threading
from datetime import datetime
from urllib.parse import urlparse

from flask import render_template, request, jsonify

from phrase_scanner_app.core import PhraseScanner

# Single local user — one shared stop flag for the in-flight scan.
_scan_stop = threading.Event()

# Clamp limits so a browser request can't kick off an abusive crawl.
MAX_URLS = 20
MAX_PHRASES = 200
MIN_DELAY, MAX_DELAY = 0.2, 10.0
MAX_PAGES_LIMIT = 500
MAX_DEPTH_LIMIT = 8


def validate_input(data):
    """Validate and normalize the /api/scan payload. Returns (urls, phrases, limits, error)."""
    raw_urls = data.get('urls', '')
    raw_phrases = data.get('phrases', '')

    urls = [line.strip() for line in raw_urls.splitlines()
            if line.strip() and not line.strip().startswith('#')]
    phrases = [line.strip().lower() for line in raw_phrases.splitlines()
               if line.strip() and not line.strip().startswith('#')]

    if not urls:
        return None, None, None, 'Please enter at least one URL.'
    if len(urls) > MAX_URLS:
        return None, None, None, f'Too many URLs (max {MAX_URLS}).'
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            return None, None, None, f'Invalid URL: {url} (must start with http:// or https://)'

    if not phrases:
        return None, None, None, 'Please enter at least one phrase.'
    if len(phrases) > MAX_PHRASES:
        return None, None, None, f'Too many phrases (max {MAX_PHRASES}).'

    try:
        delay = float(data.get('delay', 0.5))
        max_pages = int(data.get('max_pages', 100))
        max_depth = int(data.get('max_depth', 3))
    except (TypeError, ValueError):
        return None, None, None, 'Delay, max pages and max depth must be numbers.'

    delay = min(max(delay, MIN_DELAY), MAX_DELAY)
    max_pages = min(max(max_pages, 1), MAX_PAGES_LIMIT)
    max_depth = min(max(max_depth, 0), MAX_DEPTH_LIMIT)

    return urls, phrases, {'delay': delay, 'max_pages': max_pages, 'max_depth': max_depth}, None


def register(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/stop', methods=['POST'])
    def stop_scan():
        _scan_stop.set()
        return jsonify({'stopped': True})

    @app.route('/api/scan', methods=['POST'])
    def scan():
        data = request.get_json(silent=True) or {}
        urls, phrases, limits, error = validate_input(data)
        if error:
            return jsonify({'error': error}), 400

        _scan_stop.clear()
        scanner = PhraseScanner(
            base_urls=urls,
            phrases=phrases,
            delay=limits['delay'],
            max_pages_per_site=limits['max_pages'],
            max_depth=limits['max_depth'],
            stop_event=_scan_stop,
        )
        scanner.scan_all_websites()

        stats = scanner.summary_stats()
        results = scanner.format_results()

        response = {
            'scan_info': {
                'total_websites': stats['total_websites'],
                'stopped_early': scanner.stopped,
                'total_pages_scanned': stats['total_pages_scanned'],
                'successful_scans': stats['successful_scans'],
                'failed_scans': stats['failed_scans'],
                'pages_with_phrases': stats['pages_with_phrases'],
                'phrases_searched': scanner.phrases,
                'max_pages_per_site': scanner.max_pages_per_site,
                'max_depth': scanner.max_depth,
                'delay': scanner.delay,
                'scan_date': datetime.now().isoformat(),
            },
            'top_phrases': sorted(
                [{'phrase': p, 'pages': s['pages'], 'total_occurrences': s['total_occurrences']}
                 for p, s in stats['phrase_stats'].items()],
                key=lambda x: x['total_occurrences'], reverse=True
            )[:10],
            'results': results,
        }
        return jsonify(response)
