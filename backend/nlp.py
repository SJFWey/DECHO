import logging
from typing import Any, Dict, List

from backend.llm import split_text_by_meaning
from backend.utils import load_config, get_joiner
import spacy
from spacy.cli.download import download
import itertools
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# --- Spacy Model Loading ---

DEFAULT_SPACY_MODEL_MAP = {
    "en": "en_core_web_md",
    "zh": "zh_core_web_sm",
    "de": "de_core_news_md",
}

_SPACY_CACHE: Dict[str, Any] = {}


def get_spacy_model(language: str):
    config = load_config()
    model_map = config.get("app", {}).get("spacy_model_map", DEFAULT_SPACY_MODEL_MAP)
    model = model_map.get(language.lower(), "en_core_web_md")
    if language not in model_map:
        logger.warning(
            f"Spacy model does not support '{language}', using en_core_web_md model as fallback..."
        )
    return model


def init_nlp(language: str = None):
    global _SPACY_CACHE
    try:
        config = load_config()
        if language is None:
            language = config.get("app", {}).get("source_language", "en")

        if language in _SPACY_CACHE:
            return _SPACY_CACHE[language]

        model = get_spacy_model(language)
        logger.info(f"Loading NLP Spacy model for language '{language}': <{model}> ...")

        try:
            nlp = spacy.load(model)
        except OSError:
            logger.warning(f"Downloading {model} model...")
            logger.warning(
                "If download failed, please check your network and try again."
            )
            download(model)
            nlp = spacy.load(model)

        _SPACY_CACHE[language] = nlp
        return nlp
        return nlp
    except Exception as e:
        logger.error(f"Failed to load NLP model: {e}")
        raise


# --- Split by Comma ---


def is_valid_phrase(phrase):
    has_subject = any(
        token.dep_ in ["nsubj", "nsubjpass"] or token.pos_ == "PRON" for token in phrase
    )
    has_verb = any((token.pos_ == "VERB" or token.pos_ == "AUX") for token in phrase)
    return has_subject and has_verb


def analyze_comma(start, doc, token):
    left_phrase = doc[max(start, token.i - 9) : token.i]
    right_phrase = doc[token.i + 1 : min(len(doc), token.i + 10)]

    suitable_for_splitting = is_valid_phrase(right_phrase)

    left_words = [t for t in left_phrase if not t.is_punct]
    right_words = list(itertools.takewhile(lambda t: not t.is_punct, right_phrase))

    if len(left_words) <= 3 or len(right_words) <= 3:
        suitable_for_splitting = False

    return suitable_for_splitting


def split_by_comma(text, nlp):
    doc = nlp(text)
    sentences = []
    start = 0

    for i, token in enumerate(doc):
        if token.text == "," or token.text == "":
            suitable_for_splitting = analyze_comma(start, doc, token)
            if suitable_for_splitting:
                sentences.append(doc[start : token.i].text.strip())
                start = token.i + 1

    sentences.append(doc[start:].text.strip())
    return [s for s in sentences if s]


# --- Split by Connectors ---


