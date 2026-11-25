import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import pymupdf

from app.main import app
from app.db.session import init_db
from app.services.llm_provider import MockLLMProvider, get_llm_provider
from app.agents.graph import diagram_graph
from app.agents.state import DiagramAgentState
from app.schemas.generation import ContentUnderstandingOutput, ConceptItem


def create_sample_pdf_bytes(title: str = "Operating Systems", pages: int = 1) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        f"Course: {title}\nChapter 1: Process Scheduling\n"
        f"A process is an instance of a program in execution.\n"
        f"Context switching stores process state."
    )
    b = doc.tobytes()
    doc.close()
    return b


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield


@pytest.mark.asyncio
async def test_mock_llm_provider_understand_content():
    """Verify MockLLMProvider extracts title and rich structured concepts."""
    provider = MockLLMProvider()
    assert provider.is_mock is True
    assert "MockLLMProvider" in provider.provider_name

    text = (
        "Course: Graph Theory\n"
        "A graph is a non-linear data structure consisting of vertices and edges.\n"
        "Breadth-First Search explores neighbor nodes first.\n"
        "Depth-First Search explores as far as possible along each branch."
    )
    result = await provider.understand_content(text)
    assert isinstance(result, ContentUnderstandingOutput)
    assert "Graph Theory" in result.title
    assert len(result.key_concepts) >= 3
    assert result.is_mock is True


@pytest.mark.asyncio
async def test_poster_request_separates_photosynthesis_from_design_instructions():
    prompt = (
        "Create a colourful educational infographic explaining Photosynthesis – How Plants Make Their Food.\n"
        "Include These Components: Sunlight, Chlorophyll, Chloroplasts, Carbon Dioxide, Water, "
        "Light-Dependent Reactions, Calvin Cycle, Glucose, Oxygen.\n"
        "Generate an educational poster. Add a key takeaway."
    )
    result = await MockLLMProvider().understand_content(prompt)
    names = {concept.name for concept in result.key_concepts}
    assert result.title == "Photosynthesis"
    assert names == {
        "Sunlight", "Chlorophyll", "Chloroplasts", "Carbon Dioxide", "Water",
        "Light-Dependent Reactions", "Calvin Cycle", "Glucose", "Oxygen",
    }
    assert not any(name.lower().startswith(("create", "include", "generate", "show", "add")) for name in names)
    assert result.key_equations == ["6CO2 + 6H2O + Light Energy → C6H12O6 + 6O2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("dtype,expected_prefix", [
    ("flowchart", "flowchart TD"),
    ("mindmap", "mindmap"),
    ("concept_map", "flowchart LR"),
    ("architecture", "flowchart TB"),
])
async def test_mock_llm_provider_diagram_types(dtype, expected_prefix):
    """Verify all 4 diagram types generate syntactically valid Mermaid definitions."""
    provider = MockLLMProvider()
    content = ContentUnderstandingOutput(
        title="Distributed Systems",
        summary="Overview of consensus algorithms.",
        key_concepts=[
            ConceptItem(id="leader", name="Leader Election", definition="Electing coordinating node", importance="core"),
            ConceptItem(id="heartbeat", name="Heartbeat", definition="Periodic ping to verify node health", importance="secondary"),
            ConceptItem(id="log_replication", name="Log Replication", definition="Duplicating committed state", importance="core")
        ],
        suggested_diagram_type=dtype,
        is_mock=True
    )

    plan = await provider.plan_diagram(content, preferred_diagram_type=dtype)
    assert plan.diagram_type == dtype
    assert plan.mermaid_code.startswith(expected_prefix)
    assert plan.node_count == 3
    assert plan.is_mock is True


@pytest.mark.asyncio
async def test_langgraph_pipeline_execution():
    """Verify end-to-end execution of the LangGraph multi-agent state machine."""
    state: DiagramAgentState = {
        "raw_content": (
            "Course: Computer Networks\n"
            "TCP is a connection-oriented transmission protocol.\n"
            "Three-way handshake establishes a reliable session.\n"
            "Flow control prevents receiver buffer overflow."
        ),
        "source_type": "text",
        "project_id": None,
        "requested_diagram_type": "flowchart",
        "custom_focus": "Handshake mechanics",
        "content_understanding": None,
        "diagram_plan": None,
        "status": "initial",
        "error": None,
        "is_mock": False,
        "provider": "",
        "execution_logs": []
    }

    final_state = await diagram_graph.ainvoke(state)
    assert final_state["status"] in ("diagram_planned", "completed")
    assert final_state["error"] is None
    assert final_state["content_understanding"] is not None
    assert final_state["diagram_plan"] is not None
    assert final_state["diagram_plan"].diagram_type == "flowchart"
    assert len(final_state["execution_logs"]) >= 2


@pytest.mark.asyncio
async def test_api_generate_diagram_from_text():
    """Test POST /api/v1/generations/diagram with direct lecture text."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "text_input": (
                "Course: Database Internals\n"
                "B-Trees are self-balancing search trees for block storage.\n"
                "Write-Ahead Logging guarantees durability in ACID transactions."
            ),
            "diagram_type": "mindmap"
        }
        response = await client.post("/api/v1/generations/diagram", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["diagram_type"] == "mindmap"
        assert "mindmap" in data["mermaid_code"]
        assert data["is_mock"] is True
        assert len(data["concepts"]) >= 2
        assert "generation_id" in data

        # Verify we can retrieve it via GET
        gen_id = data["generation_id"]
        get_res = await client.get(f"/api/v1/generations/{gen_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == gen_id


@pytest.mark.asyncio
async def test_api_generate_diagram_from_pdf():
    """Test generating a diagram directly from an uploaded course PDF document_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload PDF
        pdf_bytes = create_sample_pdf_bytes("Microservices 101", pages=1)
        files = {"file": ("microservices.pdf", pdf_bytes, "application/pdf")}
        upload_res = await client.post("/api/v1/documents/upload", files=files)
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["document_id"]

        # 2. Generate diagram from document_id
        payload = {
            "document_id": doc_id,
            "diagram_type": "architecture"
        }
        gen_res = await client.post("/api/v1/generations/diagram", json=payload)
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["diagram_type"] == "architecture"
        assert "subgraph" in gen_data["mermaid_code"]
        assert gen_data["is_mock"] is True


@pytest.mark.asyncio
async def test_api_generate_diagram_from_topic_only():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/generations/diagram",
            json={"topic": "Photosynthesis", "diagram_type": "process"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Photosynthesis"
        assert data["generation_id"]


@pytest.mark.asyncio
async def test_api_generate_missing_input_rejected():
    """Verify request with neither text_input nor document_id returns 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/generations/diagram", json={})
        assert response.status_code == 400
        assert "Either 'text_input' or 'document_id' must be provided" in response.json()["detail"]


def test_provider_mode_distinction():
    """Verify that MockLLMProvider is active by default and clearly distinguished from Gemini."""
    provider = get_llm_provider()
    assert provider.is_mock is True
    assert "Mock" in provider.provider_name
