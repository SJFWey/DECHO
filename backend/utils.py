from rich import print as rprint


def load_key(key):
    # Mock implementation or read from global config
    # For now, return defaults
    defaults = {
        "whisper.language": "en",
        "whisper.detected_language": "en",
        "spacy_model_map": {"en": "en_core_web_sm", "zh": "zh_core_web_sm"},
    }
    return defaults.get(key, "en")


def get_joiner(language):
    if language == "zh":
        return ""
    return " "


def except_handler(msg):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                rprint(f"[red]{msg}: {e}[/red]")
                raise e

        return wrapper

    return decorator


_3_1_SPLIT_BY_NLP = "output/log/split_by_nlp.txt"
