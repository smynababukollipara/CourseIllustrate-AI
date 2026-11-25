import pytest
import pytest_asyncio
from pathlib import Path

from app.services.llm_provider import MockLLMProvider
from app.agents.nodes.content_agent import content_understanding_node
from app.agents.nodes.diagram_agent import diagram_planning_node
from app.agents.nodes.quality_agent import quality_evaluation_node, validate_mermaid_syntax, evaluate_concept_coverage
from app.agents.nodes.prompt_agent import prompt_engineering_node, STYLE_DESCRIPTIONS
from app.agents.nodes.image_agent import image_generation_node, generate_local_mock_illustration
from app.agents.state import DiagramAgentState
from app.schemas.generation import (
    ConceptItem,
    ContentUnderstandingOutput,
    DiagramPlanningOutput,
    DiagramNode,
    DiagramConnection,
)


# ==============================================================================
# 1. CONTENT UNDERSTANDING AGENT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_content_agent_cpu_pipeline_extraction():
    """Verify Content Understanding Agent extracts topic, subtopics, concepts, and relationships."""
    state: DiagramAgentState = {
        "raw_content": "Explain the working of a CPU pipeline.",
        "source_type": "text",
        "project_id": None,
        "requested_diagram_type": "flowchart",
        "custom_focus": None,
        "execution_logs": []
    }
    result = await content_understanding_node(state)
    assert result["status"] == "content_understood"
    assert result["topic"] == "CPU Pipeline"
    assert len(result["extracted_concepts"]) >= 4
    # Verify core pipeline stages
    concept_names = [c.name for c in result["extracted_concepts"]]
    assert "Instruction Fetch" in concept_names
    assert "Instruction Decode" in concept_names
    assert "Execution" in concept_names
    # Verify relationships
    assert len(result["relationships"]) >= 3
    assert any("Instruction Fetch precedes" in r for r in result["relationships"])
    # Verify learning objectives
    assert len(result["learning_objectives"]) >= 1


@pytest.mark.asyncio
async def test_content_agent_dynamic_definitions():
    """Verify Content Understanding Agent dynamically parses definitions from arbitrary lecture text."""
    state: DiagramAgentState = {
        "raw_content": (
            "Course: Distributed Systems\n"
            "Raft is a consensus algorithm designed for understandability.\n"
            "Log replication ensures state consistency across server replicas.\n"
            "Heartbeat is a periodic communication signal verifying leader health."
        ),
        "source_type": "text",
        "project_id": None,
        "requested_diagram_type": "flowchart",
        "custom_focus": None,
        "execution_logs": []
    }
    result = await content_understanding_node(state)
    assert result["status"] == "content_understood"
    assert "Distributed Systems" in result["topic"]
    assert len(result["extracted_concepts"]) >= 3


# ==============================================================================
# 2. DIAGRAM PLANNING AGENT TESTS
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("dtype", [
    "flowchart", "mindmap", "concept_map", "architecture",
    "process", "hierarchical", "comparison"
])
async def test_diagram_agent_all_seven_types(dtype):
    """Verify Diagram Planning Agent generates valid Mermaid and structured nodes for all 7 types."""
    provider = MockLLMProvider()
    content = ContentUnderstandingOutput(
        title="Photosynthesis",
        summary="Biological conversion of light energy into chemical energy.",
        key_concepts=[
            ConceptItem(id="light_reaction", name="Light Reactions", definition="Thylakoid solar energy absorption", importance="core"),
            ConceptItem(id="calvin_cycle", name="Calvin Cycle", definition="Stroma carbon fixation reactions", importance="core"),
            ConceptItem(id="atp_synthesis", name="ATP Synthesis", definition="Photophosphorylation proton gradient", importance="secondary")
        ],
        suggested_diagram_type="flowchart",
        is_mock=True
    )
    plan = await provider.plan_diagram(content, preferred_diagram_type=dtype)
    assert plan.diagram_type == dtype
    assert plan.mermaid_code is not None
    assert len(plan.mermaid_code) > 20
    assert len(plan.nodes) >= 2
    assert plan.node_count == len(content.key_concepts)


