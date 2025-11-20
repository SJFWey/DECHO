import logging
from typing import Any, Dict, List

from backend.llm import split_text_by_meaning
from backend.spacy_utils.load_nlp_model import init_nlp
from backend.spacy_utils.split_by_comma import split_by_comma
from backend.spacy_utils.split_by_connector import split_by_connectors
from backend.spacy_utils.split_long_by_root import split_long_sentence

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
    nlp = init_nlp()
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
