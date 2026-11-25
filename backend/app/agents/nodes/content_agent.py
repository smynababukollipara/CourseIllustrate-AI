import time
import logging
import re
from typing import Dict, Any

from app.agents.state import DiagramAgentState
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

_INSTRUCTION_CONCEPTS = re.compile(
    r"^(?:create|include|generate|show|add|draw|build|produce)\b|"
    r"^the resulting poster\b|^the poster must\b|^important:?$",
    re.IGNORECASE,
)


def _normalize_extraction(raw_text: str, understanding):
    """Keep request/design instructions out of the educational topic and node set."""
    text = raw_text.lower()
    topic_markers = (
        ("photosynthesis", "Photosynthesis"),
        ("water cycle", "Water Cycle"),
        ("cpu pipeline", "CPU Pipeline"),
        ("neural network", "Neural Network"),
        ("machine learning", "Machine Learning Workflow"),
    )
    for marker, title in topic_markers:
        if marker in text:
            understanding.title = title
            break

    understanding.key_concepts = [
        concept for concept in understanding.key_concepts
        if not _INSTRUCTION_CONCEPTS.search(concept.name.strip())
        and concept.name.strip().casefold() not in {"start", "outcome", "key takeaway"}
    ]
    return understanding


async def content_understanding_node(state: DiagramAgentState) -> Dict[str, Any]:
    """
    Agent 1: Content Understanding Agent.
    Ingests educational content (from text or PDF) and extracts structured concepts,
    learning objectives, and taxonomic relationships.
    """
    logger.info("Executing Content Understanding Agent...")
    start_time = time.time()
    provider = get_llm_provider()

    raw_text = state.get("raw_content", "")
    custom_focus = state.get("custom_focus")
    agent_status = dict(state.get("agent_status", {}))
    agent_status["content_understanding"] = "running"

    try:
        understanding = await provider.understand_content(
            raw_text=raw_text,
            custom_focus=custom_focus
        )
        understanding = _normalize_extraction(raw_text, understanding)
        duration_ms = int((time.time() - start_time) * 1000)

        log_entry = {
            "agent": "Content Understanding Agent",
            "action": "Extracted key concepts and pedagogical hierarchy",
            "topic": understanding.title,
            "concepts_found": len(understanding.key_concepts),
            "suggested_diagram_type": understanding.suggested_diagram_type,
            "relationships_count": len(understanding.relationships),
            "duration_ms": duration_ms,
            "is_mock": provider.is_mock,
            "provider": provider.provider_name
        }

        logs = list(state.get("execution_logs", []))
        logs.append(log_entry)
        agent_status["content_understanding"] = "completed"

        return {
            "topic": understanding.title,
            "extracted_concepts": understanding.key_concepts,
            "relationships": understanding.relationships,
            "educational_summary": understanding.summary,
            "learning_objectives": understanding.learning_objectives,
            "content_understanding": understanding,
            "status": "content_understood",
            "current_agent": "content_understanding",
            "agent_status": agent_status,
            "is_mock": provider.is_mock,
            "provider": provider.provider_name,
            "execution_logs": logs
        }

    except Exception as exc:
        logger.exception("Error in Content Understanding Agent: %s", exc)
        agent_status["content_understanding"] = "failed"
        return {
            "status": "error",
            "error": f"Content Understanding Agent failed: {str(exc)}",
            "current_agent": "content_understanding",
            "agent_status": agent_status
        }
