"""Shared-core tests. Network access is never used — fetching is mocked/faked."""

import threading

import pytest

from phrase_scanner_app.core import PhraseScanner


def make_scanner(**overrides):
    kwargs = dict(base_urls=['https://example.test'], phrases=['hello world', 'python'],
                  delay=0, max_pages_per_site=10, max_depth=2)
    kwargs.update(overrides)
    return PhraseScanner(**kwargs)


def test_normalize_url_strips_fragment():
    s = make_scanner()
    assert s.normalize_url('https://example.test/a/b?x=1#section') == 'https://example.test/a/b?x=1'


def test_is_valid_url_same_domain_and_scheme():
    s = make_scanner()
    assert s.is_valid_url('https://example.test/page', 'example.test', 'https')
    assert not s.is_valid_url('https://other.test/page', 'example.test', 'https')
    assert not s.is_valid_url('http://example.test/page', 'example.test', 'https')


def test_is_valid_url_skips_binary_extensions_and_sensitive_paths():
    s = make_scanner()
    assert not s.is_valid_url('https://example.test/file.pdf', 'example.test', 'https')
    assert not s.is_valid_url('https://example.test/admin/dashboard', 'example.test', 'https')
    assert not s.is_valid_url('https://example.test/login', 'example.test', 'https')
    assert not s.is_valid_url('https://example.test/api/users', 'example.test', 'https')


def test_extract_text_handles_nbsp_and_glued_words():
    s = make_scanner()
    text = s.extract_text('<html><body><h1>Hello&nbsp;World</h1><p>test</p></body></html>', 'html')
    assert 'hello world' in text


def test_search_phrases_word_boundaries():
    s = PhraseScanner(base_urls=['https://example.test'], phrases=['biology'],
                      delay=0, max_pages_per_site=1, max_depth=0)
    text = 'biology neurobiology biology’s'  # possessive match, embedded word no match
    result = s.search_phrases(text, 'https://example.test/', 0, 200)
    assert result['phrases_counts']['biology'] == 2


def test_format_results_and_summary_stats():
    s = make_scanner()
    s.results = [
        {'url': 'https://example.test/a', 'found_phrases': ['python'], 'phrases_counts': {'python': 3},
         'total_phrases_found': 1, 'scan_timestamp': 't', 'depth': 0, 'status_code': 200, 'error': ''},
        {'url': 'https://example.test/b', 'found_phrases': [], 'phrases_counts': {},
         'total_phrases_found': 0, 'scan_timestamp': 't', 'depth': 1, 'status_code': '', 'error': 'timeout'},
    ]
    formatted = s.format_results()
    assert formatted[0]['URL'] == 'https://example.test/a'
    assert formatted[0]['Phrase Counts'] == 'python:3'
    assert formatted[1]['Error'] == 'timeout'

    stats = s.summary_stats()
    assert stats['total_pages_scanned'] == 2
    assert stats['successful_scans'] == 1
    assert stats['failed_scans'] == 1
    assert stats['pages_with_phrases'] == 1
    assert stats['phrase_stats']['python'] == {'pages': 1, 'total_occurrences': 3}


def test_crawl_website_bfs_and_deterministic_order(monkeypatch):
    s = make_scanner(max_pages_per_site=10, max_depth=2)
    pages = {
        'https://example.test/': ('<a href="/b">b</a><a href="/a">a</a>', 200),
        'https://example.test/a': ('nothing here', 200),
        'https://example.test/b': ('nothing here', 200),
    }
    monkeypatch.setattr(s, 'fetch_webpage', lambda url: (True, pages[url][0], None, 'html', 200))
    monkeypatch.setattr(s, 'can_fetch', lambda url: True)
    results = s.crawl_website('https://example.test/')
    assert [r['url'] for r in results] == [
        'https://example.test/', 'https://example.test/a', 'https://example.test/b']


def test_crawl_website_records_robots_blocked_pages(monkeypatch):
    s = make_scanner(max_pages_per_site=10, max_depth=1)
    monkeypatch.setattr(s, 'can_fetch', lambda url: False)
    fetched = []
    monkeypatch.setattr(s, 'fetch_webpage', lambda url: fetched.append(url))
    results = s.crawl_website('https://example.test/')
    assert fetched == []
    assert len(results) == 1
    assert results[0]['error'] == 'Blocked by robots.txt'


def test_stop_event_halts_crawl_early(monkeypatch):
    s = make_scanner(max_pages_per_site=10, max_depth=3)
    stop = threading.Event()
    s.stop_event = stop

    def fake_fetch(url):
        if url == 'https://example.test/':
            return True, '<a href="/p1">1</a><a href="/p2">2</a>', None, 'html', 200
        if url == 'https://example.test/p1':
            stop.set()  # request stop while the first page is being scanned
            return True, 'nothing', None, 'html', 200
        return True, 'nothing', None, 'html', 200

    monkeypatch.setattr(s, 'fetch_webpage', fake_fetch)
    monkeypatch.setattr(s, 'can_fetch', lambda url: True)
    results = s.crawl_website('https://example.test/')
    assert s.stopped is True
    # /p2 must not be fetched once a stop was requested
    assert [r['url'] for r in results] == ['https://example.test/', 'https://example.test/p1']


def test_summary_stats_from_real_result_shape():
    s = make_scanner()
    s.results = [
        {'url': 'https://example.test/only', 'found_phrases': [], 'phrases_counts': {},
         'total_phrases_found': 0, 'scan_timestamp': 't', 'depth': 0, 'status_code': '',
         'error': 'Blocked by robots.txt'},
    ]
    stats = s.summary_stats()
    assert stats['failed_scans'] == 1
    assert stats['successful_scans'] == 0
