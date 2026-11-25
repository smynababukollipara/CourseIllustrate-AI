import time
import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete

from app.config import settings
from app.db.models import Document, Generation, Project
from app.db.session import get_db
from app.schemas.generation import (
    DiagramGenerationRequest,
    DiagramGenerationResponse,
    GenerationDetail,
    GenerationSummary,
    ConceptItem,
    QualityEvaluationOutput,
    PosterDesignSettings
)
from app.agents.graph import diagram_graph
from app.agents.state import DiagramAgentState
from app.services.diagram_render import build_course_export_pdf
from app.services.mermaid import normalize_mermaid_source
from app.services.storage import generated_asset_url, resolve_generated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generations", tags=["Generations"])


@router.post(
    "/diagram",
    response_model=DiagramGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate educational diagram and illustration using LangGraph multi-agent pipeline"
)
@router.post(
    "/start",
    response_model=DiagramGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Start educational generation workflow"
)
async def generate_diagram(
    payload: DiagramGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Coordinates all five specialized agents via LangGraph:
    1. Content Understanding Agent
    2. Diagram Planning Agent
    3. Quality Evaluation Agent (with conditional repair loop)
    4. Prompt Engineering Agent
    5. Image Generation Agent (Stable Diffusion / Hugging Face / Mock)
    """
    start_time = time.time()
    raw_content = ""
    source_type = "text"
    project_id = payload.project_id

    # 1. Resolve raw educational content
    if payload.document_id:
        doc_result = await db.execute(select(Document).where(Document.id == payload.document_id))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{payload.document_id}' not found."
            )
        raw_content = doc.extracted_text
        source_type = "pdf"
        project_id = project_id or doc.project_id
        if payload.topic and payload.topic.strip():
            raw_content = f"Educational topic: {payload.topic.strip()}\n\n{raw_content}"
    elif (payload.text_input and payload.text_input.strip()) or (payload.topic and payload.topic.strip()):
        raw_content = (payload.text_input or "").strip()
        if payload.topic and payload.topic.strip():
            raw_content = (
                f"Educational topic: {payload.topic.strip()}\n\n{raw_content}"
                if raw_content
                else f"Educational topic: {payload.topic.strip()}"
            )
        source_type = "text"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text_input' or 'document_id' must be provided."
        )

    # 2. Prepare initial LangGraph state
    gen_id = str(uuid.uuid4())
    initial_agent_status = {
        "content_understanding": "pending",
        "diagram_planning": "pending",
        "quality_evaluation": "pending",
        "prompt_engineering": "pending",
        "image_generation": "pending"
    }

    initial_state: DiagramAgentState = {
        "generation_id": gen_id,
        "raw_content": raw_content,
        "source_type": source_type,  # type: ignore
        "project_id": project_id,
        "document_id": payload.document_id,
        "requested_diagram_type": payload.diagram_type or "flowchart",
        "custom_focus": payload.custom_focus,
        "illustration_style": payload.illustration_style or "professional_educational",
        "complexity_level": payload.complexity_level or "intermediate",
        "generate_illustration": payload.generate_illustration,
        "poster_settings": payload.poster_settings,
        "retry_count": 0,
        "content_understanding": None,
        "diagram_plan": None,
        "quality_output": None,
        "prompt_output": None,
        "image_output": None,
        "status": "initiating",
        "current_agent": "content_understanding",
        "agent_status": initial_agent_status,
        "error": None,
        "errors": [],
        "is_mock": False,
        "provider": "",
        "execution_logs": []
    }

    # 3. Execute LangGraph 5-agent state machine
    try:
        final_state = await diagram_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("LangGraph execution failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent execution failure: {str(exc)}"
        )

    if final_state.get("error") and not final_state.get("diagram_plan"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=final_state.get("error", "Failed to generate diagram plan.")
        )

    content_out = final_state.get("content_understanding")
    diagram_out = final_state.get("diagram_plan")
    quality_out = final_state.get("quality_output")
    total_time_ms = int((time.time() - start_time) * 1000)

    # 4. Prepare serialized JSON fields for DB persistence
    content_json_str = content_out.model_dump_json() if content_out else None
    plan_json_str = diagram_out.model_dump_json() if diagram_out else None
    quality_json_str = quality_out.model_dump_json() if quality_out else None
    execution_logs_str = json.dumps(final_state.get("execution_logs", []))
    agent_status_str = json.dumps(final_state.get("agent_status", {}))

    # 5. Persist to SQLite generations table
    generation_record = Generation(
        id=gen_id,
        project_id=project_id,
        document_id=payload.document_id,
        topic=final_state.get("topic") or (content_out.title if content_out else "Educational Diagram"),
        diagram_type=final_state.get("diagram_type") or (diagram_out.diagram_type if diagram_out else "flowchart"),
        diagram_code=normalize_mermaid_source(
            final_state.get("mermaid_code") or (diagram_out.mermaid_code if diagram_out else "")
        ),
        image_path=final_state.get("generated_image_path"),
        svg_path=final_state.get("svg_path"),
        pdf_path=final_state.get("pdf_path"),
        summary=final_state.get("educational_summary") or (content_out.summary if content_out else ""),
        content_json=content_json_str,
        plan_json=plan_json_str,
        prompt_text=final_state.get("illustration_prompt"),
        negative_prompt=final_state.get("negative_prompt"),
        illustration_style=payload.illustration_style,
        poster_settings=payload.poster_settings.model_dump_json(),
        quality_json=quality_json_str,
        quality_score=final_state.get("evaluation_score"),
        evaluation_method="structural",
        provider=final_state.get("provider") or "CourseIllustrate AI Multi-Agent",
        is_mock=final_state.get("is_mock", True),
        image_is_mock=final_state.get("image_is_mock", True),
        image_provider=final_state.get("image_provider"),
        image_error=final_state.get("image_error"),
        image_format=final_state.get("image_output").image_format if final_state.get("image_output") else None,
        image_width=final_state.get("image_output").width if final_state.get("image_output") else None,
        image_height=final_state.get("image_output").height if final_state.get("image_output") else None,
        retry_count=final_state.get("retry_count", 0),
        source_text=raw_content[:2000],
        custom_focus=payload.custom_focus,
        agent_status=agent_status_str,
        execution_logs=execution_logs_str,
        status="completed"
    )
    db.add(generation_record)
    await db.commit()
    await db.refresh(generation_record)

    concepts = content_out.key_concepts if content_out else []

    return DiagramGenerationResponse(
        generation_id=generation_record.id,
        project_id=generation_record.project_id,
        topic=generation_record.topic,
        diagram_type=generation_record.diagram_type,
        mermaid_code=normalize_mermaid_source(generation_record.diagram_code or ""),
        summary=generation_record.summary or "",
        concepts=concepts,
        is_mock=generation_record.is_mock or False,
        provider=generation_record.provider or "MockLLMProvider",
        execution_time_ms=total_time_ms,
        created_at=generation_record.created_at,
        status=generation_record.status,
        quality_score=generation_record.quality_score,
        quality_passed=quality_out.passed if quality_out else True,
        evaluation_method=generation_record.evaluation_method,
        quality=quality_out,
        image_url=final_state.get("image_url"),
        poster_url=final_state.get("poster_url"),
        svg_url=final_state.get("svg_url"),
        pdf_url=final_state.get("pdf_url"),
        image_is_mock=generation_record.image_is_mock,
        image_provider=generation_record.image_provider,
        image_error=generation_record.image_error,
        image_format=generation_record.image_format,
        image_width=generation_record.image_width,
        image_height=generation_record.image_height,
        retry_count=generation_record.retry_count,
        execution_logs=final_state.get("execution_logs", []),
        prompt=generation_record.prompt_text,
        negative_prompt=generation_record.negative_prompt,
        illustration_style=generation_record.illustration_style,
        poster_settings=(
            PosterDesignSettings.model_validate_json(generation_record.poster_settings)
            if generation_record.poster_settings else PosterDesignSettings()
        ),
        agent_status=final_state.get("agent_status")
    )


@router.get(
    "",
    response_model=List[GenerationSummary],
    summary="List all generations with optional search filter"
)
async def list_generations(
    search: Optional[str] = Query(None, description="Search term for topic"),
    diagram_type: Optional[str] = Query(None, description="Filter by diagram type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List stored generations ordered by creation date descending."""
    query = select(Generation).order_by(desc(Generation.created_at))

    if search and search.strip():
        query = query.where(Generation.topic.ilike(f"%{search.strip()}%"))
    if diagram_type and diagram_type.strip():
        query = query.where(Generation.diagram_type == diagram_type.strip().lower())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    generations = result.scalars().all()

    summaries = []
    for g in generations:
        img_url = None
        if g.image_path:
            try:
                resolve_generated(g.image_path)
                img_url = generated_asset_url(g.image_path)
            except HTTPException:
                logger.info("Stored image is unavailable for generation %s", g.id)
        thumbnail_url = None
        diagram_dir = settings.generated_path / g.id
        if not diagram_dir.is_dir():
            diagram_dir = settings.legacy_generated_path / g.id
        diagram_pngs = sorted(diagram_dir.glob("diagram*.png"))
        if diagram_pngs:
            try:
                thumbnail_url = generated_asset_url(str(diagram_pngs[0]))
            except HTTPException:
                logger.info("Diagram thumbnail is unavailable for generation %s", g.id)
        summaries.append(
            GenerationSummary(
                id=g.id,
                project_id=g.project_id,
                document_id=g.document_id,
                topic=g.topic,
                diagram_type=g.diagram_type,
                status=g.status,
                quality_score=g.quality_score,
                is_mock=g.is_mock,
                image_is_mock=g.image_is_mock,
                created_at=g.created_at,
                image_url=img_url,
                thumbnail_url=img_url or thumbnail_url
            )
        )
    return summaries


@router.get(
    "/stats/summary",
    summary="Get aggregated generation statistics for Dashboard"
)
async def get_generation_stats(db: AsyncSession = Depends(get_db)):
    """Computes database-backed statistics: total generations, illustrations, and average quality."""
    total_gen = await db.scalar(select(func.count(Generation.id))) or 0
    total_illus = await db.scalar(
        select(func.count(Generation.id)).where(Generation.image_path.isnot(None))
    ) or 0
    total_docs = await db.scalar(select(func.count(Document.id))) or 0
    avg_score = await db.scalar(
        select(func.avg(Generation.quality_score)).where(Generation.quality_score.isnot(None))
    ) or 0.0

    # Recent 5 items
    recent_result = await db.execute(
        select(Generation).order_by(desc(Generation.created_at)).limit(5)
    )
    recent = [
        {
            "id": g.id,
            "topic": g.topic,
            "diagram_type": g.diagram_type,
            "quality_score": g.quality_score,
            "created_at": g.created_at.isoformat(),
            "has_illustration": bool(g.image_path)
        }
        for g in recent_result.scalars().all()
    ]

    return {
        "total_generations": total_gen,
        "total_illustrations": total_illus,
        "total_documents": total_docs,
        "average_quality_score": round(float(avg_score), 1),
        "recent_generations": recent
    }


@router.get(
    "/{generation_id}",
    response_model=GenerationDetail,
    summary="Get saved generation details by ID"
)
async def get_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve an existing generated diagram from SQLite."""
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation with ID '{generation_id}' not found."
        )

    # Parse JSON fields
    quality_obj = None
    if generation.quality_json:
        try:
            quality_obj = QualityEvaluationOutput.model_validate_json(generation.quality_json)
        except Exception:
            pass

    content_dict = None
    if generation.content_json:
        try:
            content_dict = json.loads(generation.content_json)
        except Exception:
            pass

    plan_dict = None
    if generation.plan_json:
        try:
            plan_dict = json.loads(generation.plan_json)
        except Exception:
            pass

    logs_list = []
    if generation.execution_logs:
        try:
            logs_list = json.loads(generation.execution_logs)
        except Exception:
            pass

    agent_status_dict = {}
    if generation.agent_status:
        try:
            agent_status_dict = json.loads(generation.agent_status)
        except Exception:
            pass

    # Construct public URL helpers
    image_url = None
    if generation.image_path:
        try:
            resolve_generated(generation.image_path)
            image_url = generated_asset_url(generation.image_path)
        except HTTPException:
            logger.info("Stored image is unavailable for generation %s", generation.id)

    try:
        svg_url = generated_asset_url(generation.svg_path) if generation.svg_path else None
    except HTTPException:
        svg_url = None
    poster_url = svg_url
    try:
        pdf_url = generated_asset_url(generation.pdf_path) if generation.pdf_path else None
    except HTTPException:
        pdf_url = None

    return GenerationDetail(
        id=generation.id,
        project_id=generation.project_id,
        document_id=generation.document_id,
        topic=generation.topic,
        diagram_type=generation.diagram_type,
        diagram_code=normalize_mermaid_source(generation.diagram_code or ""),
        status=generation.status,
        summary=generation.summary,
        quality_score=generation.quality_score,
        evaluation_method=generation.evaluation_method,
        provider=generation.provider,
        is_mock=generation.is_mock,
        image_is_mock=generation.image_is_mock,
        image_provider=generation.image_provider,
        image_error=generation.image_error,
        image_format=generation.image_format or "png",
        image_width=generation.image_width,
        image_height=generation.image_height,
        retry_count=generation.retry_count,
        error_message=generation.error_message,
        custom_focus=generation.custom_focus,
        prompt_text=generation.prompt_text,
        negative_prompt=generation.negative_prompt,
        illustration_style=generation.illustration_style,
        agent_status=agent_status_dict,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
        image_url=image_url,
        poster_url=poster_url,
        svg_url=svg_url,
        pdf_url=pdf_url,
        quality=quality_obj,
        execution_logs=logs_list,
        content=content_dict,
        plan=plan_dict,
        concepts=(content_dict or {}).get("key_concepts", []),
        poster_settings=(
            PosterDesignSettings.model_validate_json(generation.poster_settings)
            if generation.poster_settings else PosterDesignSettings()
        ),
        generate_illustration=bool(generation.image_path or generation.image_error)
    )


@router.get(
    "/{generation_id}/status",
    summary="Get execution status and agent logs of a generation"
)
async def get_generation_status(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check agent progress, current agent node, and execution logs."""
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation with ID '{generation_id}' not found."
        )

    logs = []
    if generation.execution_logs:
        try:
            logs = json.loads(generation.execution_logs)
        except Exception:
            pass

    agent_status = {}
    if generation.agent_status:
        try:
            agent_status = json.loads(generation.agent_status)
        except Exception:
            pass

    return {
        "id": generation.id,
        "status": generation.status,
        "topic": generation.topic,
        "quality_score": generation.quality_score,
        "retry_count": generation.retry_count,
        "agent_status": agent_status,
        "execution_logs": logs,
        "error_message": generation.error_message
    }


