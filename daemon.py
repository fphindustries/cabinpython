#!/usr/bin/env python3
"""
CabinPython v2 Daemon Entry Point

This is the main entry point for the CabinPython v2 daemon service.
It handles command-line arguments, configuration loading, logging setup,
and daemon lifecycle.

Usage:
    python daemon.py --config config.yaml [--log-level INFO]

For systemd service:
    See systemd/cabinpi-daemon.service
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from cabinpi.daemon import SensorDaemon


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from some libraries
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("pymodbus").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {log_level}")


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config is invalid YAML
    """
    import yaml
    from dotenv import load_dotenv
    import os

    # Load environment variables from .env file
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment from {env_path}")

    # Load YAML configuration
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Substitute environment variables in config
    config = _substitute_env_vars(config)

    logging.info(f"Loaded configuration from {config_path}")
    return config


def _substitute_env_vars(obj):
    """
    Recursively substitute environment variables in config.

    Replaces ${VAR_NAME} with the value of environment variable VAR_NAME.

    Args:
        obj: Configuration object (dict, list, str, etc.)

    Returns:
        Configuration with environment variables substituted
    """
    import os
    import re

    if isinstance(obj, dict):
        return {key: _substitute_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Replace ${VAR_NAME} with environment variable value
        pattern = re.compile(r'\$\{([^}]+)\}')
        matches = pattern.findall(obj)
        for var_name in matches:
            var_value = os.environ.get(var_name, "")
            if not var_value:
                logging.warning(f"Environment variable '{var_name}' not set")
            obj = obj.replace(f"${{{var_name}}}", var_value)
        return obj
    else:
        return obj


async def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CabinPython v2 - Modular Monitoring Daemon"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = load_config(args.config)

        # Override log level from config if present
        config_log_level = config.get("daemon", {}).get("log_level")
        if config_log_level and config_log_level != args.log_level:
            setup_logging(config_log_level)

        # Create and initialize daemon
        daemon = SensorDaemon(config)
        await daemon.initialize()

        # Run daemon (blocks until shutdown)
        await daemon.run()

        logger.info("Daemon exited successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
