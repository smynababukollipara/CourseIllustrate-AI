import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.models import Generation
from app.db.session import async_session_maker, init_db
from app.agents.graph import diagram_graph, check_quality_repair_loop
from app.agents.state import DiagramAgentState
from app.schemas.generation import ConceptItem, ContentUnderstandingOutput, DiagramPlanningOutput


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield


@pytest.mark.asyncio
async def test_full_five_agent_workflow():
    """Verify that all 5 specialized agents execute in sequence through LangGraph."""
    initial_state: DiagramAgentState = {
        "raw_content": (
            "Explain the working of a five-stage CPU pipeline: "
            "Instruction Fetch, Instruction Decode, Execution, Memory Access, and Write Back."
        ),
        "source_type": "text",
        "project_id": None,
        "requested_diagram_type": "process",
        "custom_focus": "Pipelining throughput and hazards",
        "illustration_style": "isometric",
        "complexity_level": "intermediate",
        "generate_illustration": True,
        "retry_count": 0,
        "execution_logs": []
    }

    final_state = await diagram_graph.ainvoke(initial_state)
    assert final_state["status"] == "completed"
    assert final_state.get("error") is None

    # Agent 1 Check
    assert final_state["content_understanding"] is not None
    assert "CPU Pipeline" in final_state["topic"]
    assert len(final_state["extracted_concepts"]) >= 4

    # Agent 2 Check
    assert final_state["diagram_plan"] is not None
    assert final_state["diagram_type"] == "process"
    assert "flowchart" in final_state["mermaid_code"].lower()

    # Agent 5 Check
    assert final_state["evaluation_score"] is not None
    assert final_state["evaluation_score"] >= 65.0
    assert final_state["quality_output"] is not None

    # Agent 3 Check
    assert final_state["illustration_prompt"] is not None
    assert "CPU Pipeline" in final_state["illustration_prompt"]
    assert final_state["negative_prompt"] is not None

    # Agent 4 Check
    assert final_state["image_url"] is not None
    assert final_state["svg_url"] is not None
    assert final_state["pdf_url"] is not None
    assert final_state["image_is_mock"] is True

    # Audit Logs Check - all 5 agents logged
    logs = final_state["execution_logs"]
    agent_names = [log.get("agent") for log in logs]
    assert "Content Understanding Agent" in agent_names
    assert "Diagram Planning Agent" in agent_names
    assert "Quality Evaluation Agent" in agent_names
    assert "Prompt Engineering Agent" in agent_names
    assert "Image Generation Agent" in agent_names


def test_quality_repair_loop_logic():
    """Verify quality repair condition routes to repair when failed, and respects retry limit."""
    # Failed validation with retry 0 -> routes to repair_increment
    state_retry_0: DiagramAgentState = {
        "evaluation_passed": False,
        "retry_count": 0,
        "evaluation_score": 50.0
    }
    assert check_quality_repair_loop(state_retry_0) == "repair_increment"

    # Failed validation with retry 1 -> routes to repair_increment
    state_retry_1: DiagramAgentState = {
        "evaluation_passed": False,
        "retry_count": 1,
        "evaluation_score": 55.0
    }
    assert check_quality_repair_loop(state_retry_1) == "repair_increment"

    # Failed validation with retry 2 (max reached) -> terminates repair loop, moves forward
    state_retry_2: DiagramAgentState = {
        "evaluation_passed": False,
        "retry_count": 2,
        "evaluation_score": 60.0
    }
    assert check_quality_repair_loop(state_retry_2) == "prompt_engineering"

    # Passed validation -> moves forward immediately without repair
    state_passed: DiagramAgentState = {
        "evaluation_passed": True,
        "retry_count": 0,
        "evaluation_score": 92.0
    }
    assert check_quality_repair_loop(state_passed) == "prompt_engineering"


@pytest.mark.asyncio
async def test_api_full_crud_and_exports():
    """Test POST /start, GET /stats/summary, GET list, GET detail, export SVG/PNG/PDF, and DELETE."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start Generation
        payload = {
            "text_input": (
                "Course: Compiler Design\n"
                "Lexical analysis transforms source characters into meaningful tokens.\n"
                "Syntax analysis validates grammar using context-free grammars and AST trees.\n"
                "Semantic analysis checks type correctness and scope resolution.\n"
                "Code generation synthesizes target machine instructions."
            ),
            "diagram_type": "process",
            "illustration_style": "flat_vector",
            "complexity_level": "advanced",
            "generate_illustration": True
        }
        create_res = await client.post("/api/v1/generations/start", json=payload)
        assert create_res.status_code == 200
        gen_data = create_res.json()
        gen_id = gen_data["generation_id"]
        assert gen_data["diagram_type"] == "process"
        assert gen_data["quality_score"] is not None
        assert gen_data["image_url"] is not None
        assert gen_data["svg_url"] is not None
        assert gen_data["pdf_url"] is not None

        # 2. Get Statistics Summary
        stats_res = await client.get("/api/v1/generations/stats/summary")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_generations"] >= 1
        assert stats["total_illustrations"] >= 1
        assert stats["average_quality_score"] > 0

        # 3. List Generations
        list_res = await client.get("/api/v1/generations")
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(item["id"] == gen_id for item in items)

        # 4. Search Filter
        search_res = await client.get("/api/v1/generations?search=Compiler")
        assert search_res.status_code == 200
        assert len(search_res.json()) >= 1

        # 5. Get Generation Detail, including a legacy Mermaid directive.
        legacy_code = (
            "mindmap\n"
            " root((Compiler Design))\n"
            "  Lexical Analysis\n"
            "   Core Concept\n"
            "    ::icon(fa fa-book) Converts source characters into tokens\n"
            "  Syntax Analysis\n"
            "   Core Concept\n"
            "    ::icon(fa fa-book) Validates grammar structure\n"
        )
        async with async_session_maker() as db:
            record = await db.get(Generation, gen_id)
            record.diagram_code = legacy_code
            await db.commit()

        detail_res = await client.get(f"/api/v1/generations/{gen_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == gen_id
        assert detail["illustration_style"] == "flat_vector"
        assert len(detail["execution_logs"]) >= 5
        assert detail["diagram_code"] == (
            "mindmap\n"
            " root((Compiler Design))\n"
            "  Lexical Analysis\n"
            "  Syntax Analysis"
        )
        async with async_session_maker() as db:
            record = await db.get(Generation, gen_id)
            assert record.diagram_code == legacy_code

        # 6. Status Endpoint
        status_res = await client.get(f"/api/v1/generations/{gen_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "completed"

        # 7. Export SVG
        svg_res = await client.get(f"/api/v1/generations/{gen_id}/export/svg")
        assert svg_res.status_code == 200
        assert "image/svg+xml" in svg_res.headers.get("content-type", "")

        # 8. Export PNG
        png_res = await client.get(f"/api/v1/generations/{gen_id}/export/png")
        assert png_res.status_code == 200
        assert "image/png" in png_res.headers.get("content-type", "")

        # 9. Export Multi-page Course PDF
        pdf_res = await client.get(f"/api/v1/generations/{gen_id}/export/pdf")
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers.get("content-type", "")
        assert len(pdf_res.content) > 1000

        # 10. Delete Generation
        del_res = await client.delete(f"/api/v1/generations/{gen_id}")
        assert del_res.status_code == 200

        # Verify 404 after delete
        not_found_res = await client.get(f"/api/v1/generations/{gen_id}")
        assert not_found_res.status_code == 404
