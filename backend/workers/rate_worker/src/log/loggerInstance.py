"""Shared logger instance placeholder for the rate_worker."""

from typing import cast

from .logger import Logger

# This file only exists to define the global logger variable

logger: Logger = cast(
    Logger, None
)  # Cast defers initialization until a valid log file is configured.
