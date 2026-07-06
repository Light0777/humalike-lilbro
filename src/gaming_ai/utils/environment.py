from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


def load_environment(env_file: str = ".env") -> None:
    env_path = Path(env_file)

    if not env_path.exists():
        logger.warning(
            "{} not found. Copy .env.example to .env and fill in your values.",
            env_path.name,
        )
        return

    load_dotenv(env_path)
    logger.info("Loaded environment from {}", env_path.resolve())
