import re
import time
import logging
from typing import Dict, Any, List, Tuple

from app.config import settings
from app.agents.state import DiagramAgentState
from app.schemas.generation import QualityEvaluationOutput, QualityCriterion
from app.services.poster_renderer import build_educational_poster_svg

logger = logging.getLogger(__name__)


def validate_mermaid_syntax(code: str) -> Tuple[bool, List[str]]:
    """
    Deterministic structural validation of Mermaid.js code.
    Checks valid directives, balanced enclosures, and connector validity.
    """
    errors: List[str] = []
    if not code or not code.strip():
        return False, ["Mermaid diagram code is empty."]

    cleaned = code.strip()
    lines = [l.strip() for l in cleaned.splitlines() if l.strip() and not l.strip().startswith("%%")]

    if not lines:
        return False, ["Diagram contains no executable Mermaid statements."]

    # 1. Header check
    valid_starters = (
        "flowchart", "graph", "mindmap", "sequencediagram",
        "classdiagram", "erdiagram", "gitgraph", "timeline"
    )
    first_line_lower = lines[0].lower()
    if not any(first_line_lower.startswith(starter) for starter in valid_starters):
        errors.append(f"Invalid Mermaid header directive: '{lines[0]}'. Must start with flowchart, mindmap, etc.")

    # 2. Balanced delimiters check
    delimiter_pairs = [("(", ")"), ("[", "]"), ("{", "}")]
    for open_ch, close_ch in delimiter_pairs:
        # Ignore delimiters inside quoted strings
        unquoted = re.sub(r'"[^"]*"', '', cleaned)
        unquoted = re.sub(r"'[^']*'", '', unquoted)
        open_count = unquoted.count(open_ch)
        close_count = unquoted.count(close_ch)
        if open_count != close_count:
            errors.append(
                f"Mismatched delimiter '{open_ch}{close_ch}': {open_count} opening vs {close_count} closing."
            )

    # 3. Check for illegal unquoted brackets inside node labels
    label_pattern = re.compile(r'\[([^"\]]+\[[^"\]]+)\]')
    if label_pattern.search(cleaned):
        errors.append("Nested unquoted brackets detected inside node definition.")

    return len(errors) == 0, errors


def evaluate_concept_coverage(
    concepts: List[Any],
    mermaid_code: str
) -> Tuple[float, List[str], List[str]]:
    """
    Checks whether required core and secondary concepts appear in the diagram.
    """
    if not concepts:
        return 100.0, [], []

    missing: List[str] = []
    found: List[str] = []
    code_lower = mermaid_code.lower()

    for c in concepts:
        c_name = getattr(c, "name", str(c)).lower()
        c_id = getattr(c, "id", "").lower()
        # Clean special chars
        clean_name = re.sub(r"[^a-z0-9\s]", "", c_name)
        tokens = [t for t in clean_name.split() if len(t) > 3]

        if c_id and c_id in code_lower:
            found.append(c_name)
        elif c_name in code_lower:
            found.append(c_name)
        else:
            clean_name = re.sub(r"[^a-z0-9\s]", "", c_name)
            tokens = [t for t in clean_name.split() if len(t) >= 4]
            if tokens and all(token in code_lower for token in tokens):
                found.append(c_name)
            else:
                missing.append(getattr(c, "name", str(c)))

    score = (len(found) / len(concepts)) * 100.0
    return score, found, missing


