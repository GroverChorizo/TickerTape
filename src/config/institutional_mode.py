"""
Institutional Mode configuration for backend quant engine.
Enforces local-only, no network, no synthetic/modified data, no financial advice/live trading defaults.
"""

import logging
import yaml
import os

logger = logging.getLogger("institutional_mode")


class InstitutionalModeConfig:
    """
    Configuration and enforcement for Institutional Mode.
    Reads from YAML config or environment variable.
    """

    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "institutional_mode.yaml")
    ENV_VAR = "INSTITUTIONAL_MODE"

    enabled: bool = True

    @classmethod
    def load(cls) -> None:
        """
        Load config from YAML or environment variable. Defaults to enabled.
        """
        # Check environment variable first
        env = os.getenv(cls.ENV_VAR)
        if env is not None:
            cls.enabled = env.lower() in ("1", "true", "yes", "on")
            logger.info(f"Institutional Mode set from env: {cls.enabled}")
            return
        # Fallback to YAML config
        if os.path.exists(cls.CONFIG_PATH):
            try:
                with open(cls.CONFIG_PATH, "r") as f:
                    data = yaml.safe_load(f)
                cls.enabled = bool(data.get("enabled", True))
                logger.info(f"Institutional Mode loaded from YAML: {cls.enabled}")
            except Exception as e:
                logger.error(f"Failed to load institutional_mode.yaml: {e}")
                cls.enabled = True
        else:
            logger.info("No config found; Institutional Mode enabled by default.")
            cls.enabled = True

    @classmethod
    def enforce(cls) -> None:
        """
        Enforce institutional constraints at runtime. Raises if not enabled.
        """
        if not cls.enabled:
            raise RuntimeError("Institutional Mode is required but not enabled.")


# Auto-load config on import
InstitutionalModeConfig.load()
