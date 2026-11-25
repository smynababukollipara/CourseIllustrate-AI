from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

DiagramType = Literal[
    "flowchart",
    "mindmap",
    "concept_map",
    "hierarchical",
    "process",
    "sequence",
    "architecture",
    "comparison",
    "timeline",
    "tree",
]

DIAGRAM_TYPES: List[str] = [
    "flowchart",
    "mindmap",
    "concept_map",
    "hierarchical",
    "process",
    "sequence",
    "architecture",
    "comparison",
    "timeline",
    "tree",
]


IllustrationStyle = Literal[
    "professional_educational",
    "minimalist",
    "scientific",
    "3d",
    "hand_drawn",
    "flat_vector",
    "isometric",
]

ILLUSTRATION_STYLES: List[str] = [
    "professional_educational",
    "minimalist",
    "scientific",
    "3d",
    "hand_drawn",
    "flat_vector",
    "isometric",
]

PosterTheme = Literal[
    "vibrant_educational",
    "science_technology",
    "creative_classroom",
    "professional_infographic",
    "nature_biology",
    "dark_neon_learning",
]

PosterLayoutStyle = Literal[
    "educational_infographic",
    "scientific_poster",
    "illustrated_process",
    "concept_map_poster",
    "technical_architecture_poster",
]

PosterOrientation = Literal["portrait", "landscape", "square", "presentation_16_9"]


class PosterDesignSettings(BaseModel):
    theme: PosterTheme = "vibrant_educational"
    layout_style: PosterLayoutStyle = "educational_infographic"
    orientation: PosterOrientation = "portrait"
    color_scheme: Literal["subject_aware", "theme_palette"] = "subject_aware"
    visual_complexity: Literal["introductory", "balanced", "detailed"] = "balanced"


class ConceptItem(BaseModel):
    """An individual educational concept extracted from the course content."""
    id: str = Field(description="Unique snake_case or short identifier, e.g. 'gradient_descent'")
    name: str = Field(description="Human readable display name")
    definition: str = Field(description="Clear, 1-2 sentence pedagogical definition")
    importance: Literal["core", "secondary", "supporting"] = Field(
        default="core",
        description="Pedagogical importance level"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="ID of parent concept if part of a taxonomy or hierarchy"
    )
    related_to: List[str] = Field(
        default_factory=list,
        description="List of related concept IDs"
    )


class ContentUnderstandingOutput(BaseModel):
    """Structured result produced by the Content Understanding Agent."""
    title: str = Field(description="Pedagogical or chapter title for the material")
    summary: str = Field(description="Educational summary of the main learning objectives")
    key_concepts: List[ConceptItem] = Field(
        description="Extracted concepts, entities, and definitions"
    )
    suggested_diagram_type: DiagramType = Field(
        default="flowchart",
        description="Agent-recommended diagram type based on structural characteristics"
    )
    pedagogical_notes: str = Field(
        default="",
        description="Teaching takeaways or sequencing advice"
    )
    main_subject: str = Field(default="", description="Primary subject area")
    topics: List[str] = Field(default_factory=list)
    subtopics: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list, description="Plain-language concept relationships")
    processes: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    key_equations: List[str] = Field(default_factory=list)
    source_pages: List[int] = Field(default_factory=list)
    is_mock: bool = Field(default=False)
    provider_info: str = Field(default="")


class DiagramNode(BaseModel):
    id: str
    label: str
    description: str = ""
    parent_id: Optional[str] = None


class DiagramConnection(BaseModel):
    source: str
    target: str
    label: str = ""


class DiagramPlanningOutput(BaseModel):
    """Structured result produced by the Diagram Planning Agent."""
    diagram_type: DiagramType = Field(
        description="Diagram format planned and generated"
    )
    mermaid_code: str = Field(
        description="Syntactically valid Mermaid.js code representing the diagram"
    )
    explanation: str = Field(
        description="Brief explanation of how the visual layout aids comprehension"
    )
    node_count: int = Field(default=0, description="Total nodes in the diagram")
    pedagogical_focus: str = Field(default="", description="Key visual metaphor or focus")
    title: str = Field(default="")
    nodes: List[DiagramNode] = Field(default_factory=list)
    connections: List[DiagramConnection] = Field(default_factory=list)
    layout_instructions: str = Field(default="")
    source_references: List[str] = Field(default_factory=list)
    is_mock: bool = Field(default=False)
    provider_info: str = Field(default="")


class PromptEngineeringOutput(BaseModel):
    """Visual generation prompt produced for diffusion models."""
    prompt: str
    negative_prompt: str = ""
    style: str = "professional_educational"
    diagram_type: str = ""
    title: str = ""
    visual_elements: List[str] = Field(default_factory=list)
    style_notes: List[str] = Field(default_factory=list)
    preserved_terms: List[str] = Field(default_factory=list)
    composition_notes: str = ""
    is_mock: bool = False
    provider_info: str = ""


