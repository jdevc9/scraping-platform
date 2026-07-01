import logging
import sys
from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stdout,
    )
    for noisy in ('uvicorn.access', 'sqlalchemy.engine', 'celery.app.trace'):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    return logging.getLogger(name)
