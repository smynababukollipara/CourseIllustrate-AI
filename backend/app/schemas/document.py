from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    filename: str
    page_count: int
    project_id: Optional[str] = None


class DocumentCreate(DocumentBase):
    extracted_text: str


class DocumentResponse(DocumentBase):
    id: str
    extracted_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document_id: str
    project_id: Optional[str] = None
    filename: str
    page_count: int
    extracted_text_preview: str
    total_characters: int
    message: str = "Document uploaded and parsed successfully."


class HealthResponse(BaseModel):
    status: str
    application: str
