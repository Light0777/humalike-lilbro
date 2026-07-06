import asyncio
import sys

from loguru import logger

from gaming_ai.bot import BotRunner
from gaming_ai.config import Settings
from gaming_ai.utils import load_environment, setup_logging


def main() -> None:
    load_environment()

    settings = Settings()
    setup_logging(settings.log_level)

    logger.info("Gaming AI v{} starting...", __import__("gaming_ai").__version__)

    if not settings.discord_token:
        logger.error("DISCORD_TOKEN is not set. Set it in .env to proceed.")
        sys.exit(1)

    runner = BotRunner(settings)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
