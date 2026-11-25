"""Provider-backed educational image generation and image validation."""
import logging
import base64
import binascii
from pathlib import Path
from typing import Tuple

import httpx
import pymupdf

from app.config import settings

logger = logging.getLogger(__name__)


class ImageProviderError(RuntimeError):
    """Raised when an image provider is not configured or returns an invalid response."""


def image_provider_configuration() -> Tuple[str, str, str]:
    """Return provider, model, and a user-displayable configuration error, if any."""
    provider = settings.IMAGE_PROVIDER.strip().lower()
    model = settings.HF_IMAGE_MODEL.strip()
    if provider == "mock":
        return provider, "Local development preview", ""
    if provider == "huggingface" and settings.HUGGINGFACE_API_TOKEN and settings.HUGGINGFACE_API_TOKEN.strip():
        return provider, model, ""
    if provider == "huggingface":
        return provider, model, "Image generation provider is not configured."
    if provider == "stable_diffusion" and settings.STABLE_DIFFUSION_API_URL:
        return provider, settings.STABLE_DIFFUSION_API_URL, ""
    if provider == "stable_diffusion":
        return provider, "", "Image generation provider is not configured."
    return provider, model, "Image generation provider is not configured."


def validate_and_store_image(image_data: bytes, destination_path: Path) -> Tuple[int, int]:
    """Validate raster bytes, normalize them to PNG, and atomically store the image."""
    if not image_data or len(image_data) < 8:
        raise ImageProviderError("Image provider returned an empty or incomplete image.")
    try:
        pixmap = pymupdf.Pixmap(image_data)
        if pixmap.width < 1 or pixmap.height < 1:
            raise ValueError("Image dimensions are empty.")
        if pixmap.alpha or pixmap.n > 3:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        png_data = pixmap.tobytes("png")
        checked = pymupdf.Pixmap(png_data)
    except Exception as exc:
        raise ImageProviderError("Image provider returned invalid image data.") from exc

    if not png_data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ImageProviderError("Image provider response could not be encoded as PNG.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination_path.with_suffix(destination_path.suffix + ".tmp")
    try:
        temporary_path.write_bytes(png_data)
        temporary_path.replace(destination_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return checked.width, checked.height


async def generate_huggingface_image(
    prompt: str,
    negative_prompt: str,
    destination_path: Path,
) -> Tuple[int, int, str]:
    """Call the Hugging Face Inference Router and store its validated image response."""
    provider, model, configuration_error = image_provider_configuration()
    if configuration_error:
        raise ImageProviderError(configuration_error)
    if provider != "huggingface":
        raise ImageProviderError("Hugging Face image generation is not the selected provider.")

    token = settings.HUGGINGFACE_API_TOKEN
    endpoint = f"https://router.huggingface.co/hf-inference/models/{model}"
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "width": settings.IMAGE_SIZE_WIDTH,
            "height": settings.IMAGE_SIZE_HEIGHT,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {token.strip()}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise ImageProviderError("Hugging Face image generation timed out.") from exc
    except httpx.HTTPError as exc:
        logger.warning("Hugging Face image request failed: %s", exc)
        raise ImageProviderError(f"Hugging Face image request failed: {exc}") from exc

    if response.status_code != 200:
        detail = response.text[:300].strip()
        raise ImageProviderError(
            f"Hugging Face image request failed (HTTP {response.status_code})"
            + (f": {detail}" if detail else ".")
        )

    width, height = validate_and_store_image(response.content, destination_path)
    return width, height, f"Hugging Face Inference ({model})"


async def generate_stable_diffusion_image(
    prompt: str,
    negative_prompt: str,
    destination_path: Path,
) -> Tuple[int, int, str]:
    """Call a Stable Diffusion WebUI-compatible txt2img endpoint."""
    provider, endpoint, configuration_error = image_provider_configuration()
    if configuration_error:
        raise ImageProviderError(configuration_error)
    if provider != "stable_diffusion":
        raise ImageProviderError("Stable Diffusion is not the selected image provider.")

    headers = {"Content-Type": "application/json"}
    if settings.STABLE_DIFFUSION_API_TOKEN and settings.STABLE_DIFFUSION_API_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.STABLE_DIFFUSION_API_TOKEN.strip()}"
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": settings.IMAGE_SIZE_WIDTH,
        "height": settings.IMAGE_SIZE_HEIGHT,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise ImageProviderError("Stable Diffusion image generation timed out.") from exc
    except httpx.HTTPError as exc:
        logger.warning("Stable Diffusion image request failed: %s", exc)
        raise ImageProviderError(f"Stable Diffusion image request failed: {exc}") from exc

    if response.status_code != 200:
        detail = response.text[:300].strip()
        raise ImageProviderError(
            f"Stable Diffusion image request failed (HTTP {response.status_code})"
            + (f": {detail}" if detail else ".")
        )
    try:
        images = response.json().get("images") or []
        if not images:
            raise ValueError("No image data returned.")
        image_data = base64.b64decode(images[0], validate=True)
    except (ValueError, TypeError, AttributeError, binascii.Error) as exc:
        raise ImageProviderError("Stable Diffusion provider returned invalid image data.") from exc

    width, height = validate_and_store_image(image_data, destination_path)
    return width, height, "Stable Diffusion WebUI-compatible API"
