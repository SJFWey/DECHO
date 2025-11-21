import os
import uuid
import logging
import shutil
import json
import time
from typing import Dict

import soundfile as sf
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from server.schemas import TaskResponse, TaskStatus, SubtitleResponse
from server.database import get_db, SessionLocal
from server.models import Task, PracticeRecording
from backend.audio_processing import convert_to_wav
from backend.asr import transcribe_audio
from backend.nlp import split_sentences
from backend.subtitle import generate_srt
from backend.utils import load_config
from backend.audio_generation import process_uploaded_file, generate_audio

router = APIRouter()
logger = logging.getLogger(__name__)

# Configure logging to file
LOG_DIR = "output/log"
os.makedirs(LOG_DIR, exist_ok=True)
file_handler = logging.FileHandler(
    os.path.join(LOG_DIR, "audio_processing.log"), encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

UPLOAD_DIR = "output/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def process_audio_task(task_id: str):
    db = SessionLocal()
    task = None
    total_start = time.perf_counter()
    timings: Dict[str, float] = {}
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in background task")
            return

        task.status = TaskStatus.PROCESSING
        task.progress = 0.1
        db.commit()

        # 1. Convert to WAV
        step_start = time.perf_counter()
        wav_path = convert_to_wav(task.filePath)
        timings["convert_to_wav"] = time.perf_counter() - step_start
        task.progress = 0.3
        db.commit()

        # 2. ASR
        step_start = time.perf_counter()
        asr_result = transcribe_audio(wav_path)
        timings["transcribe_audio"] = time.perf_counter() - step_start
        task.progress = 0.6
        db.commit()

        # 3. NLP Split
        config = load_config()

        # Calculate duration from audio file for fallback
        try:
            audio_info = sf.info(wav_path)
            file_duration = audio_info.duration
        except Exception as e:
            logger.warning(f"Could not get duration from audio file: {e}")
            file_duration = 0.0

        # Cleanup temporary WAV file if it was created
        if wav_path != task.filePath and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary WAV file {wav_path}: {e}")

        # Pre-process: Split ASR result by silence gaps to avoid merging sentences across large silences
        asr_tokens = asr_result.get("tokens", [])
        asr_timestamps = asr_result.get("timestamps", [])

        segments = []

        if asr_tokens and asr_timestamps and len(asr_tokens) == len(asr_timestamps):
            current_tokens = []
            current_timestamps = []
            last_end = 0.0

            for i, (tok, end) in enumerate(zip(asr_tokens, asr_timestamps)):
                # Check gap (threshold 2.0s)
                # Note: end is the end time of the current token.
                # We compare it with last_end (end time of previous token).
                # If end - last_end is large, it means there is a gap BEFORE this token.
                # But wait, 'end' includes the duration of the current token.
                # So the gap is (start_of_current - end_of_prev).
                # Since we don't have start_of_current, we use (end_of_current - duration_of_current - end_of_prev).
                # Assuming duration is small (<1s), if (end - last_end) > 3.0s, it's likely a gap.

                if i > 0 and (end - last_end > 2.0):
                    # Flush current segment
                    if current_tokens:
                        segments.append(
                            {
                                "text": "".join(current_tokens),
                                "start": (
                                    current_timestamps[0] - 0.5
                                    if current_timestamps[0] > 0.5
                                    else 0.0
                                ),
                                "end": last_end,
                                "tokens": current_tokens,
                                "timestamps": current_timestamps,
                            }
                        )
                    current_tokens = []
                    current_timestamps = []

                current_tokens.append(tok)
                current_timestamps.append(end)
                last_end = end

            # Flush last
            if current_tokens:
                segments.append(
                    {
                        "text": "".join(current_tokens),
                        "start": (
                            current_timestamps[0] - 0.5
                            if current_timestamps[0] > 0.5
                            else 0.0
                        ),
                        "end": last_end,
                        "tokens": current_tokens,
                        "timestamps": current_timestamps,
                    }
                )

        if not segments:
            # Fallback if no tokens or splitting failed
            segments = [
                {
                    "text": asr_result["text"],
                    "start": 0.0,
                    "end": 0.0,  # Will be fixed below
                    "tokens": asr_result["tokens"],
                    "timestamps": asr_result["timestamps"],
                }
            ]

        # Use timestamp from ASR if available, otherwise use file duration
        last_timestamp = (
            asr_result["timestamps"][-1] if asr_result["timestamps"] else 0.0
        )
        duration = last_timestamp if last_timestamp > 0 else file_duration

        # Ensure the last segment has a valid end time if not set correctly
        if segments:
            segments[-1]["end"] = max(segments[-1]["end"], duration)

        task.duration = duration

        step_start = time.perf_counter()
        refined_segments = split_sentences(segments, config)
        timings["split_sentences"] = time.perf_counter() - step_start
        task.progress = 0.9
        db.commit()

        # 4. Generate SRT
        step_start = time.perf_counter()
        srt_content = generate_srt(refined_segments)
        timings["generate_srt"] = time.perf_counter() - step_start

        result_data = {"segments": refined_segments, "srt": srt_content}
        task.result = json.dumps(result_data)
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        db.commit()

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        if task:
            task.status = TaskStatus.FAILED
            task.message = str(e)
            db.commit()
    finally:
        total_elapsed = time.perf_counter() - total_start
        timings["total"] = total_elapsed

        summary_parts = [
            f"{name}={duration:.2f}s" for name, duration in timings.items()
        ]
        logger.info(
            "Task %s timing breakdown -> %s", task_id, " | ".join(summary_parts)
        )

        longest_step = max(
            ((name, duration) for name, duration in timings.items() if name != "total"),
            key=lambda item: item[1],
            default=(None, None),
        )
        if longest_step[0] is not None:
            logger.info(
                "Task %s slowest step: %s (%.2fs)",
                task_id,
                longest_step[0],
                longest_step[1],
            )

        db.close()


def convert_text_and_process(task_id: str, temp_text_path: str, original_filename: str):
    db = SessionLocal()
    task = None
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in text conversion task")
            return

        task.message = "Generating audio..."
        db.commit()

        # Generate Audio
        try:
            text_content = process_uploaded_file(temp_text_path)
            generated_audio_path = generate_audio(text_content)
            if not generated_audio_path:
                raise Exception("TTS generation returned None")
        except Exception as e:
            logger.error(f"Text to Audio failed: {e}")
            task.status = TaskStatus.FAILED
            task.message = f"Text to Audio failed: {str(e)}"
            db.commit()
            return
        finally:
            if os.path.exists(temp_text_path):
                os.remove(temp_text_path)

        # Move and rename
        new_filename = os.path.splitext(original_filename)[0] + ".wav"
        file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{new_filename}")
        shutil.move(generated_audio_path, file_path)

        # task.filename = new_filename # Keep original filename for display
        task.filePath = file_path
        db.commit()

        # Now trigger the regular audio processing
        process_audio_task(task_id)

    except Exception as e:
        logger.error(f"Background text conversion failed: {e}")
        if task:
            task.status = TaskStatus.FAILED
            task.message = f"System error: {str(e)}"
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=TaskResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    task_id = str(uuid.uuid4())
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext in [".txt", ".md"]:
        # Save text file temporarily
        temp_text_path = os.path.join(UPLOAD_DIR, f"{task_id}_{filename}")
        with open(temp_text_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Create task immediately
        new_task = Task(
            id=task_id,
            status=TaskStatus.PROCESSING,
            filename=filename,
            filePath=temp_text_path,
            progress=0.0,
            message="Queued for audio generation...",
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # Offload to background
        background_tasks.add_task(
            convert_text_and_process, task_id, temp_text_path, filename
        )

        return TaskResponse(
            task_id=new_task.id,
            status=TaskStatus(new_task.status),
            message=new_task.message,
            progress=new_task.progress,
            file_path=new_task.filePath,
            filename=new_task.filename,
            duration=new_task.duration,
            created_at=new_task.createdAt,
        )

    else:
        file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{filename}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        new_task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            filename=filename,
            filePath=file_path,
            progress=0.0,
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return TaskResponse(
            task_id=new_task.id,
            status=TaskStatus(new_task.status),
            message="File uploaded successfully",
            progress=new_task.progress,
            file_path=new_task.filePath,
            filename=new_task.filename,
            duration=new_task.duration,
            created_at=new_task.createdAt,
        )


@router.post("/process/{task_id}", response_model=TaskResponse)
async def process_audio(
    task_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.PENDING:
        return TaskResponse(
            task_id=task.id,
            status=TaskStatus(task.status),
            message=task.message,
            progress=task.progress,
            last_played_chunk_index=task.lastPlayedChunkIndex,
            file_path=task.filePath,
            filename=task.filename,
            duration=task.duration,
            created_at=task.createdAt,
        )

    background_tasks.add_task(process_audio_task, task_id)

    task.status = TaskStatus.PROCESSING
    db.commit()

    return TaskResponse(
        task_id=task.id,
        status=TaskStatus(task.status),
        message="Processing started",
        progress=task.progress,
        last_played_chunk_index=task.lastPlayedChunkIndex,
        file_path=task.filePath,
        filename=task.filename,
        duration=task.duration,
        created_at=task.createdAt,
    )


@router.get("/status/{task_id}", response_model=TaskResponse)
async def get_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        task_id=task.id,
        status=TaskStatus(task.status),
        message=task.message,
        progress=task.progress,
        last_played_chunk_index=task.lastPlayedChunkIndex,
        file_path=task.filePath,
        filename=task.filename,
        duration=task.duration,
        created_at=task.createdAt,
    )


@router.get("/result/{task_id}", response_model=SubtitleResponse)
async def get_result(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task not completed")

    if not task.result:
        raise HTTPException(status_code=500, detail="Result is missing")

    result_data = json.loads(task.result)
    return SubtitleResponse(task_id=task.id, segments=result_data["segments"])


@router.get("/download/{task_id}/srt")
async def download_srt(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task not completed")

    if not task.result:
        raise HTTPException(status_code=500, detail="Result is missing")

    result_data = json.loads(task.result)
    srt_content = result_data.get("srt", "")

    # Save SRT to a temp file to serve it
    srt_path = os.path.join(UPLOAD_DIR, f"{task_id}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return FileResponse(
        srt_path, media_type="application/x-subrip", filename=f"subtitle_{task_id}.srt"
    )


@router.post("/practice/{task_id}/{segment_index}")
async def upload_practice_recording(
    task_id: str,
    segment_index: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Save file
    recording_dir = "output/user_recordings"
    os.makedirs(recording_dir, exist_ok=True)

    # Use a unique name
    ext = os.path.splitext(file.filename or "")[1] or ".webm"
    filename = f"{task_id}_{segment_index}_{uuid.uuid4()}{ext}"
    file_path = os.path.join(recording_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Save to DB
    recording = PracticeRecording(
        taskId=task_id,
        segmentIndex=segment_index,
        filePath=filename,  # Store filename relative to user_recordings mount
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)

    return {"message": "Recording saved", "filePath": filename}


@router.get("/practice/{task_id}")
async def get_practice_recordings(task_id: str, db: Session = Depends(get_db)):
    recordings = (
        db.query(PracticeRecording).filter(PracticeRecording.taskId == task_id).all()
    )
    return [
        {
            "id": r.id,
            "segmentIndex": r.segmentIndex,
            "filePath": r.filePath,
            "createdAt": r.createdAt,
        }
        for r in recordings
    ]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(Task).offset(skip).limit(limit).all()
    return [
        TaskResponse(
            task_id=task.id,
            status=TaskStatus(task.status),
            message=task.message,
            progress=task.progress,
            last_played_chunk_index=task.lastPlayedChunkIndex,
            file_path=task.filePath,
            filename=task.filename,
            duration=task.duration,
            created_at=task.createdAt,
        )
        for task in tasks
    ]


@router.post("/tasks/{task_id}/progress")
async def update_task_progress(
    task_id: str, last_played_chunk_index: int, db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.lastPlayedChunkIndex = last_played_chunk_index
    db.commit()
    return {"message": "Progress updated"}


@router.delete("/task/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 1. Delete practice recording files
    # Note: PracticeRecording.filePath is stored as filename relative to output/user_recordings
    recording_dir = "output/user_recordings"
    # Ensure recordings are loaded
    recordings = (
        db.query(PracticeRecording).filter(PracticeRecording.taskId == task_id).all()
    )

    for recording in recordings:
        if recording.filePath:
            rec_path = os.path.join(recording_dir, recording.filePath)
            if os.path.exists(rec_path):
                try:
                    os.remove(rec_path)
                except Exception as e:
                    logger.warning(f"Failed to delete recording file {rec_path}: {e}")

    # 2. Delete task audio file
    if task.filePath and os.path.exists(task.filePath):
        try:
            os.remove(task.filePath)
        except Exception as e:
            logger.warning(f"Failed to delete task file {task.filePath}: {e}")

    # 3. Delete task from DB (cascades to recordings)
    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}
