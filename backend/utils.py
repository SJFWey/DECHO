import logging
import os
import sys
from typing import Any, Dict

import yaml
from rich.logging import RichHandler

from backend.exceptions import ConfigError

# Constants
_3_1_SPLIT_BY_NLP = "output/log/split_by_nlp.txt"


def setup_logging() -> None:
    """
    Configures the logging system.
    Logs are output to the console (using Rich) and to a file in output/log/.
    """
    log_dir = "output/log"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "hearing.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RichHandler(rich_tracebacks=True),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def load_config() -> Dict[str, Any]:
    """
    Loads and validates the configuration from config.yaml.

    Returns:
        Dict[str, Any]: The configuration dictionary.

    Raises:
        ConfigError: If the configuration file is missing or invalid.
    """
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Basic validation
        if "asr" not in config or "app" not in config:
            raise ConfigError("Invalid config: missing 'asr' or 'app' sections")

        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing config file: {e}")


def save_config(config: Dict[str, Any]) -> None:
    """
    Saves the configuration to config.yaml.

    Args:
        config (Dict[str, Any]): The configuration dictionary to save.
    """
    config_path = "config.yaml"
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        raise ConfigError(f"Error saving config file: {e}")


def get_joiner(language: str) -> str:
    """
    Returns the joiner character for the given language.

    Args:
        language (str): The language code (e.g., "en", "zh", "de").

    Returns:
        str: The joiner character (" " or "").
    """
    if language == "zh":
        return ""
    return " "
