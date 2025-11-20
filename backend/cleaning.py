import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def export_segments_to_excel(segments: List[Dict[str, Any]], output_path: str) -> None:
    """
    Export segments to an Excel file for manual cleaning.

    Args:
        segments: List of dictionaries with keys 'start', 'end', 'text'.
        output_path: Path to save the Excel file.
    """
    try:
        df = pd.DataFrame(segments)
        # Ensure columns exist
        if "speaker_id" not in df.columns:
            df["speaker_id"] = "SPEAKER_00"

        # Reorder columns
        cols = ["start", "end", "speaker_id", "text"]
        # Add any other columns that might be present
        for col in df.columns:
            if col not in cols:
                cols.append(col)

        df = df[cols]

        df.to_excel(output_path, index=False)
        logger.info(f"Exported segments to {output_path}")
    except Exception as e:
        logger.error(f"Failed to export segments to Excel: {e}")
        raise


def import_segments_from_excel(input_path: str) -> List[Dict[str, Any]]:
    """
    Import cleaned segments from an Excel file.

    Args:
        input_path: Path to the Excel file.

    Returns:
        List of dictionaries with keys 'start', 'end', 'text', etc.
    """
    try:
        df = pd.read_excel(input_path)
        # Fill NaNs with empty string for text
        if "text" in df.columns:
            df["text"] = df["text"].fillna("")

        segments = df.to_dict("records")
        logger.info(f"Imported {len(segments)} segments from {input_path}")
        # Cast to expected type since we know the structure
        return [dict(s) for s in segments]  # type: ignore
    except Exception as e:
        logger.error(f"Failed to import segments from Excel: {e}")
        raise