def evaluate_structural_connectivity(mermaid_code: str, diagram_type: str) -> Tuple[float, List[str]]:
    """
    Checks that the diagram is not a disconnected set of orphan nodes.
    """
    issues: List[str] = []
    if diagram_type.lower() == "mindmap":
        # Mind maps use indentation hierarchies rather than arrows
        lines = [l for l in mermaid_code.splitlines() if l.strip()]
        if len(lines) < 2:
            issues.append("Mind map has fewer than 2 nodes.")
            return 40.0, issues
        return 95.0, []

    # For flowcharts, architecture, concept maps, process, check connector presence
    connectors = ["-->", "---", "-.->", "==>", "--o", "--x", "<-.->", "<-->"]
    conn_count = sum(mermaid_code.count(c) for c in connectors)

    # Approximate node definitions
    node_matches = re.findall(r'(\w+)\s*(\[|\(|\{)', mermaid_code)
    node_count = len(node_matches)

    if node_count > 1 and conn_count == 0:
        issues.append("Diagram contains multiple nodes but zero relational connections.")
        return 30.0, issues

    if node_count > 0 and conn_count < (node_count // 2):
        issues.append("Low connectivity: several nodes appear disconnected.")
        return 65.0, issues

    return 95.0, []


async def quality_evaluation_node(state: DiagramAgentState) -> Dict[str, Any]:
    """
    Agent 5: Quality Evaluation Agent.
    Validates Mermaid syntax, checks concept coverage and relational fidelity,
    calculates a quality score (1-10 / 0-100), and generates correction feedback
    for the Quality Repair Loop if needed.
    """
    logger.info("Executing Quality Evaluation Agent...")
    start_time = time.time()
    agent_status = dict(state.get("agent_status", {}))
    agent_status["quality_evaluation"] = "running"

    plan = state.get("diagram_plan")
    content = state.get("content_understanding")
    mermaid_code = state.get("mermaid_code") or (plan.mermaid_code if plan else "")
    diagram_type = state.get("diagram_type") or (plan.diagram_type if plan else "flowchart")
    concepts = state.get("extracted_concepts") or (content.key_concepts if content else [])

    threshold = float(getattr(settings, "QUALITY_THRESHOLD", 70.0))
    problems: List[str] = []
    suggestions: List[str] = []
    criteria: List[QualityCriterion] = []

    # 1. Syntax Validation
    syntax_valid, syntax_errors = validate_mermaid_syntax(mermaid_code)
    syntax_score = 100.0 if syntax_valid else 20.0
    if not syntax_valid:
        problems.extend(syntax_errors)
        suggestions.append("Fix mismatched brackets and verify valid Mermaid directive.")
    # 2. Concept Coverage
    coverage_score, found_c, missing_c = evaluate_concept_coverage(concepts, mermaid_code)
    if missing_c:
        problems.append(f"Missing core concepts in diagram: {', '.join(missing_c[:3])}")
        suggestions.append(f"Incorporate missing concepts into diagram nodes: {', '.join(missing_c[:3])}")
    # 3. Connectivity & Relationships
    conn_score, conn_issues = evaluate_structural_connectivity(mermaid_code, diagram_type)
    if plan and plan.nodes and not plan.connections:
        conn_score = min(conn_score, 35.0)
        conn_issues.append("Structured poster plan contains no explicit relationships.")
    if conn_issues:
        problems.extend(conn_issues)
        suggestions.append("Ensure every concept node is connected to an upstream or downstream concept.")
    instruction_nodes = [
        node.label for node in (plan.nodes if plan else [])
        if re.match(
            r"^(?:create|include|generate|show|add|draw|build|produce|start\b|outcome\b|key takeaway\b)",
            node.label.strip(),
            re.IGNORECASE,
        )
    ]
    if instruction_nodes:
        problems.append(f"Poster contains prompt instructions as concept nodes: {', '.join(instruction_nodes[:3])}.")
        suggestions.append("Remove user formatting instructions from the diagram concept list.")
    # 4. Poster layout validation
    poster_audit = None
    poster_errors: List[str] = []
    if plan:
        try:
            _, poster_audit = build_educational_poster_svg(
                title=state.get("topic") or (content.title if content else "Educational Topic"),
                diagram_type=diagram_type,
                nodes=plan.nodes,
                connections=plan.connections,
                summary=(content.summary if content else state.get("educational_summary", "")) or "",
                main_subject=(content.main_subject if content else "") or (content.title if content else ""),
                concepts=concepts,
                relationships=(content.relationships if content else state.get("relationships", [])) or [],
                learning_objectives=(content.learning_objectives if content else state.get("learning_objectives", [])) or [],
                key_equations=(content.key_equations if content else []) or [],
                poster_settings=state.get("poster_settings"),
                mock_banner=state.get("is_mock", True),
            )
            poster_errors.extend(poster_audit.errors)
        except (ValueError, TypeError) as exc:
            poster_errors.append(str(exc))
    else:
        poster_errors.append("No structured diagram plan is available for poster layout validation.")

    if poster_errors:
        problems.extend(poster_errors)
        suggestions.append("Correct the structured nodes and relationships, then regenerate the poster layout.")

    poster_layout_score = 100.0 if poster_audit and poster_audit.valid else 35.0
    if poster_audit:
        poster_layout_score = min(poster_layout_score, poster_audit.balance_score)
    readability_score = 100.0
    if poster_audit:
        readability_score -= min(60.0, poster_audit.clipped_text_count * 10.0)
        if poster_audit.contrast_ratio < 4.5:
            readability_score = min(readability_score, 55.0)
        if poster_audit.min_font_size < 14:
            readability_score = min(readability_score, 60.0)
        elif poster_audit.min_font_size < 16:
            readability_score = min(readability_score, 78.0)
    else:
        readability_score = 35.0

    hierarchy_score = 92.0 if poster_audit and poster_audit.rendered_node_count > 1 else 55.0
    if poster_audit and poster_audit.overlap_count:
        hierarchy_score = min(hierarchy_score, 45.0)

    clarity_score = 90.0 if coverage_score >= 70.0 and conn_score >= 70.0 else 60.0
    svg_score = 100.0 if poster_audit and poster_audit.svg_valid else 20.0
    balance_score = poster_audit.balance_score if poster_audit else 35.0
    illustration_score = poster_audit.illustration_relevance if poster_audit else 25.0
    instruction_score = 20.0 if instruction_nodes else 100.0

    criteria.extend([
        QualityCriterion(
            name="Content & Concept Completeness",
            score=round(coverage_score, 1),
            notes=f"{len(found_c)} of {len(concepts)} extracted concepts are represented."
        ),
        QualityCriterion(
            name="Relationship Integrity",
            score=round(conn_score, 1),
            notes="Proper edge connections between dependent concepts." if not conn_issues else "; ".join(conn_issues)
        ),
        QualityCriterion(
            name="Structural Validity",
            score=syntax_score,
            notes="Mermaid structure and delimiters are valid." if syntax_valid else "; ".join(syntax_errors)
        ),
        QualityCriterion(
            name="Educational Clarity",
            score=clarity_score,
            notes="Based on concept coverage and relationships, not syntax alone."
        ),
        QualityCriterion(
            name="Layout Completeness",
            score=poster_layout_score,
            notes=f"{poster_audit.rendered_node_count if poster_audit else 0} of {poster_audit.node_count if poster_audit else 0} nodes fit the poster."
        ),
        QualityCriterion(
            name="Text Readability",
            score=readability_score,
            notes=f"Measured contrast: {poster_audit.contrast_ratio:.2f}:1." if poster_audit else "Poster text could not be measured."
        ),
        QualityCriterion(
            name="Visual Hierarchy",
            score=hierarchy_score,
            notes=f"Evaluated {poster_audit.layout_strategy if poster_audit else 'unavailable'} layout hierarchy."
        ),
        QualityCriterion(
            name="Layout Balance",
            score=balance_score,
            notes="Deterministic layout occupancy and alignment heuristic; not a human visual review."
        ),
        QualityCriterion(
            name="Illustration Relevance",
            score=illustration_score,
            notes="Reports topic-specific vector scene selection; the vector art is not diffusion generated."
        ),
        QualityCriterion(
            name="Prompt Contamination",
            score=instruction_score,
            notes="Checks that design instructions are not presented as educational concept nodes."
        ),
        QualityCriterion(
            name="Poster SVG Validity",
            score=svg_score,
            notes="Generated SVG parses as valid XML." if svg_score == 100.0 else "Poster SVG could not be validated."
        ),
    ])

    # Valid content and Mermaid syntax alone cannot guarantee a successful poster.
    overall_score = round(
        coverage_score * 0.18
        + conn_score * 0.13
        + syntax_score * 0.10
        + clarity_score * 0.09
        + poster_layout_score * 0.14
        + readability_score * 0.10
        + hierarchy_score * 0.08
        + balance_score * 0.05
        + illustration_score * 0.04
        + instruction_score * 0.04
        + svg_score * 0.05,
        1
    )
    passed = (
        overall_score >= threshold
        and syntax_valid
        and bool(poster_audit and poster_audit.valid)
        and not instruction_nodes
    )

    feedback = ""
    if not passed:
        feedback = f"Quality check failed (Score {overall_score}/{threshold}). Issues: " + "; ".join(problems)
        if suggestions:
            feedback += f" Suggestions: " + "; ".join(suggestions)
    else:
        feedback = f"Diagram validated successfully. Score: {overall_score}/100. All key educational concepts covered."

    quality_output = QualityEvaluationOutput(
        overall_score=overall_score,
        passed=passed,
        threshold=threshold,
        criteria=criteria,
        problems=problems,
        suggestions=suggestions,
        evaluation_method="structural",
        method_note="Deterministic structural and semantic concept coverage audit.",
        is_mock=state.get("is_mock", True),
        provider_info="Quality Evaluation Agent (Deterministic Structural Verifier)"
    )

    duration_ms = int((time.time() - start_time) * 1000)
    retry_count = state.get("retry_count", 0)

    log_entry = {
        "agent": "Quality Evaluation Agent",
        "action": f"Evaluated diagram quality: score={overall_score}/100, passed={passed}",
        "syntax_valid": syntax_valid,
        "concept_coverage_percent": round(coverage_score, 1),
        "score_out_of_10": round(overall_score / 10.0, 1),
        "retry_attempt": retry_count,
        "problems_count": len(problems),
        "duration_ms": duration_ms,
        "is_mock": quality_output.is_mock,
        "provider": quality_output.provider_info
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)
    agent_status["quality_evaluation"] = "completed"

    return {
        "evaluation_score": overall_score,
        "evaluation_passed": passed,
        "evaluation_feedback": feedback,
        "quality_output": quality_output,
        "status": "quality_evaluated",
        "current_agent": "quality_evaluation",
        "agent_status": agent_status,
        "execution_logs": logs
    }
