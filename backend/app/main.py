import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.session import init_db
from app.api.v1.router import api_v1_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    logger.info("Initializing %s...", settings.APP_NAME)
    # Ensure storage directories exist
    settings.upload_path
    settings.generated_path
    # Initialize SQLite tables
    await init_db()
    logger.info("Database tables verified and initialized successfully.")
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for CourseIllustrate AI - Online Course Diagram & Illustration Generator",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Input validation error."}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error processing request %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An unexpected internal server error occurred."}
    )


# Health Check Endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "healthy",
        "application": "CourseIllustrate AI"
    }


# Register API v1 Routers under /api
app.include_router(api_v1_router, prefix="/api")

# Static file serving for generated diagram images and uploaded PDFs
app.mount("/storage/generated", StaticFiles(directory=str(settings.generated_path)), name="generated")
app.mount("/storage/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")
if settings.legacy_generated_path.is_dir():
    app.mount(
        "/storage/legacy-generated",
        StaticFiles(directory=str(settings.legacy_generated_path)),
        name="legacy-generated",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
