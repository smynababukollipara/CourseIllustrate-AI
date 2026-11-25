# CourseIllustrate AI: Online Course Diagram & Illustration Generator

> **Phase 1: Project Foundation Complete** &mdash; An AI-powered full-stack web application that transforms lecture notes, educational descriptions, and uploaded course PDFs into structured diagrams and AI-generated illustrations.

---

## Tech Stack Overview

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Axios, React Router.
- **Backend**: Python 3.12+, FastAPI, Uvicorn.
- **Database**: SQLite with SQLAlchemy 2.0 and `aiosqlite`.
- **PDF Extraction**: PyMuPDF (`pymupdf`).
- **AI Agent Framework (Phase 2)**: LangGraph (Content Understanding, Diagram Planning, Prompt Engineering, Image Generation, Quality Evaluation).
- **LLM & Diffusion**: Google Gemini API & Hugging Face / Stable Diffusion.

---

## Project Structure

```
CourseIllustrate-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── documents.py        # PDF upload, validation & retrieval
│   │   │       └── router.py           # v1 master router
│   │   ├── db/
│   │   │   ├── models.py               # Project, Document, Generation ORM
│   │   │   └── session.py              # SQLite session & table init
│   │   ├── schemas/
│   │   │   └── document.py             # Pydantic validation schemas
│   │   ├── services/
│   │   │   └── pdf_service.py          # PyMuPDF extraction engine
│   │   ├── config.py                   # Pydantic Settings & environment config
│   │   └── main.py                     # FastAPI entrypoint, CORS & health checks
│   ├── storage/
│   │   ├── uploads/                    # Persisted uploaded course PDFs
│   │   └── generated/                  # Output illustrations & exports
│   ├── tests/
│   │   └── test_api.py                 # Pytest test suite (health, DB, PDF)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Navbar.jsx              # App header with live backend status
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx       # Overview & architecture stats
│   │   │   └── StudioPage.jsx          # Interactive PDF upload & text preview
│   │   ├── services/
│   │   │   └── api.js                  # Axios client & API methods
│   │   ├── App.jsx
│   │   ├── index.css                   # Tailwind styles
│   │   └── main.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── .env.example
│
├── docs/                               # Architectural & API specifications
├── pytest.ini
├── README.md
└── .gitignore
```

---

## Getting Started & Installation

### Prerequisites
- Python 3.12+
- Node.js v18+ (tested on Node v22)

---

### Backend Setup

1. **Navigate to the backend directory and activate the virtual environment**:
   ```bash
   # From project root
   python -m venv venv
   
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   # macOS / Linux
   source venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment Variables** (optional):
   Image generation defaults to a clearly labeled local development preview. To use
   Hugging Face Inference, set these values in `backend/.env`:
   ```env
   IMAGE_PROVIDER=huggingface
   HUGGINGFACE_API_TOKEN=your_hugging_face_token
   HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
   ```
   Or use a Stable Diffusion WebUI-compatible `txt2img` API:
   ```env
   IMAGE_PROVIDER=stable_diffusion
   STABLE_DIFFUSION_API_URL=http://localhost:7860/sdapi/v1/txt2img
   # Optional when the endpoint requires bearer authentication:
   STABLE_DIFFUSION_API_TOKEN=your_provider_token
   ```
   Credentials are read only by the backend. The application does not download
   models; inference is submitted to the configured remote/provider endpoint.
   When a real provider is selected but not configured, illustration generation
   reports that it is unavailable while preserving the generated diagram.

4. **Run the FastAPI server**:
   ```bash
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
   The backend API will be live at: `http://localhost:8000`  
   Interactive Swagger docs: `http://localhost:8000/docs`

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the Vite development server**:
   ```bash
   npm run dev
   ```
   The frontend will be live at: `http://localhost:5173`

---

## API Endpoints (Phase 1)

### Health Check
- **`GET /api/health`**
  - Response:
    ```json
    {
      "status": "healthy",
      "application": "CourseIllustrate AI"
    }
    ```

### Document Ingestion & PyMuPDF Extraction
- **`POST /api/v1/documents/upload`**
  - **Payload**: `multipart/form-data` with `file: <PDF>` and optional `project_id: string`.
  - **Validation**: Rejects non-PDFs (400), empty files (400), corrupted PDFs (400), files > 25MB (413).
  - **Response**:
    ```json
    {
      "document_id": "90e29b4e-e170-449e-b91c-7f51ecae1dc3",
      "project_id": null,
      "filename": "lecture_01.pdf",
      "page_count": 5,
      "extracted_text_preview": "--- Page 1 ---\nCourse Title: Machine Learning...",
      "total_characters": 8420,
      "message": "Document uploaded and parsed successfully."
    }
    ```

- **`GET /api/v1/documents/{document_id}`**
  - Retrieves full extracted text and metadata for a previously uploaded document.

---

## Running the Automated Test Suite

Run the full pytest suite for the backend:
```bash
$env:PYTHONPATH="backend"
pytest backend/tests -v
```

All 7 test suites verify:
1. Server operational readiness & health check endpoint.
2. SQLite database creation and schema integrity (`projects`, `documents`, `generations`).
3. Valid PDF uploads, disk persistence, and text extraction accuracy.
4. Error handling for non-PDF extensions, corrupted headers, and empty files.
5. Direct PyMuPDF unit extraction.
