import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    generations: Mapped[List["Generation"]] = relationship("Generation", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationship
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="documents")


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    diagram_type: Mapped[str] = mapped_column(String(64), nullable=False, default="flowchart")
    diagram_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    svg_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_format: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    illustration_style: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    poster_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluation_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_mock: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    image_is_mock: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    image_provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_focus: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    execution_logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationship
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="generations")
