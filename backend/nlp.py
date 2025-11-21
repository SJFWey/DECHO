import logging
import threading
from typing import Any, Dict, List, Optional

from backend.llm import split_text_by_meaning
from backend.utils import load_config, get_joiner
import spacy
from spacy.cli.download import download
import itertools
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# --- Spacy Model Loading ---

DEFAULT_SPACY_MODEL_MAP = {
    "de": "de_core_news_md",
}

_SPACY_CACHE: Dict[str, Any] = {}
_SPACY_LOCK = threading.Lock()


def get_spacy_model(language: str):
    config = load_config()
    model_map = config.get("app", {}).get("spacy_model_map", DEFAULT_SPACY_MODEL_MAP)
    model = model_map.get(language.lower(), "de_core_news_md")
    if language not in model_map:
        logger.warning(
            f"Spacy model does not support '{language}', using de_core_news_md model as fallback..."
        )
    return model


def init_nlp(language: Optional[str] = None):
    """
    Initializes and caches a spacy NLP model for the given language.
    Thread-safe using double-checked locking pattern.
    """
    global _SPACY_CACHE
    try:
        config = load_config()
        if language is None:
            language = config.get("app", {}).get("source_language", "de")

        if language is None:
            language = "de"

        # First check without lock (fast path)
        if language in _SPACY_CACHE:
            return _SPACY_CACHE[language]

        # Need to load model - acquire lock
        with _SPACY_LOCK:
            # Double-check inside lock
            if language in _SPACY_CACHE:
                return _SPACY_CACHE[language]

            model = get_spacy_model(language)
            logger.info(
                f"Loading NLP Spacy model for language '{language}': <{model}> ..."
            )

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
    if lang == "de":
        connectors = ["dass", "welche", "wo", "wann", "weil", "aber", "und", "oder"]
        det_pron_deps = ["det", "pron"]
        noun_pos = ["NOUN", "PROPN"]
    else:
        return False, False

    if token.text.lower() not in connectors:
        return False, False

    if token.dep_ in det_pron_deps and token.head.pos_ in noun_pos:
        return False, False
    else:
        return True, False


def split_by_connectors(text, context_words=5, nlp: Optional[Any] = None):
    if nlp is None:
        nlp = init_nlp()

    if nlp is None:
        raise ValueError("Failed to initialize NLP model")

    doc = nlp(text)
    sentences = [doc.text]

    # Safety measure: limit iterations to prevent infinite loops
    max_iterations = 100
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
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

    if iteration >= max_iterations:
        logger.warning(
            f"split_by_connectors reached max iterations ({max_iterations}). "
            "Returning current state to avoid infinite loop."
        )

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
    language = config.get("app", {}).get("source_language", "de")
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
    Aligns text segments with original tokens to retrieve precise timestamps.
    Uses a robust normalization approach to handle punctuation/whitespace differences.

    Args:
        parts (List[str]): List of text segments (e.g. from LLM).
        tokens (List[str]): List of original tokens from ASR.
        timestamps (List[float]): List of end timestamps for each token.

    Returns:
        List[Dict[str, Any]]: Aligned segments with 'start' and 'end' keys.
    """
    if not tokens or not timestamps or len(tokens) != len(timestamps):
        logger.warning(
            "Invalid tokens/timestamps for alignment. Falling back to linear."
        )
        return []

    clean_tokens = [str(t) for t in tokens]

    # Use language-aware joiner for token concatenation
    # For languages like Chinese/Japanese, tokens don't need spaces
    # For others (English, German, etc.), they do
    config = load_config()
    language = config.get("app", {}).get("source_language", "de")
    joiner = get_joiner(language)
    full_text = joiner.join(clean_tokens)

    if not full_text:
        logger.warning("Tokenizer returned empty text. Falling back to linear.")
        return []

    # Build per-token timing info and a char->token lookup table
    token_infos: List[Dict[str, float]] = []
    char_to_token: List[int] = []
    prev_end_time = 0.0

    for idx, token in enumerate(clean_tokens):
        try:
            end_time = float(timestamps[idx])
        except (TypeError, ValueError):
            logger.warning(
                "Non-numeric timestamp detected for token %s. Falling back to linear.",
                token,
            )
            return []

        # Determine start time for this token
        # If it's the first token, or if there's a large gap from previous token,
        # we estimate start time to avoid stretching the token duration.
        if idx == 0:
            # First token: assume it's short (e.g. max 0.5s) or starts at 0 if close enough
            start_time = max(0.0, end_time - 0.5)
        else:
            # Check gap
            if end_time - prev_end_time > 1.0:  # If gap > 1s, treat as silence
                start_time = max(prev_end_time, end_time - 0.5)
            else:
                start_time = prev_end_time

        # Ensure monotonicity (though start_time logic above tries to respect it)
        if start_time < prev_end_time:
            start_time = prev_end_time

        if end_time < start_time:
            end_time = start_time

        token_infos.append({"start_time": start_time, "end_time": end_time})

        for _ in token:
            char_to_token.append(idx)

        prev_end_time = end_time

    if len(char_to_token) != len(full_text):
        logger.warning("Token/text length mismatch detected. Falling back to linear.")
        return []

    # Create normalized text and mapping back to original indices
    # We want to match alphanumeric characters only to be robust against punctuation changes
    normalized_text = ""
    norm_to_orig_map = []

    for i, char in enumerate(full_text):
        if char.isalnum():
            normalized_text += char.lower()
            norm_to_orig_map.append(i)

    aligned_segments: List[Dict[str, Any]] = []
    search_pos = 0

    for part in parts:
        # Normalize the part
        part_norm = "".join([c.lower() for c in part if c.isalnum()])

        if not part_norm:
            continue

        # Find in normalized text
        match_start = normalized_text.find(part_norm, search_pos)

        if match_start == -1:
            # Try from beginning if not found (in case of overlap or reordering)
            match_start = normalized_text.find(part_norm)

        if match_start == -1:
            # Fallback for this part if still not found
            part_start_time = aligned_segments[-1]["end"] if aligned_segments else 0.0
            part_end_time = part_start_time + 0.1
            aligned_segments.append(
                {"text": part, "start": part_start_time, "end": part_end_time}
            )
            continue

        match_end = match_start + len(part_norm)

        # Map back to original indices with bounds checking
        # match_end is exclusive in slice, so the last char index is match_end - 1
        if match_end > len(norm_to_orig_map):
            match_end = len(norm_to_orig_map)

        if match_end == 0:
            # Edge case: empty match
            part_start_time = aligned_segments[-1]["end"] if aligned_segments else 0.0
            part_end_time = part_start_time + 0.1
            aligned_segments.append(
                {"text": part, "start": part_start_time, "end": part_end_time}
            )
            continue

        orig_start_index = norm_to_orig_map[match_start]
        orig_end_index = norm_to_orig_map[match_end - 1]

        # Map to tokens
        start_token_idx = char_to_token[orig_start_index]
        end_token_idx = char_to_token[orig_end_index]

        part_start_time = token_infos[start_token_idx]["start_time"]
        part_end_time = token_infos[end_token_idx]["end_time"]

        if part_end_time < part_start_time:
            part_end_time = part_start_time

        aligned_segments.append(
            {"text": part, "start": part_start_time, "end": part_end_time}
        )

        search_pos = match_end

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

    source_lang = config.get("app", {}).get("source_language", "de")
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

    # Extend the end of each segment by 150ms to avoid abrupt cut-offs
    for seg in refined_segments:
        seg["end"] += 0.15

    return refined_segments
