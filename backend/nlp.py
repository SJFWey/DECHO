from backend.spacy_utils.load_nlp_model import init_nlp
from backend.spacy_utils.split_by_comma import split_by_comma
from backend.spacy_utils.split_by_connector import split_by_connectors
from backend.spacy_utils.split_long_by_root import split_long_sentence


def split_sentences(segments, config):
    """
    Refines segments using NLP to split long sentences.
    Adapts logic from VideoLingo's _3_1_split_nlp.py
    """
    nlp = init_nlp()
    max_len = config.get("app", {}).get("max_split_length", 80)

    refined_segments = []

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        duration = end - start

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
                new_parts.extend(split_by_connectors(part, context_words=5, nlp=nlp))
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
        # We distribute the original duration among parts based on character length
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

    return refined_segments
