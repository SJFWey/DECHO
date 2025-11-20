from sqlalchemy import String, Float, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from server.database import Base
import uuid
from typing import Optional, List
from datetime import datetime


class Task(Base):
    __tablename__ = "Task"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(String, default="pending")
    filename: Mapped[str] = mapped_column(String)
    filePath: Mapped[str] = mapped_column(String)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    lastPlayedChunkIndex: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    recordings: Mapped[List["PracticeRecording"]] = relationship(
        "PracticeRecording", back_populates="task", cascade="all, delete-orphan"
    )


class PracticeRecording(Base):
    __tablename__ = "PracticeRecording"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    taskId: Mapped[str] = mapped_column(
        String, ForeignKey("Task.id", ondelete="CASCADE")
    )
    segmentIndex: Mapped[int] = mapped_column(Integer)
    filePath: Mapped[str] = mapped_column(String)
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship("Task", back_populates="recordings")
