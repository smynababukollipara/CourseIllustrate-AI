import time
import logging
from typing import Dict, Any, List

from app.agents.state import DiagramAgentState
from app.schemas.generation import PromptEngineeringOutput

logger = logging.getLogger(__name__)

STYLE_DESCRIPTIONS = {
    "professional_educational": (
        "professional editorial educational textbook illustration, crisp vector art, elegant visual hierarchy, "
        "subtle gradient shading, dark studio background, refined indigo and violet accents, high information clarity"
    ),
    "minimalist": (
        "minimalist graphic illustration, restrained modern palette, generous negative space, geometric abstractions, "
        "crisp lines, high contrast visual elements, modern Swiss design aesthetic"
    ),
    "scientific": (
        "precise scientific journal illustration, technical schematic, labeled component flow, clean architectural view, "
        "crisp technical draughtsmanship, subdued neutral background with high-visibility accent highlights"
    ),
    "3d": (
        "3D educational concept render, octane render, soft ambient occlusion, volumetric subtle lighting, "
        "tactile matte finish, smooth bevels, clean isometric perspective, premium modern tech feel"
    ),
    "hand_drawn": (
        "hand-drawn academic sketchbook illustration, fine ink crosshatching, subtle watercolor wash, "
        "educational blueprint notes, artisanal textbook diagram style"
    ),
    "flat_vector": (
        "flat vector graphic illustration, modern tech SaaS aesthetic, solid color blocking, bold silhouette, "
        "crisp geometric outlines, vibrant readable color scheme, SVG clarity"
    ),
    "isometric": (
        "detailed isometric 3D educational diorama, orthographic perspective, layered modular components, "
        "clean cutaway visual structure, soft directional shadows, dark slate background"
    )
}

DEFAULT_NEGATIVE_PROMPT = (
    "photorealistic face, blurry, low quality, noisy, jpeg artifacts, watermark, signature, copyright, "
    "garbled unreadable text, deformed shapes, chaotic clutter, childish cartoon, horror, oversaturated"
)


async def prompt_engineering_node(state: DiagramAgentState) -> Dict[str, Any]:
    """
    Agent 3: Prompt Engineering Agent.
    Transforms educational topic, learning objectives, and concepts into
    detailed diffusion-model prompts with visual composition, lighting, style,
    and negative prompts.
    """
    logger.info("Executing Prompt Engineering Agent...")
    start_time = time.time()
    agent_status = dict(state.get("agent_status", {}))
    agent_status["prompt_engineering"] = "running"

    topic = state.get("topic") or "Educational Topic"
    summary = state.get("educational_summary") or ""
    concepts = state.get("extracted_concepts") or []
    style_key = state.get("illustration_style", "professional_educational").lower()
    custom_focus = state.get("custom_focus")

    style_desc = STYLE_DESCRIPTIONS.get(style_key, STYLE_DESCRIPTIONS["professional_educational"])

    # Identify primary visual elements from concepts
    concept_names = [c.name if hasattr(c, "name") else str(c) for c in concepts[:5]]
    preserved_terms = concept_names.copy()

    visual_elements: List[str] = []
    for c in concepts[:4]:
        name = getattr(c, "name", str(c))
        visual_elements.append(f"visualized representation of {name}")

    elements_clause = ", ".join(visual_elements) if visual_elements else "key structural components"

    # Assemble detailed, topic-specific diffusion prompt
    prompt_parts = [
        f"An educational visual illustration explaining '{topic}'",
        f"featuring {elements_clause}",
        f"style: {style_desc}",
        "composition: centered instructional layout with clear visual hierarchy, logical directional flow",
        "lighting: soft studio lighting with gentle glows, dark deep navy slate background (#090d16)",
        "color palette: sophisticated indigo (#6366f1), electric violet, cyan highlights, and crisp white details",
        "purpose: clear visual comprehension for students and online course learners",
        "extremely high quality, 8k resolution concept art, pristine vector clarity"
    ]

    if custom_focus:
        prompt_parts.insert(2, f"special pedagogical emphasis: {custom_focus}")

    full_prompt = ". ".join(prompt_parts)
    negative_prompt = DEFAULT_NEGATIVE_PROMPT

    prompt_output = PromptEngineeringOutput(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        style=style_key,
        diagram_type=state.get("diagram_type", "flowchart"),
        title=topic,
        visual_elements=visual_elements,
        style_notes=[f"Style selected: {style_key}", f"Style description applied: {style_desc[:60]}..."],
        preserved_terms=preserved_terms,
        composition_notes="Centered educational hierarchy, directionally aligned conceptual flow.",
        is_mock=state.get("is_mock", True),
        provider_info="Prompt Engineering Agent (Educational Diffusion Prompt Synthesizer)"
    )

    duration_ms = int((time.time() - start_time) * 1000)

    log_entry = {
        "agent": "Prompt Engineering Agent",
        "action": f"Synthesized diffusion prompt for style '{style_key}'",
        "topic": topic,
        "style": style_key,
        "prompt_length_chars": len(full_prompt),
        "visual_elements_count": len(visual_elements),
        "preserved_terms": preserved_terms,
        "duration_ms": duration_ms,
        "is_mock": prompt_output.is_mock,
        "provider": prompt_output.provider_info
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)
    agent_status["prompt_engineering"] = "completed"

    return {
        "illustration_prompt": full_prompt,
        "negative_prompt": negative_prompt,
        "prompt_output": prompt_output,
        "status": "prompt_engineered",
        "current_agent": "prompt_engineering",
        "agent_status": agent_status,
        "execution_logs": logs
    }
