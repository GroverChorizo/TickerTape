"""Implementation for run_ingestion CLI used in tests and CI."""
from __future__ import annotations
from typing import List
from pathlib import Path
from datetime import datetime, timezone
import logging

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from backend.storage import DatasetRegistry
from backend.liquidations_feed import LiquidationsFeed
from backend.snapshotter import run_once

logger = logging.getLogger(__name__)

PROFILE_CADENCES = {
    "liquidations_dashboard": ["10m", "1h", "4h", "24h"],
}


def run_ingestion_impl(profile: str, once: bool = False) -> None:
    if profile not in PROFILE_CADENCES:
        raise ValueError(f"Unknown profile: {profile}")

    from src.backend import storage as storage_module

    registry = DatasetRegistry(path=storage_module.BASE_PARQUET_ROOT / "_registry.json")
    feed = LiquidationsFeed()

    # In future: load buffered events from ingestion layer.

    cadences = PROFILE_CADENCES[profile]
    for tf in cadences:
        path = run_once(feed, registry, tf)
        logger.info({"event": "run_once_written", "timeframe": tf, "path": path})

    # Done
    logger.info({"event": "run_ingestion_complete", "profile": profile})
