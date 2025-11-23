"""Entrypoint for running the backend application."""

import os

from dotenv import load_dotenv

from . import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    if os.environ.get("APP_ENV") in ("dev", "test"):
        try:
            from app.db.session import init_local_db

            init_local_db()
        except Exception:
            pass
    app.run(debug=True, port=5001, host="0.0.0.0")
