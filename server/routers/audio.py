import os
import uuid
import logging
import shutil
import json
import soundfile as sf
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from server.schemas import TaskResponse, TaskStatus, SubtitleResponse
from server.database import get_db, SessionLocal
from server.models import Task, PracticeRecording
from backend.audio_processing import convert_to_wav
from backend.asr import transcribe_audio
from backend.nlp import split_sentences
from backend.subtitle import generate_srt
from backend.utils import load_config

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "output/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def process_audio_task(task_id: str):
    db = SessionLocal()
    task = None
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in background task")
            return

        task.status = TaskStatus.PROCESSING
        task.progress = 0.1
        db.commit()

        # 1. Convert to WAV
        wav_path = convert_to_wav(task.filePath)
        task.progress = 0.3
        db.commit()

        # 2. ASR
        asr_result = transcribe_audio(wav_path)
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

        segments = [
            {
                "text": asr_result["text"],
                "start": 0.0,
                "end": 0.0,  # Will be fixed by NLP
                "tokens": asr_result["tokens"],
                "timestamps": asr_result["timestamps"],
            }
        ]

        # Use timestamp from ASR if available, otherwise use file duration
        last_timestamp = (
            asr_result["timestamps"][-1] if asr_result["timestamps"] else 0.0
        )
        duration = last_timestamp if last_timestamp > 0 else file_duration

        segments[0]["end"] = duration
        task.duration = duration

        refined_segments = split_sentences(segments, config)
        task.progress = 0.9
        db.commit()

        # 4. Generate SRT
        srt_content = generate_srt(refined_segments)

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
        db.close()


@router.post("/upload", response_model=TaskResponse)
async def upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    new_task = Task(
        id=task_id,
        status=TaskStatus.PENDING,
        filename=file.filename,
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
            file_path=task.filePath,
            filename=task.filename,
            duration=task.duration,
            created_at=task.createdAt,
        )
        for task in tasks
    ]


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
