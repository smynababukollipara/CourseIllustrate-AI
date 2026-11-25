import logging
from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, START, END

from app.config import settings
from app.agents.state import DiagramAgentState
from app.agents.nodes.content_agent import content_understanding_node
from app.agents.nodes.diagram_agent import diagram_planning_node
from app.agents.nodes.quality_agent import quality_evaluation_node
from app.agents.nodes.prompt_agent import prompt_engineering_node
from app.agents.nodes.image_agent import image_generation_node

logger = logging.getLogger(__name__)


def should_continue_after_content(state: DiagramAgentState) -> str:
    """Proceed to diagram planning only if content understanding succeeded."""
    if state.get("error") or not state.get("content_understanding"):
        logger.warning("Pipeline halting early due to error in Content Understanding Agent.")
        return END  # type: ignore
    return "diagram_planning"


def check_quality_repair_loop(state: DiagramAgentState) -> str:
    """
    Quality repair condition:
    If validation failed and retries < MAX_GENERATION_RETRIES, route through repair loop.
    Otherwise proceed to Prompt Engineering.
    """
    passed = state.get("evaluation_passed", True)
    retries = state.get("retry_count", 0)
    max_retries = getattr(settings, "MAX_GENERATION_RETRIES", 2)

    if not passed and retries < max_retries:
        logger.info(
            "Quality validation failed (score=%s). Routing back for repair (retry %d of %d).",
            state.get("evaluation_score"),
            retries + 1,
            max_retries
        )
        return "repair_increment"

    return "prompt_engineering"


async def repair_increment_node(state: DiagramAgentState) -> Dict[str, Any]:
    """Increments retry count and sets audit status for the repair loop."""
    current_retries = state.get("retry_count", 0) + 1
    logger.info("Executing Quality Repair Loop: starting attempt #%d", current_retries)
    return {
        "retry_count": current_retries,
        "status": f"repairing_diagram_attempt_{current_retries}"
    }


def build_diagram_graph():
    """
    Constructs and compiles the complete 5-agent LangGraph workflow:
    1. Content Understanding Agent
    2. Diagram Planning Agent
    3. Quality Evaluation Agent
    4. Conditional Quality Repair Loop (max 2 retries)
    5. Prompt Engineering Agent
    6. Image Generation Agent
    """
    workflow = StateGraph(DiagramAgentState)

    # 1. Register all 5 agent nodes + repair increment node
    workflow.add_node("content_understanding", content_understanding_node)
    workflow.add_node("diagram_planning", diagram_planning_node)
    workflow.add_node("quality_evaluation", quality_evaluation_node)
    workflow.add_node("repair_increment", repair_increment_node)
    workflow.add_node("prompt_engineering", prompt_engineering_node)
    workflow.add_node("image_generation", image_generation_node)

    # 2. State transitions & edges
    workflow.add_edge(START, "content_understanding")

    workflow.add_conditional_edges(
        "content_understanding",
        should_continue_after_content,
        {
            "diagram_planning": "diagram_planning",
            END: END
        }
    )

    workflow.add_edge("diagram_planning", "quality_evaluation")

    # Quality repair conditional routing
    workflow.add_conditional_edges(
        "quality_evaluation",
        check_quality_repair_loop,
        {
            "repair_increment": "repair_increment",
            "prompt_engineering": "prompt_engineering"
        }
    )

    # Loop back from repair increment to diagram planning
    workflow.add_edge("repair_increment", "diagram_planning")

    # Continue from prompt engineering to image generation
    workflow.add_edge("prompt_engineering", "image_generation")
    workflow.add_edge("image_generation", END)

    compiled = workflow.compile()
    return compiled


# Shared singleton compiled graph instance
diagram_graph = build_diagram_graph()
