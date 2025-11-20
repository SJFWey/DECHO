import itertools
import os
import warnings
from backend.spacy_utils.load_nlp_model import init_nlp

warnings.filterwarnings("ignore", category=FutureWarning)


def is_valid_phrase(phrase):
    #  Check for subject and verb
    has_subject = any(
        token.dep_ in ["nsubj", "nsubjpass"] or token.pos_ == "PRON" for token in phrase
    )
    has_verb = any((token.pos_ == "VERB" or token.pos_ == "AUX") for token in phrase)
    return has_subject and has_verb


def analyze_comma(start, doc, token):
    left_phrase = doc[max(start, token.i - 9) : token.i]
    right_phrase = doc[token.i + 1 : min(len(doc), token.i + 10)]

    suitable_for_splitting = is_valid_phrase(
        right_phrase
    )  # and is_valid_phrase(left_phrase) # ! no need to chekc left phrase

    #  Remove punctuation and check word count
    left_words = [t for t in left_phrase if not t.is_punct]
    right_words = list(
        itertools.takewhile(lambda t: not t.is_punct, right_phrase)
    )  # ! only check the first part of the right phrase

    if len(left_words) <= 3 or len(right_words) <= 3:
        suitable_for_splitting = False

    return suitable_for_splitting


import logging

logger = logging.getLogger(__name__)


def split_by_comma(text, nlp):
    doc = nlp(text)
    sentences = []
    start = 0

    for i, token in enumerate(doc):
        if token.text == "," or token.text == "":
            suitable_for_splitting = analyze_comma(start, doc, token)

            if suitable_for_splitting:
                sentences.append(doc[start : token.i].text.strip())
                logger.debug(
                    f"Split at comma: {doc[start:token.i][-4:]},| {doc[token.i + 1:][:4]}"
                )
                start = token.i + 1

    sentences.append(doc[start:].text.strip())
    return sentences
