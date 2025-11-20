import os
import sys
import logging
import subprocess

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import SessionLocal
from server.models import Task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_duration_ffprobe(file_path):
    """Get duration using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
    return None


def fix_durations():
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.duration.is_(None)).all()
        logger.info(f"Found {len(tasks)} tasks with missing duration.")

        for task in tasks:
            if not task.filePath:
                continue

            # Handle relative paths if necessary, assuming running from root
            file_path = task.filePath
            if not os.path.exists(file_path):
                # Try relative to root if it was stored as relative
                if os.path.exists(os.path.join(os.getcwd(), file_path)):
                    file_path = os.path.join(os.getcwd(), file_path)
                else:
                    logger.warning(f"File not found: {task.filePath}")
                    continue

            duration = get_duration_ffprobe(file_path)
            if duration:
                task.duration = duration
                logger.info(f"Updated task {task.id} duration to {duration}")
            else:
                logger.warning(f"Could not determine duration for {file_path}")

        db.commit()
        logger.info("Finished updating durations.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    fix_durations()