@pytest.mark.asyncio
async def test_process_diagram_uses_concise_labels_and_keeps_full_explanations():
    full_definition = (
        "Instruction Fetch reads the next instruction from the instruction cache, "
        "increments the program counter, and supplies the instruction to decode."
    )
    content = ContentUnderstandingOutput(
        title="CPU Pipeline",
        summary="Instructions move through ordered stages.",
        key_concepts=[
            ConceptItem(
                id="instruction_fetch",
                name="Instruction Fetch",
                definition=full_definition,
                importance="core",
            ),
            ConceptItem(
                id="instruction_decode",
                name="Instruction Decode",
                definition="Decodes the instruction and reads register operands.",
                importance="core",
            ),
        ],
    )

    plan = await MockLLMProvider().plan_diagram(content, preferred_diagram_type="process")

    assert "..." not in plan.mermaid_code
    assert full_definition not in plan.mermaid_code
    assert plan.nodes[0].label == "Stage 1: Instruction Fetch"
    assert plan.nodes[0].description == full_definition


# ==============================================================================
# 3. PROMPT ENGINEERING AGENT TESTS
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("style", [
    "professional_educational", "minimalist", "scientific",
    "3d", "hand_drawn", "flat_vector", "isometric"
])
async def test_prompt_agent_style_customization(style):
    """Verify Prompt Engineering Agent incorporates topic, style keywords, and negative prompts."""
    state: DiagramAgentState = {
        "topic": "Neural Network Optimization",
        "educational_summary": "Iterative parameter tuning via backpropagation.",
        "extracted_concepts": [
            ConceptItem(id="c1", name="Gradient Descent", definition="Loss surface navigation", importance="core"),
            ConceptItem(id="c2", name="Learning Rate", definition="Step size hyperparameter", importance="core")
        ],
        "illustration_style": style,
        "custom_focus": "Show loss landscape saddle points",
        "execution_logs": []
    }
    result = await prompt_engineering_node(state)
    assert result["status"] == "prompt_engineered"
    prompt_str = result["illustration_prompt"]
    assert "Neural Network Optimization" in prompt_str
    assert "saddle points" in prompt_str
    assert result["negative_prompt"] is not None
    assert "blurry" in result["negative_prompt"].lower()
    assert result["prompt_output"].style == style


# ==============================================================================
# 4. QUALITY EVALUATION AGENT TESTS
# ==============================================================================

def test_mermaid_syntax_validation():
    """Verify deterministic Mermaid syntax validation checks balanced brackets and headers."""
    # Valid
    valid_code = "flowchart TD\n    A[Input Data] --> B[Processing]\n    B --> C[Outcome]"
    valid, errors = validate_mermaid_syntax(valid_code)
    assert valid is True
    assert len(errors) == 0

    # Invalid header
    bad_header = "unknown TD\n    A --> B"
    valid, errors = validate_mermaid_syntax(bad_header)
    assert valid is False
    assert any("directive" in e.lower() for e in errors)

    # Mismatched brackets
    mismatched = "flowchart TD\n    A[Unclosed bracket --> B[Target]"
    valid, errors = validate_mermaid_syntax(mismatched)
    assert valid is False
    assert any("mismatched" in e.lower() for e in errors)


def test_concept_coverage_scoring():
    """Verify concept coverage calculation detects missing educational nodes."""
    concepts = [
        ConceptItem(id="fetch", name="Instruction Fetch", definition="Fetch", importance="core"),
        ConceptItem(id="decode", name="Instruction Decode", definition="Decode", importance="core"),
        ConceptItem(id="execute", name="Execution", definition="Execute", importance="core")
    ]
    # Full coverage
    code = "flowchart TD\n    fetch[Instruction Fetch] --> decode[Instruction Decode] --> execute[Execution]"
    score, found, missing = evaluate_concept_coverage(concepts, code)
    assert score == 100.0
    assert len(missing) == 0

    # Partial coverage
    code_partial = "flowchart TD\n    fetch[Instruction Fetch] --> other[Other]"
    score_p, found_p, missing_p = evaluate_concept_coverage(concepts, code_partial)
    assert score_p < 50.0
    assert "Instruction Decode" in missing_p