def analyze_connectors(doc, token):
    lang = doc.lang_
    if lang == "en":
        connectors = ["that", "which", "where", "when", "because", "but", "and", "or"]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "zh":
        connectors = ["", "", "", "", "", "", "", ""]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "ja":
        connectors = ["", "", "", "", "", "", ""]
        mark_dep = "mark"
        det_pron_deps = ["case"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "fr":
        connectors = ["que", "qui", "où", "quand", "parce que", "mais", "et", "ou"]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "ru":
        connectors = ["что", "который", "где", "когда", "потому что", "но", "и", "или"]
        mark_dep = "mark"
        det_pron_deps = ["det"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "es":
        connectors = ["que", "cual", "donde", "cuando", "porque", "pero", "y", "o"]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "de":
        connectors = ["dass", "welche", "wo", "wann", "weil", "aber", "und", "oder"]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "it":
        connectors = ["che", "quale", "dove", "quando", "perché", "ma", "e", "o"]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    else:
        return False, False

    if token.text.lower() not in connectors:
        return False, False

    if lang == "en" and token.text.lower() == "that":
        if token.dep_ == mark_dep and token.head.pos_ == verb_pos:
            return True, False
        else:
            return False, False
    elif token.dep_ in det_pron_deps and token.head.pos_ in noun_pos:
        return False, False
    else:
        return True, False


def split_by_connectors(text, context_words=5, nlp=None):
    doc = nlp(text)
    sentences = [doc.text]

    while True:
        split_occurred = False
        new_sentences = []

        for sent in sentences:
            doc = nlp(sent)
            start = 0

            for i, token in enumerate(doc):
                split_before, _ = analyze_connectors(doc, token)

                if i + 1 < len(doc) and doc[i + 1].text in [
                    "'s",
                    "'re",
                    "'ve",
                    "'ll",
                    "'d",
                ]:
                    continue

                left_words = doc[max(0, token.i - context_words) : token.i]
                right_words = doc[
                    token.i + 1 : min(len(doc), token.i + context_words + 1)
                ]

                left_words = [word.text for word in left_words if not word.is_punct]
                right_words = [word.text for word in right_words if not word.is_punct]

                if (
                    len(left_words) >= context_words
                    and len(right_words) >= context_words
                    and split_before
                ):
                    new_sentences.append(doc[start : token.i].text.strip())
                    start = token.i
                    split_occurred = True
                    break

            if start < len(doc):
                new_sentences.append(doc[start:].text.strip())

        if not split_occurred:
            break

        sentences = new_sentences

    return sentences


# --- Split Long by Root ---


def split_long_sentence(doc):
    tokens = [token.text for token in doc]
    n = len(tokens)

    dp = [float("inf")] * (n + 1)
    dp[0] = 0
    prev = [0] * (n + 1)

    for i in range(1, n + 1):
        for j in range(max(0, i - 100), i):
            if i - j >= 30:
                token = doc[i - 1]
                if j == 0 or (
                    token.is_sent_end
                    or token.pos_ in ["VERB", "AUX"]
                    or token.dep_ == "ROOT"
                ):
                    if dp[j] + 1 < dp[i]:
                        dp[i] = dp[j] + 1
                        prev[i] = j

    sentences = []
    i = n

    config = load_config()
    language = config.get("app", {}).get("target_language", "de")
    joiner = get_joiner(language)

    while i > 0:
        j = prev[i]
        sentences.append(joiner.join(tokens[j:i]).strip())
        i = j

    return sentences[::-1]


logger = logging.getLogger(__name__)


def align_segments_with_tokens(
    parts: List[str], tokens: List[str], timestamps: List[float]
) -> List[Dict[str, Any]]:
    """
    Aligns text parts with audio using token timestamps.
    """
    if not tokens or not timestamps or len(tokens) != len(timestamps):
        logger.warning(
            "Invalid tokens/timestamps for alignment. Falling back to linear."
        )
        return []

    # 1. Build character map from tokens
    # char_map[i] = start_time of character i in "".join(tokens)
    char_map = []
    current_time = 0.0

    # Pre-process tokens to ensure they are strings
    clean_tokens = [str(t) for t in tokens]

    # We assume timestamps[i] is the END time of tokens[i]
    # But we need to handle the first token start time.
    # If we don't have start times, we assume contiguous flow.

    for i, token in enumerate(clean_tokens):
        end_time = timestamps[i]
        # Start time is previous end time
        start_time = current_time

        # Sanity check: if timestamp is weird
        if end_time < start_time:
            end_time = start_time + 0.01

        token_len = len(token)
        if token_len > 0:
            duration = end_time - start_time
            step = duration / token_len
            for j in range(token_len):
                char_time = start_time + j * step
                char_map.append(char_time)

        current_time = end_time

    raw_text = "".join(clean_tokens)
    max_idx = len(raw_text)

    aligned_segments = []
    raw_idx = 0

    for part in parts:
        if not part:
            continue

        # Heuristic: match characters
        match_start_idx = -1
        match_end_idx = -1

        current_raw_idx = raw_idx
        first_char_found = False

        for char in part:
            if char.isspace():
                continue

            found = False
            # Lookahead 100 chars
            for offset in range(100):
                if current_raw_idx + offset < max_idx:
                    if raw_text[current_raw_idx + offset].lower() == char.lower():
                        if not first_char_found:
                            match_start_idx = current_raw_idx + offset
                            first_char_found = True
                        current_raw_idx = current_raw_idx + offset + 1
                        found = True
                        break

            if not found:
                pass

        match_end_idx = current_raw_idx

        if match_start_idx != -1 and match_end_idx > match_start_idx:
            part_start_time = char_map[match_start_idx]
            if match_end_idx < len(char_map):
                part_end_time = char_map[match_end_idx]
            else:
                part_end_time = current_time

            raw_idx = match_end_idx
        else:
            # Fallback
            part_start_time = aligned_segments[-1]["end"] if aligned_segments else 0.0
            part_end_time = part_start_time + 0.1

        aligned_segments.append(
            {"text": part, "start": part_start_time, "end": part_end_time}
        )

    return aligned_segments


def split_sentences(
    segments: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Refines segments using NLP to split long sentences.
    Adapts logic from VideoLingo's _3_1_split_nlp.py

    Args:
        segments (List[Dict[str, Any]]): List of segments with 'text', 'start', 'end' keys.
                                         Optional 'tokens' and 'timestamps' for precise alignment.
        config (Dict[str, Any]): Configuration dict with 'app.max_split_length' key.

    Returns:
        List[Dict[str, Any]]: List of refined segments with interpolated timestamps.
    """
    logger.info("Starting NLP sentence splitting...")

    source_lang = config.get("app", {}).get("source_language", "en")
    nlp = init_nlp(language=source_lang)

    max_len = config.get("app", {}).get("max_split_length", 80)
    use_llm = config.get("app", {}).get("use_llm", False)
    logger.debug(f"Max split length set to: {max_len}, Use LLM: {use_llm}")

    refined_segments = []

    for i, seg in enumerate(segments):
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        duration = end - start

        tokens = seg.get("tokens")
        timestamps = seg.get("timestamps")

        parts = []
        if use_llm:
            try:
                logger.info(f"Splitting segment {i} with LLM...")
                parts = split_text_by_meaning(text, max_length=max_len)
            except Exception as e:
                logger.error(
                    f"LLM splitting failed: {e}. Falling back to rule-based splitting."
                )
                parts = []

        if not parts:
            # 0. Initial split by sentence endings (basic spaCy)
            # This handles cases where ASR returns multiple sentences in one segment
            doc = nlp(text)
            parts = [sent.text.strip() for sent in doc.sents]

            # 1. Split by comma
            new_parts = []
            for part in parts:
                if len(part) > max_len:
                    new_parts.extend(split_by_comma(part, nlp))
                else:
                    new_parts.append(part)
            parts = new_parts

            # 2. Split by connectors
            new_parts = []
            for part in parts:
                if len(part) > max_len:
                    new_parts.extend(
                        split_by_connectors(part, context_words=5, nlp=nlp)
                    )
                else:
                    new_parts.append(part)
            parts = new_parts

            # 3. Split by root (last resort for very long sentences)
            new_parts = []
            for part in parts:
                if len(part) > max_len:
                    doc_part = nlp(part)
                    new_parts.extend(split_long_sentence(doc_part))
                else:
                    new_parts.append(part)
            parts = new_parts

        # 4. Interpolate timestamps
        # Try to use token-based alignment if available
        aligned = []
        if tokens and timestamps:
            aligned = align_segments_with_tokens(parts, tokens, timestamps)

        if aligned:
            refined_segments.extend(aligned)
        else:
            # Fallback: distribute the original duration among parts based on character length
            total_chars = sum(len(p) for p in parts)

            current_start = start
            for part in parts:
                part_len = len(part)
                if total_chars > 0:
                    part_duration = (part_len / total_chars) * duration
                else:
                    part_duration = 0

                refined_segments.append(
                    {
                        "start": current_start,
                        "end": current_start + part_duration,
                        "text": part,
                    }
                )
                current_start += part_duration

    logger.info(
        f"NLP splitting complete. {len(segments)} segments -> {len(refined_segments)} segments."
    )
    return refined_segments
