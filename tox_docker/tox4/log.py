from logging import Logger
from typing import Optional

from tox.report import LOGGER, ToxHandler

_HANDLER = None


def _get_handler() -> ToxHandler:
    global _HANDLER
    if _HANDLER is None:
        logger: Optional[Logger] = LOGGER
        while logger:
            for handler in logger.handlers:
                if isinstance(handler, ToxHandler):
                    _HANDLER = handler
                    logger = None
                    break
            else:
                logger = logger.parent if logger.propagate else None

    assert _HANDLER is not None
    return _HANDLER


def log(line: str) -> None:
    with _get_handler().with_context("docker"):
        LOGGER.warning(line)