class ImageGenerationOutput(BaseModel):
    """Metadata for a stored diagram image. Paths are relative to generated storage."""
    relative_path: str
    svg_path: Optional[str] = None
    pdf_path: Optional[str] = None
    image_format: str = "png"
    width: int = 0
    height: int = 0
    byte_size: int = 0
    is_mock: bool = False
    provider: str = ""
    prompt_used: str = ""
    valid: bool = False
    attempt: int = 1


class QualityCriterion(BaseModel):
    name: str
    score: float = Field(description="0-100")
    notes: str = ""


class QualityEvaluationOutput(BaseModel):
    """
    Quality result. evaluation_method "structural" inspects the plan, labels,
    coverage, and file validity. It is not a pixel-level visual review.
    evaluation_method "image_model" is set only after an image model actually
    reviews the generated file.
    """
    overall_score: float
    passed: bool
    threshold: float
    criteria: List[QualityCriterion] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    evaluation_method: Literal["structural", "image_model"] = "structural"
    method_note: str = ""
    is_mock: bool = False
    provider_info: str = ""


class DiagramGenerationRequest(BaseModel):
    """API request payload to generate a course diagram."""
    topic: Optional[str] = Field(
        default=None,
        description="Optional educational topic to focus content understanding on"
    )
    text_input: Optional[str] = Field(
        default=None,
        description="Direct lecture text or study notes"
    )
    document_id: Optional[str] = Field(
        default=None,
        description="ID of a previously uploaded and parsed PDF document"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project ID to associate this generation with"
    )
    diagram_type: Optional[str] = Field(
        default="flowchart",
        description="Preferred diagram format (flowchart, mindmap, concept_map, architecture, process, hierarchical, comparison, or auto)."
    )
    auto_select_type: bool = Field(
        default=False,
        description="When true, the planning agent uses its suggested diagram type."
    )
    custom_focus: Optional[str] = Field(
        default=None,
        description="Optional custom focus or angle (e.g., 'emphasize time complexity')"
    )
    illustration_style: Optional[str] = Field(
        default="professional_educational",
        description="Style for diffusion illustration: professional_educational, minimalist, scientific, 3d, hand_drawn, flat_vector, isometric."
    )
    complexity_level: Optional[str] = Field(
        default="intermediate",
        description="Complexity level: introductory, intermediate, advanced."
    )
    generate_illustration: bool = Field(
        default=True,
        description="Whether to generate a diffusion-based illustration alongside the structured diagram."
    )
    poster_settings: PosterDesignSettings = Field(default_factory=PosterDesignSettings)


class PosterRegenerationRequest(BaseModel):
    poster_settings: PosterDesignSettings = Field(default_factory=PosterDesignSettings)


class DiagramGenerationResponse(BaseModel):
    """API response payload containing generated diagram and educational metadata."""
    generation_id: str
    project_id: Optional[str] = None
    topic: str
    diagram_type: str
    mermaid_code: str
    summary: str
    concepts: List[ConceptItem]
    is_mock: bool
    provider: str
    execution_time_ms: int
    created_at: datetime
    status: str = "completed"
    quality_score: Optional[float] = None
    quality_passed: Optional[bool] = None
    evaluation_method: Optional[str] = None
    quality: Optional[QualityEvaluationOutput] = None
    image_url: Optional[str] = None
    poster_url: Optional[str] = None
    svg_url: Optional[str] = None
    pdf_url: Optional[str] = None
    image_is_mock: Optional[bool] = None
    image_provider: Optional[str] = None
    image_error: Optional[str] = None
    image_format: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    retry_count: int = 0
    execution_logs: List[Dict[str, Any]] = Field(default_factory=list)
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    illustration_style: Optional[str] = None
    poster_settings: Optional[PosterDesignSettings] = None
    agent_status: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)


class GenerationDetail(BaseModel):
    id: str
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    topic: str
    diagram_type: str
    diagram_code: Optional[str] = None
    status: str
    summary: Optional[str] = None
    quality_score: Optional[float] = None
    evaluation_method: Optional[str] = None
    provider: Optional[str] = None
    is_mock: Optional[bool] = None
    image_is_mock: Optional[bool] = None
    image_provider: Optional[str] = None
    image_error: Optional[str] = None
    image_format: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    custom_focus: Optional[str] = None
    prompt_text: Optional[str] = None
    negative_prompt: Optional[str] = None
    illustration_style: Optional[str] = None
    agent_status: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    image_url: Optional[str] = None
    poster_url: Optional[str] = None
    svg_url: Optional[str] = None
    pdf_url: Optional[str] = None
    quality: Optional[QualityEvaluationOutput] = None
    execution_logs: List[Dict[str, Any]] = Field(default_factory=list)
    content: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    concepts: List[ConceptItem] = Field(default_factory=list)
    poster_settings: Optional[PosterDesignSettings] = None
    generate_illustration: bool = True

    model_config = ConfigDict(from_attributes=True)


class GenerationSummary(BaseModel):
    id: str
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    topic: str
    diagram_type: str
    status: str
    quality_score: Optional[float] = None
    is_mock: Optional[bool] = None
    image_is_mock: Optional[bool] = None
    created_at: datetime
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    project_title: Optional[str] = None
    document_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
