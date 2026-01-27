"""Bootstrap data for first run."""

from __future__ import annotations

import logging

from tools.run_ingestion_impl import run_ingestion_impl

from .config import TuiConfig

logger = logging.getLogger(__name__)


def bootstrap_data(config: TuiConfig) -> None:
    if config.mode in {"offline_demo", "local_ingestion", "live"}:
        try:
            from backend import storage as storage_module
            from backend.storage import DatasetRegistry

            registry_path = config.data_root / "_registry.json"
            DatasetRegistry(path=registry_path)

            storage_module.BASE_PARQUET_ROOT = config.data_root
            storage_module.REGISTRY_PATH = registry_path
            try:
                from src.backend import storage as storage_src

                storage_src.BASE_PARQUET_ROOT = config.data_root
                storage_src.REGISTRY_PATH = registry_path
            except Exception:
                pass
            run_ingestion_impl("liquidations_dashboard", once=True)
        except Exception as exc:
            logger.warning({"event": "bootstrap_failed", "error": str(exc)})
