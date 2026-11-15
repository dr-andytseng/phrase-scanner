#!/usr/bin/env python3
"""
Compatibility launcher for the packaged CLI.

Run with:  python phrase_scanner.py --help

Requires the project to be installed first, e.g.:
    python -m pip install -e .
"""

from phrase_scanner_app.cli import main

if __name__ == "__main__":
    main()
