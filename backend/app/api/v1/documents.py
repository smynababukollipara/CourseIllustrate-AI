from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.models import Document, Project
from app.db.session import get_db
from app.schemas.document import DocumentUploadResponse, DocumentResponse
from app.services.pdf_service import (
    PDFService,
    EmptyPDFError,
    InvalidPDFError,
    PDFProcessingError,
    pdf_service
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process PDF document"
)
async def upload_document(
    file: UploadFile = File(..., description="PDF course material to extract text from"),
    project_id: Optional[str] = Form(None, description="Optional project ID to associate with"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a course PDF document, extract text page-by-page using PyMuPDF,
    and persist document metadata and extracted content in the database.
    """
    # 1. Validate file format
    original_filename = file.filename or "uploaded_document.pdf"
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents are supported."
        )

    # 2. Read file content
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(exc)}"
        )

    # 3. Check file size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 4. If project_id provided, verify project exists
    if project_id:
        proj_result = await db.execute(select(Project).where(Project.id == project_id))
        if not proj_result.scalar_one_or_none():
            # If not found, create a placeholder project with this ID or raise 404
            new_proj = Project(id=project_id, title=Path(original_filename).stem, description="Auto-created project")
            db.add(new_proj)
            await db.commit()

    # 5. Extract text via PyMuPDF service
    try:
        extracted_text, page_count = pdf_service.extract_text_from_bytes(content)
    except EmptyPDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except InvalidPDFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except PDFProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF extraction error: {str(exc)}"
        )

    # 6. Save PDF file to storage
    try:
        saved_path = pdf_service.save_upload(content, original_filename)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store PDF file on server: {str(exc)}"
        )

    # 7. Persist document record to SQLite database
    document_record = Document(
        project_id=project_id,
        filename=original_filename,
        extracted_text=extracted_text,
        page_count=page_count
    )
    db.add(document_record)
    await db.commit()
    await db.refresh(document_record)

    # 8. Create preview snippet (first 300 chars)
    preview = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")

    return DocumentUploadResponse(
        document_id=document_record.id,
        project_id=document_record.project_id,
        filename=document_record.filename,
        page_count=document_record.page_count,
        extracted_text_preview=preview,
        total_characters=len(extracted_text),
        message="Document uploaded and parsed successfully."
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details and extracted text"
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full extracted text and metadata for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return document
