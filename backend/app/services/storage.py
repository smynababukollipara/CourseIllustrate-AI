"""Safe path helpers for uploaded and generated files."""
from pathlib import Path
from fastapi import HTTPException, status
from app.config import settings


def resolve_under(base: Path, stored: str) -> Path:
    """Resolve a stored relative or absolute path and reject traversal."""
    if not stored or not str(stored).strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not available.")
    root = base.resolve()
    raw = Path(stored)
    candidate = raw.resolve() if raw.is_absolute() else (root / stored).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
    return candidate


def resolve_generated(stored: str) -> Path:
    try:
        path = resolve_under(settings.generated_path, stored)
        if path.is_file():
            return path
    except HTTPException:
        pass
    legacy_root = settings.legacy_generated_path.resolve()
    raw = Path(stored)
    legacy_path = raw.resolve() if raw.is_absolute() else (legacy_root / stored).resolve()
    if legacy_path == legacy_root or legacy_root not in legacy_path.parents or not legacy_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated file was not found.")
    return legacy_path


def generated_asset_url(stored: str) -> str:
    """Return a static URL for a file in current or legacy generated storage."""
    path = resolve_generated(stored)
    current_root = settings.generated_path.resolve()
    if path == current_root or current_root in path.parents:
        relative = path.relative_to(current_root)
        return f"/storage/generated/{relative.as_posix()}"
    legacy_relative = path.relative_to(settings.legacy_generated_path.resolve())
    return f"/storage/legacy-generated/{legacy_relative.as_posix()}"


def resolve_upload(stored: str) -> Path:
    path = resolve_under(settings.upload_path, stored)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded file was not found.")
    return path
