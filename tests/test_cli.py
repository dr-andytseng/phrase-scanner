"""CLI tests — no network access; the scan itself is stubbed."""

import json
import os
import sys

import pytest

from phrase_scanner_app import cli


class FakeScanner:
    """Minimal stand-in for PhraseScanner: records construction, canned scan."""

    instances = []

    def __init__(self, urls_file=None, phrases_file=None, delay=None,
                 max_pages_per_site=None, max_depth=None, **kwargs):
        self.urls_file = urls_file
        self.phrases_file = phrases_file
        self.delay = delay
        self.max_pages_per_site = max_pages_per_site
        self.max_depth = max_depth
        self.base_urls = ['https://example.test']
        self.phrases = ['python']
        self.results = [
            {'url': 'https://example.test', 'found_phrases': ['python'],
             'phrases_counts': {'python': 1}, 'total_phrases_found': 1,
             'scan_timestamp': '2026-01-01T00:00:00', 'depth': 0,
             'status_code': 200, 'error': ''},
        ]
        FakeScanner.instances.append(self)

    def scan_all_websites(self):
        pass

    def format_results(self):
        return [
            {'URL': 'https://example.test', 'Phrases Found': 1, 'Phrase List': 'python',
             'Phrase Counts': 'python:1', 'Scan Time': '2026-01-01T00:00:00',
             'Depth': 0, 'Status Code': 200, 'Error': ''},
        ]

    def summary_stats(self):
        return {'total_websites': 1, 'total_pages_scanned': 1, 'successful_scans': 1,
                'failed_scans': 0, 'pages_with_phrases': 1,
                'phrase_stats': {'python': {'pages': 1, 'total_occurrences': 1}}}


def test_create_sample_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.create_sample_files()
    assert (tmp_path / 'urls.txt').exists()
    assert (tmp_path / 'phrases.txt').exists()
    assert 'python' in (tmp_path / 'phrases.txt').read_text()


def test_main_creates_outputs_without_network(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['phrase-scanner'])
    monkeypatch.setattr(cli, 'PhraseScanner', FakeScanner)
    cli.main()

    csv_out = (tmp_path / 'phrasescanner_results_CSV.csv').read_text()
    json_out = json.loads((tmp_path / 'phrasescanner_results_JSON.json').read_text())

    assert 'https://example.test' in csv_out
    assert json_out['scan_info']['total_pages_scanned'] == 1
    assert json_out['results'][0]['Phrase Counts'] == 'python:1'
    assert FakeScanner.instances, 'scanner was never constructed'


def test_help_exits_without_scanning(tmp_path, monkeypatch, capsys):
    FakeScanner.instances = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['phrase-scanner', '--help'])
    monkeypatch.setattr(cli, 'PhraseScanner', FakeScanner)
    cli.main()
    assert 'Usage' in capsys.readouterr().out
    assert FakeScanner.instances == [], 'help must not construct the scanner'
    assert not (tmp_path / 'phrasescanner_results_CSV.csv').exists()
