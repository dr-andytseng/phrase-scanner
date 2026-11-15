"""Web interface tests — Flask test client; crawling is stubbed. No network."""

import pytest

from phrase_scanner_app.web import create_app


class FakeScanner:
    instances = []

    def __init__(self, base_urls=None, phrases=None, delay=None,
                 max_pages_per_site=None, max_depth=None, stop_event=None):
        self.base_urls = list(base_urls or [])
        self.phrases = list(phrases or [])
        self.delay = delay
        self.max_pages_per_site = max_pages_per_site
        self.max_depth = max_depth
        self.stopped = False
        FakeScanner.instances.append(self)

    def scan_all_websites(self):
        # Simulate one canned page with one phrase hit — no network.
        self.results = [
            {'url': 'https://example.test' + '/hit', 'found_phrases': ['python'],
             'phrases_counts': {'python': 2}, 'total_phrases_found': 1,
             'scan_timestamp': '2026-01-01T00:00:00', 'depth': 0,
             'status_code': 200, 'error': ''},
        ]

    def summary_stats(self):
        return {'total_websites': len(self.base_urls), 'total_pages_scanned': 1,
                'successful_scans': 1, 'failed_scans': 0, 'pages_with_phrases': 1,
                'phrase_stats': {'python': {'pages': 1, 'total_occurrences': 2}}}

    def format_results(self):
        return [{'URL': 'https://example.test/hit', 'Phrases Found': 1,
                 'Phrase List': 'python', 'Phrase Counts': 'python:2',
                 'Scan Time': '2026-01-01T00:00:00', 'Depth': 0, 'Status Code': 200,
                 'Error': ''}]


@pytest.fixture()
def client(monkeypatch):
    FakeScanner.instances = []
    monkeypatch.setattr('phrase_scanner_app.web.routes.PhraseScanner', FakeScanner)
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


def test_index_serves_ui(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'PhraseScanner' in resp.data


def test_static_assets_served(client):
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/style.css').status_code == 200


def test_scan_rejects_invalid_input(client):
    resp = client.post('/api/scan', json={'urls': 'not-a-url', 'phrases': 'python'})
    assert resp.status_code == 400
    assert b'error' in resp.data


def test_scan_rejects_empty_input(client):
    resp = client.post('/api/scan', json={'urls': '', 'phrases': ''})
    assert resp.status_code == 400


def test_scan_clamps_limits_and_returns_results(client):
    resp = client.post('/api/scan', json={
        'urls': 'https://example.test\n',
        'phrases': 'Python',
        'delay': 99, 'max_pages': 99999, 'max_depth': 99,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['scan_info']['max_pages_per_site'] == 500
    assert data['scan_info']['max_depth'] == 8
    assert data['scan_info']['delay'] <= 10
    assert data['scan_info']['total_pages_scanned'] == 1
    assert data['results'][0]['Phrase Counts'] == 'python:2'
    assert FakeScanner.instances[0].phrases == ['python']


def test_stop_endpoint(client):
    resp = client.post('/api/stop')
    assert resp.status_code == 200
    assert resp.get_json() == {'stopped': True}
