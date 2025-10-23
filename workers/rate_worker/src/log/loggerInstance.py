from typing import cast

from .logger import Logger

# This file only exists to define the global logger variable

logger: Logger = cast(Logger, None)  # Don't want to initialize the logger without verifying that the log file exists. The 'cast' is a promise that we will assign a Logger later
