import uuid

import pytest
import pymupdf
from httpx import ASGITransport, AsyncClient

from app.agents.nodes.image_agent import image_generation_node
from app.agents.state import DiagramAgentState
from app.config import settings
from app.main import app
from app.schemas.generation import DiagramPlanningOutput
from app.services.image_service import (
    ImageProviderError,
    generate_huggingface_image,
    image_provider_configuration,
    validate_and_store_image,
)


def _png_bytes() -> bytes:
    document = pymupdf.open()
    page = document.new_page(width=64, height=48)
    page.draw_rect((0, 0, 64, 48), color=(0.2, 0.3, 0.7), fill=(0.2, 0.3, 0.7))
    data = page.get_pixmap().tobytes("png")
    document.close()
    return data


def _diagram_plan() -> DiagramPlanningOutput:
    return DiagramPlanningOutput(
        diagram_type="flowchart",
        mermaid_code="flowchart TD\n  A[Core] --> B[Outcome]",
        explanation="Core concept leads to an outcome.",
        node_count=2,
    )


def test_image_provider_configuration_requires_huggingface_credentials(monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "huggingface")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_TOKEN", None)

    provider, model, error = image_provider_configuration()

    assert provider == "huggingface"
    assert model == settings.HF_IMAGE_MODEL
    assert error == "Image generation provider is not configured."


@pytest.mark.asyncio
async def test_huggingface_validates_and_stores_actual_image_response(tmp_path, monkeypatch):
    image_data = _png_bytes()

    class Response:
        status_code = 200
        content = image_data
        text = ""

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, headers, json):
            assert "router.huggingface.co" in url
            assert headers["Authorization"] == "Bearer test-token"
            assert json["inputs"] == "A labeled educational CPU pipeline illustration"
            assert json["parameters"]["negative_prompt"] == "unreadable text"
            return Response()

    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "huggingface")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_TOKEN", "test-token")
    monkeypatch.setattr("app.services.image_service.httpx.AsyncClient", Client)
    target = tmp_path / "provider-image.png"

    width, height, provider = await generate_huggingface_image(
        "A labeled educational CPU pipeline illustration",
        "unreadable text",
        target,
    )

    assert (width, height) == (64, 48)
    assert provider.startswith("Hugging Face Inference")
    assert target.is_file()
    assert target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_huggingface_rejects_non_image_response(tmp_path, monkeypatch):
    class Response:
        status_code = 200
        content = b'{"error":"model unavailable"}' * 8
        text = ""

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "huggingface")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_TOKEN", "test-token")
    monkeypatch.setattr("app.services.image_service.httpx.AsyncClient", Client)
    target = tmp_path / "invalid.png"

    with pytest.raises(ImageProviderError, match="invalid image data"):
        await generate_huggingface_image("valid prompt", "", target)
    assert not target.exists()


def test_validate_and_store_image_creates_valid_accessible_png(tmp_path):
    target = tmp_path / "nested" / "stored.png"

    dimensions = validate_and_store_image(_png_bytes(), target)

    assert dimensions == (64, 48)
    assert target.is_file()
    stored_image = pymupdf.Pixmap(target.read_bytes())
    assert (stored_image.width, stored_image.height) == (64, 48)


@pytest.mark.asyncio
async def test_mock_image_url_is_accessible_from_static_mount(monkeypatch):
    generation_id = f"image-url-test-{uuid.uuid4().hex}"
    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "mock")
    plan = _diagram_plan()
    state: DiagramAgentState = {
        "generation_id": generation_id,
        "topic": "CPU pipeline",
        "diagram_type": "flowchart",
        "diagram_plan": plan,
        "generate_illustration": True,
        "is_mock": True,
        "execution_logs": [],
    }

    try:
        result = await image_generation_node(state)
        assert result["image_is_mock"] is True
        assert result["image_provider"] == "Local development preview (not Stable Diffusion)"
        assert result["image_url"] == f"/storage/generated/{generation_id}/illustration.png"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(result["image_url"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        import shutil
        shutil.rmtree(settings.generated_path / generation_id, ignore_errors=True)


@pytest.mark.asyncio
async def test_missing_credentials_fail_image_only_and_preserve_diagram(monkeypatch):
    generation_id = f"image-config-test-{uuid.uuid4().hex}"
    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "huggingface")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_TOKEN", None)
    state: DiagramAgentState = {
        "generation_id": generation_id,
        "topic": "CPU pipeline",
        "diagram_type": "flowchart",
        "diagram_plan": _diagram_plan(),
        "generate_illustration": True,
        "execution_logs": [],
    }

    try:
        result = await image_generation_node(state)
        assert result["agent_status"]["image_generation"] == "failed"
        assert result["image_error"] == "Image generation provider is not configured."
        assert result["image_url"] is None
        assert result["svg_url"] is not None
        assert result["pdf_url"] is not None
        assert not (settings.generated_path / generation_id / "illustration.png").exists()
    finally:
        import shutil
        shutil.rmtree(settings.generated_path / generation_id, ignore_errors=True)


@pytest.mark.asyncio
async def test_provider_failure_does_not_remove_diagram(monkeypatch):
    generation_id = f"image-error-test-{uuid.uuid4().hex}"

    async def fail_provider(*_args, **_kwargs):
        raise ImageProviderError("Hugging Face image request failed (HTTP 503): model unavailable")

    monkeypatch.setattr(settings, "IMAGE_PROVIDER", "huggingface")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_TOKEN", "test-token")
    monkeypatch.setattr("app.agents.nodes.image_agent.generate_huggingface_image", fail_provider)
    state: DiagramAgentState = {
        "generation_id": generation_id,
        "topic": "CPU pipeline",
        "diagram_type": "flowchart",
        "diagram_plan": _diagram_plan(),
        "generate_illustration": True,
        "execution_logs": [],
    }

    try:
        result = await image_generation_node(state)
        assert result["agent_status"]["image_generation"] == "failed"
        assert "HTTP 503" in result["image_error"]
        assert result["image_url"] is None
        assert (settings.generated_path / generation_id / "poster.svg").is_file()
    finally:
        import shutil
        shutil.rmtree(settings.generated_path / generation_id, ignore_errors=True)
