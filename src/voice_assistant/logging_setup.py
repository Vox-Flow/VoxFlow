"""Basit, ham ses veya kişisel içerik sızdırmayan logger yapılandırması."""

from __future__ import annotations

import logging
import os


def setup_logging(level: str | None = None) -> logging.Logger:
    lvl = (level or os.environ.get("VOXFLOW_LOG_LEVEL") or "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("voxflow")
