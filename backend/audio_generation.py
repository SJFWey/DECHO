import logging
import os
import re
import sys
import uuid
from typing import Any, Dict, Optional
from pathlib import Path

# Add project root to sys.path to allow running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm import tts_llm

logger = logging.getLogger(__name__)


def generate_audio(
    text_content: str, options: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Generates audio from text using TTS LLM and saves it to a file.

    Args:
        text_content (str): The text to convert to speech.
        options (Optional[Dict[str, Any]]): Custom options for TTS.

    Returns:
        Optional[str]: The path to the generated audio file, or None if failed.
    """
    try:
        audio_bytes = tts_llm(text_content, options)

        if not audio_bytes:
            logger.error("TTS returned no audio bytes.")
            return None

        # Determine output directory
        # We can use a temp directory or a specific output directory
        # For now, let's use output/temp_tts
        output_dir = os.path.join("output", "temp_tts")
        os.makedirs(output_dir, exist_ok=True)

        # Generate unique filename
        filename = f"tts_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        logger.info(f"Audio generated and saved to: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to generate audio: {e}")
        return None


def process_uploaded_file(file_path: str) -> str:
    """
    Reads and processes an uploaded .txt or .md file for TTS generation.

    Args:
        file_path (str): The path to the uploaded file.

    Returns:
        str: The processed text content.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() not in [".txt", ".md"]:
        raise ValueError(
            f"Unsupported file type: {path.suffix}. Only .txt and .md are supported."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if path.suffix.lower() == ".md":
            # Basic Markdown cleanup
            # Remove images ![alt](url)
            content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
            # Replace links [text](url) with text
            content = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", content)
            # Remove header markers #
            content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
            # Remove bold/italic markers
            content = re.sub(r"\*\*|__", "", content)
            # Be careful with * and _ as they can be used for lists or other things.
            # Only remove if they are likely formatting.
            # For simplicity, let's just remove ** and __ for now, and maybe single * if it wraps text?
            # Let's stick to simple removal of ** and __

        return content.strip()

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise
