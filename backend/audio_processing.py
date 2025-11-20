import os
import shutil
import subprocess
from typing import Optional


class AudioConversionError(RuntimeError):
    """
    Raised when the uploaded audio cannot be converted to the normalized WAV format.
    """


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
    output_path = os.path.splitext(input_path)[0] + ".wav"

    if os.path.abspath(input_path) == os.path.abspath(output_path):
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_converted.wav"

    ffmpeg_bin = _ffmpeg_binary()

    ffmpeg_error: Optional[Exception] = None
    if ffmpeg_bin:
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
            return output_path
        except subprocess.CalledProcessError as exc:
            ffmpeg_error = exc
            print(f"ffmpeg conversion failed: {exc}")
    else:
        print(
            "ffmpeg executable not found. Set FFMPEG_BINARY env var or add ffmpeg to PATH to avoid pydub fallback."
        )

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format="wav")
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise AudioConversionError(
            "Failed to convert audio to WAV. Please provide a standard PCM/MP3/M4A file."
        ) from (exc if ffmpeg_error is None else ffmpeg_error)
