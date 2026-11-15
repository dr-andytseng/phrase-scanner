"""
Optional Flask web interface for PhraseScanner.

This package is only usable when the "web" extra is installed. Importing it
without Flask installed raises a clear error message; the command-line
interface never imports this package.
"""

try:
    from flask import Flask
except ImportError as exc:
    raise ImportError(
        "The PhraseScanner web interface requires Flask, which is not installed.\n"
        "Install it with:  python -m pip install -e \".[web]\"   (or: pip install \"phrase-scanner[web]\")\n"
        "The command-line interface (phrase-scanner) works without it."
    ) from exc


def create_app():
    """Flask application factory. Importing this module never starts a server or a crawl."""
    app = Flask(__name__)

    from phrase_scanner_app.web import routes
    routes.register(app)

    return app
