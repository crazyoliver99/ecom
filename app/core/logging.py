"""Structured JSON logging.

Every log line is a single JSON object, so logs stay machine-parseable as the
system grows (provider runs, scoring, LLM calls will all log through this).
"""

import json
import logging
import logging.config
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": level, "handlers": ["default"]},
            "loggers": {
                # Route uvicorn's own logs through the same JSON handler.
                "uvicorn": {"level": level, "handlers": ["default"], "propagate": False},
                "uvicorn.error": {"level": level, "handlers": ["default"], "propagate": False},
                "uvicorn.access": {"level": level, "handlers": ["default"], "propagate": False},
            },
        }
    )
