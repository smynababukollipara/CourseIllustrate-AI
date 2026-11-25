import time
import logging
import re
from typing import Dict, Any

from app.agents.state import DiagramAgentState
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

_INSTRUCTION_LABEL = re.compile(
    r"^(?:create|include|generate|show|add|draw|build|produce)\b|"
    r"^(?:start|outcome|key takeaway)\b|^the resulting poster\b",
    re.IGNORECASE,
)


async def diagram_planning_node(state: DiagramAgentState) -> Dict[str, Any]:
    """
    Agent 2: Diagram Planning Agent.
    Transforms structured educational concepts into validated Mermaid.js diagram code
    matching the user's preferred visual format (flowchart, mindmap, concept_map, architecture,
    process, hierarchical, comparison).
    Incorporates repair feedback if invoked from the Quality Repair Loop.
    """
    logger.info("Executing Diagram Planning Agent...")
    start_time = time.time()
    provider = get_llm_provider()

    content = state.get("content_understanding")
    if not content:
        return {
            "status": "error",
            "error": "Diagram Planning Agent cannot run: missing Content Understanding output."
        }

    dtype = state.get("requested_diagram_type", "flowchart")
    custom_focus = state.get("custom_focus")
    repair_feedback = state.get("evaluation_feedback")
    retry_count = state.get("retry_count", 0)

    agent_status = dict(state.get("agent_status", {}))
    agent_status["diagram_planning"] = "running"

    try:
        plan = await provider.plan_diagram(
            content=content,
            preferred_diagram_type=dtype,
            custom_focus=custom_focus,
            repair_feedback=repair_feedback
        )
        plan.nodes = [
            node for node in plan.nodes
            if not _INSTRUCTION_LABEL.search(node.label.strip())
        ]
        node_ids = {node.id for node in plan.nodes}
        plan.connections = [
            edge for edge in plan.connections
            if edge.source in node_ids and edge.target in node_ids
        ]
        plan.node_count = len(plan.nodes)
        duration_ms = int((time.time() - start_time) * 1000)

        action_desc = f"Planned and synthesized {plan.diagram_type} Mermaid diagram ({plan.node_count} nodes)"
        if repair_feedback:
            action_desc += f" [Repair attempt #{retry_count}]"

        log_entry = {
            "agent": "Diagram Planning Agent",
            "action": action_desc,
            "diagram_type": plan.diagram_type,
            "nodes_planned": plan.node_count,
            "connections_planned": len(plan.connections),
            "duration_ms": duration_ms,
            "is_mock": provider.is_mock,
            "provider": provider.provider_name
        }

        logs = list(state.get("execution_logs", []))
        logs.append(log_entry)
        agent_status["diagram_planning"] = "completed"

        diagram_spec = {
            "title": plan.title or content.title,
            "diagram_type": plan.diagram_type,
            "nodes": [n.model_dump() for n in plan.nodes],
            "connections": [c.model_dump() for c in plan.connections],
            "layout": plan.layout_instructions
        }

        return {
            "diagram_type": plan.diagram_type,
            "mermaid_code": plan.mermaid_code,
            "explanation": plan.explanation,
            "diagram_spec": diagram_spec,
            "diagram_plan": plan,
            "status": "diagram_planned",
            "current_agent": "diagram_planning",
            "agent_status": agent_status,
            "execution_logs": logs
        }

    except Exception as exc:
        logger.exception("Error in Diagram Planning Agent: %s", exc)
        agent_status["diagram_planning"] = "failed"
        return {
            "status": "error",
            "error": f"Diagram Planning Agent failed: {str(exc)}",
            "current_agent": "diagram_planning",
            "agent_status": agent_status
        }