@router.delete(
    "/{generation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a generation and remove its files"
)
async def delete_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Deletes generation record from database and cleans up generated assets."""
    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation with ID '{generation_id}' not found."
        )

    # Clean local disk directory if exists
    import shutil
    for gen_dir in (
        settings.generated_path / generation_id,
        settings.legacy_generated_path / generation_id,
    ):
        if gen_dir.exists() and gen_dir.is_dir():
            shutil.rmtree(gen_dir, ignore_errors=True)

    await db.delete(generation)
    await db.commit()

    return {"message": f"Generation '{generation_id}' deleted successfully.", "id": generation_id}


@router.get(
    "/{generation_id}/export/{format_type}",
    summary="Export generated visual as SVG, PNG, or complete Course PDF"
)
async def export_generation(
    generation_id: str,
    format_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Downloads diagram / illustration in the requested format:
    - svg: raw vector SVG diagram
    - png: rasterized PNG diagram / illustration
    - pdf: complete multi-page educational study PDF
    """
    fmt = format_type.lower()
    if fmt not in ("svg", "png", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format_type}'. Supported: 'svg', 'png', 'pdf'."
        )

    result = await db.execute(select(Generation).where(Generation.id == generation_id))
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation with ID '{generation_id}' not found."
        )

    gen_dir = settings.generated_path / generation_id
    if not gen_dir.is_dir():
        gen_dir = settings.legacy_generated_path / generation_id

    # 1. SVG Export
    if fmt == "svg":
        candidates = [gen_dir / "poster.svg"] if (gen_dir / "poster.svg").is_file() else list(gen_dir.glob("*.svg"))
        if candidates and candidates[0].is_file():
            return FileResponse(
                path=str(candidates[0]),
                media_type="image/svg+xml",
                filename=f"{gen.topic.replace(' ', '_')}_diagram.svg"
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SVG file was not found.")

    # 2. PNG Export
    elif fmt == "png":
        poster_png = gen_dir / "poster.png"
        if poster_png.is_file():
            return FileResponse(
                path=str(poster_png),
                media_type="image/png",
                filename=f"{gen.topic.replace(' ', '_')}_poster.png"
            )
        illus = gen_dir / "illustration.png"
        if illus.is_file():
            return FileResponse(path=str(illus), media_type="image/png", filename=f"{gen.topic.replace(' ', '_')}_illustration.png")
        candidates = list(gen_dir.glob("diagram*.png"))
        if candidates and candidates[0].is_file():
            return FileResponse(
                path=str(candidates[0]),
                media_type="image/png",
                filename=f"{gen.topic.replace(' ', '_')}_diagram.png"
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PNG file was not found.")

    # 3. PDF Export (Comprehensive Course PDF)
    elif fmt == "pdf":
        export_pdf_path = gen_dir / "course_package.pdf"
        diagram_png = gen_dir / "poster.png" if (gen_dir / "poster.png").is_file() else None
        if diagram_png is None:
            d_candidates = list(gen_dir.glob("diagram*.png"))
            if d_candidates:
                diagram_png = d_candidates[0]

        illustration_png = None
        illus = gen_dir / "illustration.png"
        if illus.is_file():
            illustration_png = illus

        concepts_list = []
        relationships_list = []
        if gen.content_json:
            try:
                c_data = json.loads(gen.content_json)
                concepts_list = c_data.get("key_concepts", [])
                relationships_list = c_data.get("relationships", [])
            except Exception:
                pass

        build_course_export_pdf(
            pdf_path=export_pdf_path,
            title=gen.topic,
            diagram_type=gen.diagram_type,
            summary=gen.summary or "",
            concepts=concepts_list,
            relationships=relationships_list,
            diagram_png_path=diagram_png,
            illustration_png_path=illustration_png,
            quality_score=gen.quality_score,
            provider_info=gen.provider,
            prompt=gen.prompt_text,
            created_at_str=gen.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            image_provider=gen.image_provider,
            image_is_mock=bool(gen.image_is_mock),
        )

        return FileResponse(
            path=str(export_pdf_path),
            media_type="application/pdf",
            filename=f"{gen.topic.replace(' ', '_')}_course_diagram.pdf"
        )
