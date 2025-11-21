from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


from datetime import datetime


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: Optional[str] = None
    progress: float = 0.0
    last_played_chunk_index: int = 0
    file_path: Optional[str] = None
    filename: Optional[str] = None
    duration: Optional[float] = None
    created_at: Optional[datetime] = None


class SubtitleSegment(BaseModel):
    start: float
    end: float
    text: str
    translation: Optional[str] = None


class SubtitleResponse(BaseModel):
    task_id: str
    segments: List[SubtitleSegment]


class ASRConfig(BaseModel):
    method: str
    parakeet_model_dir: str
    enable_demucs: bool
    enable_vad: bool


class LLMConfig(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class TTSDefaults(BaseModel):
    language: str
    speed: str
    tone: str


class TTSVoiceMap(BaseModel):
    male: str
    female: str


class TTSConfig(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    defaults: TTSDefaults
    voice_map: TTSVoiceMap


class AppConfig(BaseModel):
    max_split_length: int
    use_llm: bool
    source_language: str
    target_language: str
    spacy_model_map: Dict[str, str]


class AppConfigUpdate(BaseModel):
    max_split_length: Optional[int] = None
    use_llm: Optional[bool] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    spacy_model_map: Optional[Dict[str, str]] = None


class ConfigResponse(BaseModel):
    asr: ASRConfig
    llm: LLMConfig
    tts: TTSConfig
    app: AppConfig


class ConfigUpdate(BaseModel):
    asr: Optional[ASRConfig] = None
    llm: Optional[LLMConfig] = None
    tts: Optional[TTSConfig] = None
    app: Optional[AppConfigUpdate] = None
