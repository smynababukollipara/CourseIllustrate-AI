from typing import TypedDict, Optional, List, Dict, Any, Literal
from app.schemas.generation import (
    ConceptItem,
    ContentUnderstandingOutput,
    DiagramPlanningOutput,
    PromptEngineeringOutput,
    ImageGenerationOutput,
    QualityEvaluationOutput,
    PosterDesignSettings,
)


class DiagramAgentState(TypedDict, total=False):
    """
    Central state shared across LangGraph agent nodes.
    Maintains raw course content, intermediate agent extractions, diagram plan,
    quality evaluation, prompt engineering, and diffusion image generation.
    """
    # Core identifiers & inputs
    generation_id: Optional[str]
    project_id: Optional[str]
    document_id: Optional[str]
    raw_content: str
    source_type: Literal["text", "pdf"]
    requested_diagram_type: str
    custom_focus: Optional[str]
    illustration_style: str
    complexity_level: str
    generate_illustration: bool
    poster_settings: PosterDesignSettings

    # Agent 1: Content Understanding
    topic: Optional[str]
    extracted_concepts: List[ConceptItem]
    relationships: List[str]
    educational_summary: Optional[str]
    learning_objectives: List[str]
    content_understanding: Optional[ContentUnderstandingOutput]

    # Agent 2: Diagram Planning
    diagram_type: str
    diagram_spec: Optional[Dict[str, Any]]
    mermaid_code: Optional[str]
    explanation: Optional[str]
    diagram_plan: Optional[DiagramPlanningOutput]

    # Agent 5: Quality Evaluation & Repair Loop
    evaluation_score: Optional[float]
    evaluation_passed: bool
    evaluation_feedback: Optional[str]
    quality_output: Optional[QualityEvaluationOutput]
    retry_count: int

    # Agent 3: Prompt Engineering
    illustration_prompt: Optional[str]
    negative_prompt: Optional[str]
    prompt_output: Optional[PromptEngineeringOutput]

    # Agent 4: Image Generation
    generated_image_path: Optional[str]
    image_url: Optional[str]
    svg_path: Optional[str]
    svg_url: Optional[str]
    poster_url: Optional[str]
    poster_png_url: Optional[str]
    pdf_path: Optional[str]
    pdf_url: Optional[str]
    image_provider: Optional[str]
    image_error: Optional[str]
    image_is_mock: bool
    image_output: Optional[ImageGenerationOutput]

    # Operational status & Agent tracking
    current_agent: str
    agent_status: Dict[str, str]  # e.g. {"content_understanding": "completed", ...}
    status: str
    error: Optional[str]
    errors: List[str]
    final_status: str
    is_mock: bool
    provider: str
    execution_logs: List[Dict[str, Any]]


AgentState = DiagramAgentState
