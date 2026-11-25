import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import pymupdf
from sqlalchemy import text

from app.main import app
from app.db.session import init_db, engine, async_session_maker
from app.services.pdf_service import PDFService, EmptyPDFError, InvalidPDFError


def create_sample_pdf_bytes(title: str = "Machine Learning 101", pages: int = 2) -> bytes:
    """Helper to generate an in-memory valid PDF for testing."""
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text(
            (50, 72),
            f"Course Title: {title}\nChapter {i+1}: Foundations of AI\n"
            f"Concept: Gradient Descent and Optimization in Neural Networks.\n"
            f"Page index {i+1} content details."
        )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Ensure database tables exist before each test."""
    await init_db()
    yield


@pytest.mark.asyncio
async def test_health_endpoint():
    """1 & 2: Test FastAPI server starts and health endpoint returns expected response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["application"] == "CourseIllustrate AI"


@pytest.mark.asyncio
async def test_database_tables_created():
    """3 & 4: Verify SQLite database and tables exist."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.fetchall()]
        assert "projects" in tables
        assert "documents" in tables
        assert "generations" in tables


@pytest.mark.asyncio
async def test_valid_pdf_upload_and_extraction():
    """5 & 6: Test upload of a valid PDF and automatic text extraction."""
    pdf_bytes = create_sample_pdf_bytes(title="Data Structures", pages=2)
    files = {
        "file": ("data_structures.pdf", pdf_bytes, "application/pdf")
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "data_structures.pdf"
        assert data["page_count"] == 2
        assert "Data Structures" in data["extracted_text_preview"]
        assert data["total_characters"] > 0
        assert "document_id" in data

        # Verify we can fetch the document detail
        doc_id = data["document_id"]
        get_res = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_res.status_code == 200
        doc_data = get_res.json()
        assert doc_data["id"] == doc_id
        assert "Gradient Descent" in doc_data["extracted_text"]


@pytest.mark.asyncio
async def test_invalid_extension_rejected():
    """7a: Test upload of non-PDF file is rejected."""
    files = {
        "file": ("notes.txt", b"plain text notes", "text/plain")
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        assert "Only PDF documents are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_corrupted_pdf_rejected():
    """7b: Test upload of corrupted/fake PDF file is rejected."""
    files = {
        "file": ("corrupt.pdf", b"This is definitely not a PDF binary header", "application/pdf")
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        assert "corrupted or not a valid PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_empty_pdf_rejected():
    """7c: Test upload of completely empty file is rejected."""
    files = {
        "file": ("empty.pdf", b"", "application/pdf")
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


def test_pdf_service_unit():
    """Unit test for PDFService text extraction directly."""
    # Valid
    pdf_bytes = create_sample_pdf_bytes("Physics 101", pages=1)
    text_content, count = PDFService.extract_text_from_bytes(pdf_bytes)
    assert count == 1
    assert "Physics 101" in text_content

    # Empty
    with pytest.raises(EmptyPDFError):
        PDFService.extract_text_from_bytes(b"")

    # Corrupt
    with pytest.raises(InvalidPDFError):
        PDFService.extract_text_from_bytes(b"corrupted header bytes")
