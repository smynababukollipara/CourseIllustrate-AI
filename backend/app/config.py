from pathlib import Path
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "CourseIllustrate AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./course_illustrate.db"

    # LLM / Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    USE_MOCK_LLM: bool = True  # Automatically defaults to True when GEMINI_API_KEY is not set
    PROVIDER_TIMEOUT_SECONDS: int = 90

    # Image generation. "mock" draws real PNG/SVG/PDF files locally.
    # "huggingface" calls Hugging Face Inference API with HUGGINGFACE_API_TOKEN and HF_IMAGE_MODEL.
    # "stable_diffusion" calls a compatible SD API endpoint.
    IMAGE_PROVIDER: str = "mock"
    HUGGINGFACE_API_TOKEN: Optional[str] = None
    HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"
    STABLE_DIFFUSION_API_URL: Optional[str] = None
    STABLE_DIFFUSION_API_TOKEN: Optional[str] = None
    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash-preview-image-generation"
    IMAGE_SIZE_WIDTH: int = 1024
    IMAGE_SIZE_HEIGHT: int = 1024
    # "structural" scores plan, labels, and file validity.
    # "image_model" additionally requests an image-model review when a key is configured.
    IMAGE_EVALUATION: str = "structural"

    # Quality gate. Score is 0-100. Failed diagrams are repaired up to this many times.
    QUALITY_THRESHOLD: float = 72
    MAX_GENERATION_RETRIES: int = 2

    # Storage paths (relative to backend folder by default)
    UPLOAD_DIR: str = "./storage/uploads"
    GENERATED_DIR: str = "./storage/generated"
    MAX_UPLOAD_SIZE_MB: int = 25

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("IMAGE_PROVIDER", mode="before")
    @classmethod
    def normalize_image_provider(cls, value: str) -> str:
        provider = str(value).strip().lower()
        if provider not in {"mock", "huggingface", "stable_diffusion"}:
            raise ValueError("IMAGE_PROVIDER must be 'mock', 'huggingface', or 'stable_diffusion'.")
        return provider

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.GENERATED_DIR)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def legacy_generated_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "storage" / "generated"


settings = Settings()
