"""Entry point so you can run `python -m app`."""

from __future__ import annotations

import os

from . import create_app


def main() -> None:
    """Run the Flask development server."""
    app = create_app()
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    if os.getenv("APP_ENV") in ("dev", "test"):
        try:
            from app.db.session import init_local_db

            init_local_db()
        except Exception:
            pass
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
