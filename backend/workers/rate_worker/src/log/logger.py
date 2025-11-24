"""Lightweight logger used by the rate_worker CLI."""

import datetime
import os
from enum import Enum
from pathlib import Path
from typing import Any


class LogLevel(Enum):
    """Logging levels supported by the worker."""

    SILENT = 0
    INFO = 1
    DEBUG = 2


class Logger:
    """A logging class that reads config from environment variables.

    - $LOG_FILE: Path to the log file
    - $LOG_LEVEL: Verbosity level (0=silent, 1=info, 2=debug)
    """

    def __init__(self) -> None:
        self.log_file_path: str = os.getenv("LOG_FILE")
        try:
            self.log_level: int = int(os.getenv("LOG_LEVEL", "0"))
        except Exception:
            self.log_level: int = 0

        if self.log_level not in [0, 1, 2]:
            self.log_level: int = 0

        if self.log_file_path:
            try:
                log_dir = Path(self.log_file_path).parent
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                # TODO(rbaker) consider failing hard if we cannot create the log file
                ...

    def _write_log(self, level: LogLevel, message: str, timestamp: str) -> None:
        """Write a log entry at the given level if enabled."""
        if self.log_level < level.value:
            return
        if not self.log_file_path:
            return

        level_name = level.name
        log_entry: str = f"[{timestamp}] {level_name}: {message}\n"

        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            # TODO(rbaker) consider failing hard if logging fails
            ...

    def log_info(self, message: str) -> None:
        """Log an info-level message if enabled."""
        timestamp: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_log(LogLevel.INFO, message, timestamp)

    def log_debug(self, message: str) -> None:
        """Log a debug-level message if enabled."""
        timestamp: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_log(LogLevel.DEBUG, message, timestamp)

    def get_config(self) -> dict[str, Any]:
        """Return the current logger configuration."""
        return {
            "log_file": self.log_file_path,
            "log_level": self.log_level,
            "log_level_name": LogLevel(self.log_level).name,
        }
