import io
import uuid
import logging
from pathlib import Path
from typing import Tuple, Union
import pymupdf
from app.config import settings

logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception raised when PDF processing fails."""
    pass


class EmptyPDFError(PDFProcessingError):
    """Raised when PDF contains zero pages or no text."""
    pass


class InvalidPDFError(PDFProcessingError):
    """Raised when file is not a valid PDF or is corrupted."""
    pass


class PDFService:
    """Service for extracting text and processing PDF course materials using PyMuPDF."""

    @staticmethod
    def extract_text_from_bytes(pdf_bytes: bytes) -> Tuple[str, int]:
        """
        Extract text page by page from raw PDF bytes.

        Args:
            pdf_bytes: Raw bytes of the PDF file.

        Returns:
            Tuple of (extracted_text, page_count)

        Raises:
            EmptyPDFError: If file is empty or has 0 pages.
            InvalidPDFError: If file is corrupted or not a valid PDF.
            PDFProcessingError: For unexpected extraction failures.
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise EmptyPDFError("The uploaded file is empty.")

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except pymupdf.FileDataError as exc:
            logger.error("Invalid or corrupted PDF file: %s", exc)
            raise InvalidPDFError("The provided file is corrupted or not a valid PDF document.") from exc
        except Exception as exc:
            logger.error("Failed to open PDF stream: %s", exc)
            raise InvalidPDFError(f"Failed to read PDF document: {str(exc)}") from exc

        try:
            page_count = doc.page_count
            if page_count == 0:
                raise EmptyPDFError("The PDF document contains 0 pages.")

            extracted_pages = []
            for page_index in range(page_count):
                page = doc.load_page(page_index)
                page_text = page.get_text("text").strip()
                if page_text:
                    extracted_pages.append(f"--- Page {page_index + 1} ---\n{page_text}")
                else:
                    extracted_pages.append(f"--- Page {page_index + 1} ---\n[Empty page]")

            full_text = "\n\n".join(extracted_pages).strip()
            return full_text, page_count

        except (EmptyPDFError, InvalidPDFError):
            raise
        except Exception as exc:
            logger.error("Error extracting text from PDF: %s", exc)
            raise PDFProcessingError(f"Error occurred during text extraction: {str(exc)}") from exc
        finally:
            doc.close()

    @staticmethod
    def extract_text_from_file(file_path: Union[str, Path]) -> Tuple[str, int]:
        """Extract text from a saved PDF file path."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        try:
            with open(path, "rb") as f:
                content = f.read()
            return PDFService.extract_text_from_bytes(content)
        except (EmptyPDFError, InvalidPDFError, PDFProcessingError, FileNotFoundError):
            raise
        except Exception as exc:
            raise PDFProcessingError(f"Failed to read file from disk: {str(exc)}") from exc

    @staticmethod
    def save_upload(file_bytes: bytes, original_filename: str) -> Path:
        """
        Save uploaded PDF bytes to the configured upload storage directory.
        Generates a unique filename to avoid collisions.
        """
        upload_dir = settings.upload_path
        file_extension = Path(original_filename).suffix or ".pdf"
        safe_name = f"{uuid.uuid4().hex}_{Path(original_filename).stem}{file_extension}"
        destination = upload_dir / safe_name

        with open(destination, "wb") as f:
            f.write(file_bytes)

        return destination


pdf_service = PDFService()
