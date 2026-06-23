"""
logging_setup.py
================
Structured (JSON-lines) logging. Each log line is a JSON object so runs can be
grepped, shipped to a log store, or parsed for audit. A run id is bound to every
record via a logging filter.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "run_id"):
            payload["run_id"] = record.run_id  # type: ignore[attr-defined]
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id  # type: ignore[attr-defined]
        return True


def setup_logging(run_id: str, level: int = logging.INFO,
                  logfile: Optional[str] = None) -> logging.Logger:
    """Configure the ``data_collection`` logger tree for one run."""
    logger = logging.getLogger("data_collection")
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = JsonFormatter()

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.addFilter(_RunIdFilter(run_id))
    logger.propagate = False
    return logger