@pytest.mark.asyncio
async def test_quality_agent_evaluation_score():
    """Verify Quality Evaluation Agent generates structured criteria, scoring, and suggestions."""
    content = ContentUnderstandingOutput(
        title="Binary Search",
        summary="Divide and conquer search algorithm.",
        key_concepts=[
            ConceptItem(id="mid", name="Midpoint Evaluation", definition="Bisect interval", importance="core"),
            ConceptItem(id="branch", name="Interval Elimination", definition="Discard half", importance="core")
        ],
        suggested_diagram_type="flowchart",
        is_mock=True
    )
    plan = DiagramPlanningOutput(
        diagram_type="flowchart",
        mermaid_code="flowchart TD\n    A[Midpoint Evaluation] --> B[Interval Elimination]",
        explanation="Binary search bisection flow.",
        node_count=2,
        nodes=[
            DiagramNode(id="mid", label="Midpoint Evaluation", description="Bisect interval"),
            DiagramNode(id="branch", label="Interval Elimination", description="Discard half"),
        ],
        connections=[
            DiagramConnection(source="mid", target="branch", label="followed by")
        ],
        is_mock=True
    )
    state: DiagramAgentState = {
        "topic": "Binary Search",
        "diagram_plan": plan,
        "content_understanding": content,
        "mermaid_code": plan.mermaid_code,
        "extracted_concepts": content.key_concepts,
        "execution_logs": []
    }
    result = await quality_evaluation_node(state)
    assert result["status"] == "quality_evaluated"
    assert result["evaluation_score"] >= 70.0
    assert result["evaluation_passed"] is True
    assert result["quality_output"] is not None
    assert len(result["quality_output"].criteria) >= 8


# ==============================================================================
# 5. IMAGE GENERATION AGENT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_image_agent_mock_mode_safe_local_generation(tmp_path):
    """Verify Image Generation Agent produces valid local assets in mock dev mode without network."""
    plan = DiagramPlanningOutput(
        diagram_type="flowchart",
        mermaid_code="flowchart TD\n    A[Alpha] --> B[Beta]",
        explanation="Alpha Beta flow",
        node_count=2,
        is_mock=True
    )
    state: DiagramAgentState = {
        "generation_id": "test_gen_123",
        "topic": "Operating Systems Virtual Memory",
        "illustration_style": "minimalist",
        "diagram_plan": plan,
        "diagram_type": "flowchart",
        "generate_illustration": True,
        "illustration_prompt": "Minimalist educational illustration of virtual memory page tables",
        "extracted_concepts": [
            ConceptItem(id="pt", name="Page Table", definition="Virtual to physical mapping", importance="core"),
            ConceptItem(id="tlb", name="Translation Lookaside Buffer", definition="Fast hardware cache", importance="core")
        ],
        "is_mock": True,
        "execution_logs": []
    }
    result = await image_generation_node(state)
    assert result["status"] == "completed"
    assert result["image_is_mock"] is True
    assert result["image_provider"] == "Local development preview (not Stable Diffusion)"
    assert result["image_url"] is not None
    assert result["svg_url"] is not None
    assert result["pdf_url"] is not None


@pytest.mark.asyncio
async def test_image_agent_diagram_only_skips_illustration():
    """Verify that when generate_illustration is False, the image agent skips diffusion cleanly."""
    plan = DiagramPlanningOutput(
        diagram_type="flowchart",
        mermaid_code="flowchart TD\n    A[Start] --> B[End]",
        explanation="Simple flow",
        node_count=2,
        is_mock=True
    )
    state: DiagramAgentState = {
        "generation_id": "test_gen_diagram_only",
        "topic": "Algorithms",
        "diagram_plan": plan,
        "generate_illustration": False,
        "execution_logs": []
    }
    result = await image_generation_node(state)
    assert result["status"] == "completed"
    assert result["agent_status"]["image_generation"] == "skipped"
    assert result["generated_image_path"] is None
    assert result["svg_url"] is not None
