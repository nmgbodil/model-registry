"""Entrypoint to run the development server."""

from __future__ import annotations

from . import create_app
from .config import get_settings

app = create_app()
_cfg = get_settings()

if __name__ == "__main__":
    app.run(host=_cfg.HOST, port=_cfg.PORT, debug=_cfg.DEBUG)
