from typing import Any, Dict, List


def format_timestamp(seconds: float) -> str:
    """
    Converts seconds to SRT timestamp format: HH:MM:SS,mmm

    Args:
        seconds (float): Time in seconds.

    Returns:
        str: Formatted timestamp string.
    """
    millis = int((seconds - int(seconds)) * 1000)
    seconds_int = int(seconds)
    minutes = seconds_int // 60
    hours = minutes // 60
    minutes %= 60
    seconds_int %= 60
    return f"{hours:02}:{minutes:02}:{seconds_int:02},{millis:03}"


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """
    Generates SRT content from segments.

    Args:
        segments (List[Dict[str, Any]]): List of segments with 'text', 'start', 'end' keys.

    Returns:
        str: The complete SRT file content.
    """
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"]

        srt_lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    return "\n".join(srt_lines)
