#!/usr/bin/env python3
"""
Command-line interface for PhraseScanner.

Orchestrates the shared scanner in phrase_scanner_app.core and handles
terminal output and result files. No web code is imported here.
"""

import csv
import json
import os
import sys
from datetime import datetime

from phrase_scanner_app.core import PhraseScanner

USAGE = """\
PhraseScanner — crawl websites and report where your phrases appear.

Usage:
  phrase-scanner          Run the scan using urls.txt and phrases.txt in the
                          current directory (created with samples on first run).
  phrase-scanner --help   Show this help without scanning.

Inputs (current directory):
  urls.txt                One URL per line; lines starting with # are ignored.
  phrases.txt             One phrase per line; lines starting with # are ignored.
                          Matching is case-insensitive and whole-word.

Outputs (current directory):
  phrasescanner_results_CSV.csv
  phrasescanner_results_JSON.json

Optional web interface:  python -m flask --app phrase_scanner_app.web:create_app run
(Requires: python -m pip install -e ".[web]")
"""


def save_to_csv(scanner, filename='phrasescanner_results_CSV.csv'):
    """Save results to CSV file with new column format."""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['URL', 'Phrases Found', 'Phrase List', 'Phrase Counts', 'Scan Time', 'Depth', 'Status Code', 'Error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for csv_result in scanner.format_results():
            writer.writerow(csv_result)

    print(f"📊 Results saved to: {filename}")


def save_to_json(scanner, filename='phrasescanner_results_JSON.json'):
    """Save results to JSON file with new format."""
    output_data = {
        'scan_info': {
            'total_websites': len(scanner.base_urls),
            'total_pages_scanned': len(scanner.results),
            'phrases_searched': scanner.phrases,
            'max_pages_per_site': scanner.max_pages_per_site,
            'max_depth': scanner.max_depth,
            'scan_date': datetime.now().isoformat()
        },
        'results': scanner.format_results()
    }

    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)

    print(f"📋 Results saved to: {filename}")


def print_summary(scanner):
    """Print a detailed summary of the scan results."""
    stats = scanner.summary_stats()
    pages_with_phrases = [r for r in scanner.results if not r.get('error') and r['total_phrases_found'] > 0]
    phrase_stats = stats['phrase_stats']

    print("\n" + "=" * 80)
    print("📈 ENHANCED SCAN SUMMARY")
    print("=" * 80)
    print(f"🌐 Total websites: {stats['total_websites']}")
    print(f"📄 Total pages scanned: {stats['total_pages_scanned']}")
    print(f"✅ Successful scans: {stats['successful_scans']}")
    print(f"❌ Failed scans: {stats['failed_scans']}")
    print(f"🎯 Pages with Phrases: {stats['pages_with_phrases']}")

    if phrase_stats:
        print(f"\n🔍 Top phrases found:")
        sorted_phrases = sorted(phrase_stats.items(),
                               key=lambda x: x[1]['total_occurrences'],
                               reverse=True)[:10]

        for phrase, phrase_stats_entry in sorted_phrases:
            print(f"  • '{phrase}': {phrase_stats_entry['total_occurrences']} occurrences across {phrase_stats_entry['pages']} pages")

    if pages_with_phrases:
        print(f"\n📋 Sample pages with phrases:")
        for result in pages_with_phrases[:10]:  # Show first 10
            phrases_found = ', '.join(result['found_phrases'][:5])  # Show first 5 phrases
            if len(result['found_phrases']) > 5:
                phrases_found += '...'
            print(f"  • {result['url']}: {phrases_found}")

        if len(pages_with_phrases) > 10:
            print(f"  ... and {len(pages_with_phrases) - 10} more pages")


def create_sample_files():
    """Create sample input files if they don't exist."""

    # Create sample URLs file
    if not os.path.exists('urls.txt'):
        sample_urls = [
            "# These are example websites to scan, please edit urls.txt with your chosen websites.",
            "https://www.python.org",
            "https://realpython.com",
            "https://docs.python.org/3/"
        ]

        with open('urls.txt', 'w') as f:
            f.write('\n'.join(sample_urls))
        print("📝 Created sample urls.txt file")

    # Create sample phrases file
    if not os.path.exists('phrases.txt'):
        sample_phrases = [
            "# These are example phrases, please edit phrases.txt with your own phrases.",
            "python",
            "programming",
            "development",
            "tutorial",
            "documentation",
            "machine learning",
            "data science",
            "artificial intelligence"
        ]

        with open('phrases.txt', 'w') as f:
            f.write('\n'.join(sample_phrases))
        print("📝 Created sample phrases.txt file")


def main():
    """Main function to run the enhanced scanner."""
    if '--help' in sys.argv or '-h' in sys.argv:
        print(USAGE)
        return

    print("🔍 PhraseScanner")
    print("=" * 50)

    # Create sample files if they don't exist
    create_sample_files()

    # Configuration
    DELAY_BETWEEN_REQUESTS = 0.5  # seconds
    MAX_PAGES_PER_SITE = 5000    # Limit to prevent infinite crawling
    MAX_CRAWL_DEPTH = 5        # How deep to go from the starting URL

    try:
        # Create scanner instance
        scanner = PhraseScanner(
            urls_file='urls.txt',
            phrases_file='phrases.txt',
            delay=DELAY_BETWEEN_REQUESTS,
            max_pages_per_site=MAX_PAGES_PER_SITE,
            max_depth=MAX_CRAWL_DEPTH
        )

        # Debug: Print actual configuration being used
        print(f"🔧 Debug - Config Values: MAX_PAGES_PER_SITE={MAX_PAGES_PER_SITE}, MAX_CRAWL_DEPTH={MAX_CRAWL_DEPTH}")
        print(f"🔧 Debug - Scanner Values: max_pages_per_site={scanner.max_pages_per_site}, max_depth={scanner.max_depth}")

        # Run the enhanced scan
        scanner.scan_all_websites()

        # Save results
        save_to_csv(scanner, 'phrasescanner_results_CSV.csv')
        save_to_json(scanner, 'phrasescanner_results_JSON.json')

        # Print summary
        print_summary(scanner)

    except KeyboardInterrupt:
        print("\n⏹️  Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
