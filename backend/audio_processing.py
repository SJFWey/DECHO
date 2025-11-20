import logging
import os
import shutil
import subprocess
from typing import Optional
import soundfile as sf

from backend.exceptions import AudioConversionError
from backend.utils import load_config

logger = logging.getLogger(__name__)


def _ffmpeg_binary() -> Optional[str]:
    """
    Return the preferred ffmpeg binary path if available.

    Returns:
        Optional[str]: Absolute path to ffmpeg or None when not found.
    """
    custom = os.getenv("FFMPEG_BINARY")
    if custom and os.path.exists(custom):
        return custom
    return shutil.which("ffmpeg")


def apply_demucs(input_path: str) -> str:
    """
    Apply Demucs to separate vocals from the audio.
    Returns the path to the separated vocals file.
    """
    logger.info(f"Applying Demucs to: {input_path}")

    # Check if demucs is installed
    if not shutil.which("demucs"):
        logger.warning("Demucs is enabled but not found in PATH. Skipping Demucs.")
        return input_path

    output_dir = os.path.join(os.path.dirname(input_path), "separated")
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "demucs",
        "-n",
        "htdemucs",
        input_path,
        "-o",
        output_dir,
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Construct expected path: output_dir/htdemucs/{filename_without_ext}/vocals.wav
        filename = os.path.splitext(os.path.basename(input_path))[0]
        vocals_path = os.path.join(output_dir, "htdemucs", filename, "vocals.wav")

        if os.path.exists(vocals_path):
            logger.info(f"Demucs separation successful: {vocals_path}")
            return vocals_path
        else:
            logger.error(f"Demucs output not found at: {vocals_path}")
            return input_path

    except subprocess.CalledProcessError as exc:
        error_msg = exc.stderr.decode().strip() if exc.stderr else str(exc)
        logger.error(f"Demucs failed: {error_msg}")
        return input_path


def convert_to_wav(input_path: str) -> str:
    """
    Convert an arbitrary audio file to a mono 16 kHz WAV file.

    Args:
        input_path (str): Source audio path supplied by the user.

    Returns:
        str: Path to the converted WAV file.

    Raises:
        AudioConversionError: Raised when conversion fails for all available backends.
    """
    logger.info(f"Converting audio: {input_path}")

    # Check for Demucs
    try:
        config = load_config()
        if config.get("asr", {}).get("enable_demucs", False):
            input_path = apply_demucs(input_path)
    except Exception as e:
        logger.warning(f"Failed to load config or apply Demucs: {e}")

    # Check if conversion is needed
    # Only check properties if it looks like a WAV file to avoid soundfile errors on other formats
    if input_path.lower().endswith(".wav"):
        try:
            info = sf.info(input_path)
            if (
                info.samplerate == 16000
                and info.channels == 1
                and info.format == "WAV"
                and info.subtype in ["PCM_16", "FLOAT"]
            ):
                logger.info(f"Audio is already 16kHz mono WAV: {input_path}")
                return input_path
        except Exception as e:
            logger.warning(f"Failed to check audio properties with soundfile: {e}")

    output_path = os.path.splitext(input_path)[0] + ".wav"

    if os.path.abspath(input_path) == os.path.abspath(output_path):
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_converted.wav"

    ffmpeg_bin = _ffmpeg_binary()

    if not ffmpeg_bin:
        logger.error("ffmpeg executable not found.")
        raise AudioConversionError(
            "ffmpeg executable not found. Please install ffmpeg and add it to your PATH."
        )

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Audio converted successfully: {output_path}")
        return output_path
    except subprocess.CalledProcessError as exc:
        error_msg = exc.stderr.decode().strip() if exc.stderr else str(exc)
        logger.error(f"ffmpeg conversion failed: {error_msg}")
        raise AudioConversionError(f"ffmpeg conversion failed: {error_msg}") from exc
