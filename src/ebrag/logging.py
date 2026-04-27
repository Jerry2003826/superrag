from __future__ import annotations

import logging as std_logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    normalized_level = level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": normalized_level,
            },
        }
    )


def get_logger(name: str) -> std_logging.Logger:
    return std_logging.getLogger(name)
