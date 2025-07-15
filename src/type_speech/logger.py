import sys
from loguru import logger
from type_speech.config import config

logger.remove()

console_level = config.app.console_log_level.upper()
file_level = config.app.file_log_level.upper()

# Use sys.stdout as fallback if stderr is None
console_output = sys.stderr if sys.stderr is not None else sys.stdout
if console_output is not None:
    logger.add(
        console_output,
        level=console_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

logger.add(
    "logs/type_speech.log",
    level=file_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="1 day",
    retention="7 days",
    compression="zip",
)

__all__ = ["logger"]
