import logging
import spacy
from spacy.cli.download import download
from backend.utils import load_config

logger = logging.getLogger(__name__)

SPLIT_BY_MARK_FILE = "output/log/split_by_mark.txt"

# Default map if not in config
DEFAULT_SPACY_MODEL_MAP = {
    "en": "en_core_web_md",
    "zh": "zh_core_web_sm",
    "de": "de_core_news_md",
}


def get_spacy_model(language: str):
    config = load_config()
    # Try to get map from config, else use default
    model_map = config.get("app", {}).get("spacy_model_map", DEFAULT_SPACY_MODEL_MAP)

    model = model_map.get(language.lower(), "en_core_web_md")
    if language not in model_map:
        logger.warning(
            f"Spacy model does not support '{language}', using en_core_web_md model as fallback..."
        )
    return model


def init_nlp():
    try:
        config = load_config()
        # Determine language: prioritize target_language, fallback to 'de' for this app
        language = config.get("app", {}).get("target_language", "de")

        model = get_spacy_model(language)
        logger.info(f"Loading NLP Spacy model: <{model}> ...")

        try:
            nlp = spacy.load(model)
        except OSError:
            logger.warning(f"Downloading {model} model...")
            logger.warning(
                "If download failed, please check your network and try again."
            )
            download(model)
            nlp = spacy.load(model)

        logger.info("NLP Spacy model loaded successfully!")
        return nlp
    except Exception as e:
        logger.error(f"Failed to load NLP Spacy model: {e}")
        raise e
