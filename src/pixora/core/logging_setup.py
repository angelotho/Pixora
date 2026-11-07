"""Logs locais rotativos, com remoção de tokens e assinaturas de URLs."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Query strings de URLs de CDN carregam assinaturas temporárias; removemos tudo após "?".
_URL_QUERY = re.compile(r"(https?://[^\s?#\"']+)\?[^\s\"']*")
_SECRETS = re.compile(r"(?i)\b(sessionid|csrftoken|ds_user_id|access_token|password|senha)=([^\s&;\"']+)")


def redact(text: str) -> str:
    text = _URL_QUERY.sub(r"\1?<redacted>", text)
    return _SECRETS.sub(r"\1=<redacted>", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(log_dir: Path, level: int = logging.INFO) -> Path:
    log_file = log_dir / "pixora.log"
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = RedactingFormatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    try:
        handler: logging.Handler = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(fmt)
    root.addHandler(handler)
    # O Instaloader é verboso em DEBUG; mantemos apenas avisos dele e do urllib3.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return log_file
