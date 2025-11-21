import logging
import os
import threading
from typing import Any, Dict

from dotenv import load_dotenv
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


_config_cache = None
_config_loaded = False
_config_lock = threading.Lock()


def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("true", "1", "yes", "on")


def load_config(reload: bool = False) -> Dict[str, Any]:
    """
    Loads and validates the configuration from environment variables.
    Caches the configuration for performance.
    Thread-safe using double-checked locking pattern.

    Returns:
        Dict[str, Any]: The configuration dictionary.

    Raises:
        ConfigError: If required configuration is missing or invalid.
    """
    global _config_cache, _config_loaded

    # Fast path: check if cache is valid without lock
    if _config_cache is not None and not reload and _config_loaded:
        return _config_cache

    # Need to load config - acquire lock
    with _config_lock:
        # Double-check inside lock
        if _config_cache is not None and not reload and _config_loaded:
            return _config_cache

        # Load .env file if it exists
        load_dotenv(override=reload)

        # Build configuration from environment variables
        config = {
            "llm": {
                "api_key": os.getenv("LLM_API_KEY", ""),
                "base_url": os.getenv("LLM_BASE_URL", "https://example-llm-provider.com/v1"),
                "model": os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            },
            "tts": {
                "api_key": os.getenv("TTS_API_KEY", ""),
                "model": os.getenv("TTS_MODEL", "gemini-2.5-flash-preview-tts"),
                "voice_map": {
                    "male": os.getenv("TTS_VOICE_MALE", "Orus"),
                    "female": os.getenv("TTS_VOICE_FEMALE", "Kore"),
                },
                "defaults": {
                    "speed": os.getenv("TTS_SPEED", "Native conversational pace"),
                    "tone": os.getenv("TTS_TONE", "Clear, educational, engaging"),
                    "language": os.getenv("TTS_LANGUAGE", "de-DE"),
                },
            },
            "asr": {
                "method": os.getenv("ASR_METHOD", "parakeet"),
                "parakeet_model_dir": os.getenv(
                    "ASR_PARAKEET_MODEL_DIR",
                    "models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
                ),
                "enable_demucs": _str_to_bool(os.getenv("ASR_ENABLE_DEMUCS", "false")),
                "enable_vad": _str_to_bool(os.getenv("ASR_ENABLE_VAD", "false")),
            },
            "app": {
                "max_split_length": int(os.getenv("APP_MAX_SPLIT_LENGTH", "80")),
                "use_llm": _str_to_bool(os.getenv("APP_USE_LLM", "true")),
                "source_language": os.getenv("APP_SOURCE_LANGUAGE", "de"),
                "target_language": os.getenv("APP_TARGET_LANGUAGE", "de"),
                "spacy_model_map": {
                    "de": os.getenv("APP_SPACY_MODEL_DE", "de_core_news_md"),
                },
            },
        }

        # Basic validation
        if not config["asr"] or not config["app"]:
            raise ConfigError("Invalid config: missing 'asr' or 'app' sections")

        _config_cache = config
        _config_loaded = True

        return config


def get_joiner(language: str) -> str:
    """
    Returns the joiner character for the given language.

    Args:
        language (str): The language code (e.g., "de").

    Returns:
        str: The joiner character (" " or "").
    """
    if language == "zh":
        return ""
    return " "
