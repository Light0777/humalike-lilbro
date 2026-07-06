import sys
from pathlib import Path

from loguru import logger

__all__ = ["logger", "setup_logging"]


def setup_logging(level: str = "INFO") -> None:
    logger.remove()

    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level:<7}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        colorize=True,
    )

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.add(
        logs_dir / "gaming-ai.log",
        level=level,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {name}:{function}:{line} - {message}",
    )

    logger.info("Logging configured at level={}", level)
