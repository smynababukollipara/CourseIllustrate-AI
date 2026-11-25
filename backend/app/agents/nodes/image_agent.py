import io
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List
import pymupdf

from app.config import settings
from app.agents.state import DiagramAgentState
from app.schemas.generation import ImageGenerationOutput, DiagramNode, DiagramConnection
from app.services.poster_renderer import render_educational_poster_files
from app.services.image_service import (
    ImageProviderError,
    generate_huggingface_image,
    generate_stable_diffusion_image,
    image_provider_configuration,
    validate_and_store_image,
)

logger = logging.getLogger(__name__)


def generate_local_mock_illustration(
    destination_path: Path,
    topic: str,
    style: str,
    concepts: list,
    width: int = 1200,
    height: int = 860
) -> Path:
    """
    Renders a dedicated, styled educational vector/raster illustration locally.
    Includes a clear, unmistakable watermark/badge indicating Mock/Development mode.
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)

    # 1. Dark tech canvas background
    page.draw_rect(pymupdf.Rect(0, 0, width, height), color=(0.04, 0.05, 0.1), fill=(0.04, 0.05, 0.1))

    # 2. Header banner with style indication
    page.draw_rect(pymupdf.Rect(0, 0, width, 120), color=(0.1, 0.12, 0.25), fill=(0.1, 0.12, 0.25))
    page.insert_text(
        (48, 52),
        f"Course Illustration: {topic[:55]}",
        fontsize=24,
        fontname="helv",
        color=(0.95, 0.96, 1.0)
    )
    page.insert_text(
        (48, 86),
        f"Artistic Style: {style.replace('_', ' ').title()}  ·  Educational Concept Art",
        fontsize=13,
        fontname="helv",
        color=(0.65, 0.7, 0.95)
    )

    # Explicit MOCK watermark banner
    page.draw_rect(pymupdf.Rect(width - 360, 30, width - 40, 80), color=(0.8, 0.6, 0.1), fill=(0.2, 0.16, 0.04), width=1.5)
    page.insert_text(
        (width - 345, 54),
        "DEVELOPMENT MOCK ASSET",
        fontsize=11,
        fontname="helv",
        color=(0.98, 0.8, 0.3)
    )
    page.insert_text(
        (width - 345, 70),
        "Configure an image provider in backend environment",
        fontsize=9,
        fontname="helv",
        color=(0.85, 0.75, 0.5)
    )

    # 3. Draw conceptual educational panels
    display_concepts = concepts[:4] if concepts else [
        {"name": "Fundamental Principles", "definition": "Theoretical baseline"},
        {"name": "Operational Execution", "definition": "Core mechanics & processing"},
        {"name": "System Outcomes", "definition": "Verified takeaways & results"}
    ]

    card_w = 240
    card_h = 280
    start_x = 60
    gap_x = 45
    start_y = 190

    for idx, c in enumerate(display_concepts):
        name = getattr(c, "name", str(c.get("name") if isinstance(c, dict) else c))
        definition = getattr(c, "definition", str(c.get("definition") if isinstance(c, dict) else ""))
        cx = start_x + idx * (card_w + gap_x)
        if cx + card_w > width - 40:
            break

        rect = pymupdf.Rect(cx, start_y, cx + card_w, start_y + card_h)
        # Card background & border
        page.draw_rect(rect, color=(0.39, 0.4, 0.95), fill=(0.09, 0.11, 0.22), width=1.5)
        # Top color tab
        page.draw_rect(pymupdf.Rect(cx, start_y, cx + card_w, start_y + 36), color=(0.39, 0.4, 0.95), fill=(0.2, 0.22, 0.45))
        page.insert_text((cx + 12, start_y + 24), f"STAGE 0{idx+1}", fontsize=11, fontname="helv", color=(0.8, 0.85, 1.0))
        # Title
        page.insert_textbox(pymupdf.Rect(cx + 12, start_y + 48, cx + card_w - 12, start_y + 110), name, fontsize=14, fontname="helv", color=(1.0, 1.0, 1.0))
        # Definition
        page.insert_textbox(pymupdf.Rect(cx + 12, start_y + 118, cx + card_w - 12, start_y + card_h - 16), definition[:180], fontsize=10, fontname="helv", color=(0.75, 0.8, 0.92))

        # Arrow connecting to next panel
        if idx < len(display_concepts) - 1 and (cx + card_w + gap_x) < width - 40:
            p1 = (cx + card_w + 6, start_y + card_h // 2)
            p2 = (cx + card_w + gap_x - 6, start_y + card_h // 2)
            page.draw_line(p1, p2, color=(0.58, 0.64, 0.98), width=2.0)

    # 4. Footer info bar
    page.insert_text(
        (48, height - 35),
        "CourseIllustrate AI  ·  Hybrid Vector Diagram & Diffusion Illustration Architecture",
        fontsize=10,
        fontname="helv",
        color=(0.4, 0.45, 0.6)
    )

    pdf_bytes = doc.tobytes()
    doc.close()

    # Convert in-memory vector page to raster PNG without file locks
    raster_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pix = raster_doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
    raster_doc.close()
    pix.save(str(destination_path))

    return destination_path


async def image_generation_node(state: DiagramAgentState) -> Dict[str, Any]:
    """
    Agent 4: Image Generation Agent.
    Generates topic-specific educational illustration via Stable Diffusion / Hugging Face,
    or creates high-quality local development assets in mock mode.
    Also produces vector SVG and PDF renders of the structured diagram.
    """
    logger.info("Executing Image Generation Agent...")
    start_time = time.time()
    agent_status = dict(state.get("agent_status", {}))
    agent_status["image_generation"] = "running"

    gen_id = state.get("generation_id") or uuid.uuid4().hex
    target_dir = settings.generated_path / gen_id
    target_dir.mkdir(parents=True, exist_ok=True)

    topic = state.get("topic") or "Educational Topic"
    style = state.get("illustration_style", "professional_educational")
    concepts = state.get("extracted_concepts") or []
    content = state.get("content_understanding")
    plan = state.get("diagram_plan")
    diagram_type = state.get("diagram_type", "flowchart")
    should_generate_illustration = state.get("generate_illustration", True)

    prompt = state.get("illustration_prompt") or f"Educational illustration explaining {topic}"
    negative_prompt = state.get("negative_prompt") or ""

    # 1. Render Diagram Files (SVG, PNG, PDF) using structured nodes
    nodes = plan.nodes if plan and plan.nodes else [
        DiagramNode(id="node_1", label=topic, description="Subject Overview")
    ]
    connections = plan.connections if plan and plan.connections else []

    diag_svg, diag_png, diag_pdf, d_w, d_h, poster_audit = render_educational_poster_files(
        title=topic,
        diagram_type=diagram_type,
        nodes=nodes,
        connections=connections,
        destination_dir=target_dir,
        summary=(content.summary if content else state.get("educational_summary", "")) or "",
        main_subject=(content.main_subject if content else "") or topic,
        concepts=concepts,
        relationships=(content.relationships if content else state.get("relationships", [])) or [],
        learning_objectives=(content.learning_objectives if content else state.get("learning_objectives", [])) or [],
        key_equations=(content.key_equations if content else []) or [],
        poster_settings=state.get("poster_settings"),
        mock_banner=state.get("is_mock", True),
    )

    # Relative paths for web serving
    svg_rel = f"{gen_id}/{diag_svg.name}"
    png_rel = f"{gen_id}/{diag_png.name}"
    pdf_rel = f"{gen_id}/{diag_pdf.name}"
    svg_url = f"/storage/generated/{svg_rel}"
    poster_url = svg_url
    pdf_url = f"/storage/generated/{pdf_rel}"
    poster_png_url = f"/storage/generated/{png_rel}"

    # 2. Diffusion Illustration Generation
    illustration_path = target_dir / "illustration.png"
    image_rel = f"{gen_id}/illustration.png"
    image_url = f"/storage/generated/{image_rel}"
    image_is_mock = False
    provider_name = None
    image_error = None

    if not should_generate_illustration:
        logger.info("Illustration generation skipped by user preference.")
        agent_status["image_generation"] = "skipped"
        duration_ms = int((time.time() - start_time) * 1000)
        log_entry = {
            "agent": "Image Generation Agent",
            "action": "Skipped illustration generation (diagram-only requested)",
            "poster_rendered": diag_svg.name,
            "poster_layout_valid": poster_audit.valid,
            "pdf_rendered": diag_pdf.name,
            "duration_ms": duration_ms
        }
        logs = list(state.get("execution_logs", []))
        logs.append(log_entry)
        return {
            "svg_path": svg_rel,
            "svg_url": svg_url,
            "poster_url": poster_url,
            "poster_png_url": poster_png_url,
            "pdf_path": pdf_rel,
            "pdf_url": pdf_url,
            "generated_image_path": None,
            "image_url": None,
            "image_provider": None,
            "image_error": None,
            "image_is_mock": False,
            "current_agent": "image_generation",
            "agent_status": agent_status,
            "status": "completed",
            "execution_logs": logs
        }

    # Attempt Real Diffusion Provider if configured
    provider, _, configuration_error = image_provider_configuration()
    image_dimensions = None
    if configuration_error:
        image_error = configuration_error
        logger.info(image_error)
    else:
        try:
            if provider == "mock":
                generate_local_mock_illustration(illustration_path, topic, style, concepts)
                image_dimensions = validate_and_store_image(
                    illustration_path.read_bytes(), illustration_path
                )
                image_is_mock = True
                provider_name = "Local development preview (not Stable Diffusion)"
            else:
                generate_image = (
                    generate_stable_diffusion_image
                    if provider == "stable_diffusion"
                    else generate_huggingface_image
                )
                width, height, provider_name = await generate_image(prompt, negative_prompt, illustration_path)
                image_dimensions = (width, height)
        except (ImageProviderError, OSError, RuntimeError) as exc:
            image_error = str(exc)
            logger.warning("Image generation failed; preserving diagram output: %s", image_error)
        except Exception as exc:
            logger.exception("Unexpected illustration generation error; preserving diagram output.")
            image_error = f"Image generation failed: {exc}"

    image_available = image_dimensions is not None
    if image_available:
        image_rel = f"{gen_id}/illustration.png"
        image_url = f"/storage/generated/{image_rel}"
        agent_status["image_generation"] = "completed"
    else:
        image_rel = None
        image_url = None
        agent_status["image_generation"] = "failed"

    img_output = None
    if image_available:
        img_output = ImageGenerationOutput(
            relative_path=image_rel,
            svg_path=svg_rel,
            pdf_path=pdf_rel,
            image_format="png",
            width=image_dimensions[0],
            height=image_dimensions[1],
            byte_size=illustration_path.stat().st_size,
            is_mock=image_is_mock,
            provider=provider_name or "",
            prompt_used=prompt,
            valid=True,
            attempt=state.get("retry_count", 0) + 1
        )

    duration_ms = int((time.time() - start_time) * 1000)

    log_entry = {
        "agent": "Image Generation Agent",
        "action": (
            f"Generated development preview: style={style}"
            if image_is_mock else
            f"Generated provider illustration: style={style}"
            if image_available else
            f"Image generation failed: {image_error}"
        ),
        "provider": provider_name,
        "is_mock": image_is_mock,
        "image_file": illustration_path.name if image_available else None,
        "svg_file": diag_svg.name,
        "poster_layout_valid": poster_audit.valid,
        "poster_png_url": poster_png_url,
        "pdf_file": diag_pdf.name,
        "duration_ms": duration_ms
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)

    return {
        "generated_image_path": image_rel,
        "image_url": image_url,
        "svg_path": svg_rel,
        "svg_url": svg_url,
        "poster_url": poster_url,
        "poster_png_url": poster_png_url,
        "pdf_path": pdf_rel,
        "pdf_url": pdf_url,
        "image_provider": provider_name,
        "image_error": image_error,
        "image_is_mock": image_is_mock,
        "image_output": img_output,
        "status": "completed",
        "current_agent": "image_generation",
        "agent_status": agent_status,
        "execution_logs": logs
    }
