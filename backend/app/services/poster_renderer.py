"""Structured, printable SVG poster rendering for educational diagrams."""

import html
import math
import re
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pymupdf

from app.schemas.generation import PosterDesignSettings


THEME_LABELS = {
    "vibrant_educational": "Vibrant Educational",
    "science_technology": "Science & Technology",
    "creative_classroom": "Creative Classroom",
    "professional_infographic": "Professional Infographic",
    "nature_biology": "Nature & Biology",
    "dark_neon_learning": "Dark Neon Learning",
}

THEMES = {
    "vibrant_educational": {
        "background": "#F7F7FF", "surface": "#FFFFFF", "ink": "#18213B",
        "muted": "#536178", "accent": "#5146C8",
        "roles": {"input": "#2376C9", "process": "#7752C9", "memory": "#0786A5",
                  "output": "#16804A", "warning": "#C84D45", "concept": "#5146C8"},
    },
    "science_technology": {
        "background": "#F1F7FC", "surface": "#FFFFFF", "ink": "#10263D",
        "muted": "#486177", "accent": "#076E9A",
        "roles": {"input": "#1769AA", "process": "#6745AD", "memory": "#078B9B",
                  "output": "#12806A", "warning": "#C75043", "concept": "#076E9A"},
    },
    "creative_classroom": {
        "background": "#FFFAF1", "surface": "#FFFFFF", "ink": "#382B25",
        "muted": "#6B5A4E", "accent": "#D87524",
        "roles": {"input": "#3588BC", "process": "#8152B6", "memory": "#168A79",
                  "output": "#45884B", "warning": "#D56234", "concept": "#D87524"},
    },
    "professional_infographic": {
        "background": "#F5F7F8", "surface": "#FFFFFF", "ink": "#1C2A36",
        "muted": "#52616C", "accent": "#315F83",
        "roles": {"input": "#356C91", "process": "#655A8F", "memory": "#287E83",
                  "output": "#397A5B", "warning": "#B96543", "concept": "#315F83"},
    },
    "nature_biology": {
        "background": "#F3F8F1", "surface": "#FFFFFF", "ink": "#1C3328",
        "muted": "#506A56", "accent": "#327044",
        "roles": {"input": "#2875A2", "process": "#50803C", "memory": "#218A83",
                  "output": "#D09B26", "warning": "#C45E36", "concept": "#327044"},
    },
    "dark_neon_learning": {
        "background": "#0B1020", "surface": "#111A32", "ink": "#F2F5FF",
        "muted": "#B8C5E0", "accent": "#A98BFF",
        "roles": {"input": "#45B6FF", "process": "#B27AFF", "memory": "#31D4D4",
                  "output": "#55D68B", "warning": "#FF6688", "concept": "#A98BFF"},
    },
}

SUBJECT_ROLES = {
    "biology": {"input": "#2875A2", "process": "#50803C", "memory": "#218A83",
                "output": "#D09B26", "warning": "#C45E36"},
    "physics": {"input": "#3478C8", "process": "#D87827", "memory": "#7954B8",
                "output": "#23835B", "warning": "#C84D45"},
    "computer_science": {"input": "#2376C9", "process": "#7752C9", "memory": "#0786A5",
                         "output": "#16804A", "warning": "#C84D45"},
    "machine_learning": {"input": "#2376C9", "process": "#0786A5", "memory": "#7752C9",
                         "output": "#16804A", "warning": "#D87827"},
}

_VALID_DIAGRAM_TYPES = {
    "flowchart", "mindmap", "concept_map", "hierarchical", "process",
    "sequence", "architecture", "comparison", "timeline", "tree",
}


@dataclass(frozen=True)
class PosterLayoutAudit:
    node_count: int
    rendered_node_count: int
    relationship_count: int
    overlap_count: int
    clipped_text_count: int
    contrast_ratio: float
    svg_valid: bool
    errors: Tuple[str, ...]
    width: int
    height: int
    layout_strategy: str = "multi_column_infographic"
    balance_score: float = 0.0
    min_font_size: int = 0
    illustration_relevance: float = 0.0

    @property
    def valid(self) -> bool:
        return (
            self.svg_valid
            and self.node_count == self.rendered_node_count
            and self.overlap_count == 0
            and self.clipped_text_count == 0
            and not self.errors
        )


def choose_subject_palette(
    subject: str,
    theme: str = "vibrant_educational",
    color_scheme: str = "subject_aware",
) -> Dict[str, str]:
    """Return stable semantic colors; subject-aware roles override theme accents."""
    theme_key = theme if theme in THEMES else "vibrant_educational"
    palette = dict(THEMES[theme_key]["roles"])
    if color_scheme != "subject_aware":
        return palette

    text = (subject or "").lower()
    if any(word in text for word in ("biology", "photosynthesis", "cell", "ecology", "water cycle")):
        subject_key = "biology"
    elif any(word in text for word in ("physics", "force", "motion", "energy", "mechanics")):
        subject_key = "physics"
    elif any(word in text for word in ("machine learning", "neural network", "model training", "prediction")):
        subject_key = "machine_learning"
    elif any(word in text for word in ("computer", "cpu", "processor", "software", "algorithm")):
        subject_key = "computer_science"
    else:
        return palette

    if theme_key == "dark_neon_learning":
        return palette
    palette.update(SUBJECT_ROLES[subject_key])
    return palette


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise ValueError("Diagram specification entries must be objects.")


def _node_records(nodes: Sequence[Any]) -> List[Dict[str, str]]:
    if not nodes:
        raise ValueError("Poster diagram specification must include at least one node.")
    records: List[Dict[str, str]] = []
    seen = set()
    for raw_node in nodes:
        data = _as_mapping(raw_node)
        node_id = str(data.get("id") or "").strip()
        label = str(data.get("label") or "").strip()
        if not node_id or not label:
            raise ValueError("Every poster node must have a non-empty id and label.")
        if node_id in seen:
            raise ValueError(f"Poster diagram contains duplicate node id '{node_id}'.")
        seen.add(node_id)
        records.append({
            "id": node_id,
            "label": label,
            "description": str(data.get("description") or "").strip(),
            "parent_id": str(data.get("parent_id") or "").strip(),
        })
    return records


def _connection_records(connections: Sequence[Any], node_ids: set) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for raw_connection in connections or []:
        data = _as_mapping(raw_connection)
        source = str(data.get("source") or "").strip()
        target = str(data.get("target") or "").strip()
        if source not in node_ids or target not in node_ids:
            raise ValueError(f"Poster relationship references an unknown node: '{source}' -> '{target}'.")
        if source == target:
            raise ValueError(f"Poster relationship cannot connect node '{source}' to itself.")
        result.append({
            "source": source,
            "target": target,
            "label": str(data.get("label") or "").strip(),
        })
    return result


def _settings(value: Any) -> PosterDesignSettings:
    if isinstance(value, PosterDesignSettings):
        return value
    return PosterDesignSettings.model_validate(value or {})


def _wrap(value: str, max_chars: int) -> List[str]:
    paragraphs = (value or "").splitlines() or [""]
    lines: List[str] = []
    for paragraph in paragraphs:
        wrapped = textwrap.wrap(
            paragraph,
            width=max(1, max_chars),
            break_long_words=True,
            break_on_hyphens=True,
            replace_whitespace=True,
            drop_whitespace=True,
        )
        lines.extend(wrapped or [""])
    return lines


def _category(text: str) -> str:
    value = text.lower()
    if any(word in value for word in ("hazard", "warning", "risk", "limitation", "danger", "error")):
        return "warning"
    if any(word in value for word in ("memory", "cache", "storage", "collection", "water", "register")):
        return "memory"
    if any(word in value for word in ("input", "data", "sunlight", "fetch", "collection", "carbon dioxide")):
        return "input"
    if any(word in value for word in ("output", "result", "oxygen", "glucose", "prediction", "write back", "benefit")):
        return "output"
    if any(word in value for word in ("execution", "training", "process", "energy", "reaction", "evaporation")):
        return "process"
    return "concept"


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgb
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _subject_label(subject: str, topic: str) -> str:
    text = f"{subject} {topic}".lower()
    if "biology" in text or any(word in text for word in ("photosynthesis", "water cycle", "cell", "ecosystem")):
        return "BIOLOGY & LIFE SCIENCE"
    if "physics" in text or any(word in text for word in ("force", "motion", "energy", "mechanics")):
        return "PHYSICS & ENGINEERING"
    if any(word in text for word in ("machine learning", "neural network", "model training")):
        return "MACHINE LEARNING"
    if any(word in text for word in ("computer", "cpu", "processor", "algorithm", "software")):
        return "COMPUTER SCIENCE"
    return (subject or "EDUCATIONAL CONCEPT").upper()


def _svg_lines(
    x: float,
    y: float,
    lines: Sequence[str],
    *,
    font_size: int,
    fill: str,
    weight: int = 400,
    line_height: int = 22,
    anchor: str = "start",
) -> str:
    tspans = "".join(
        f'<tspan x="{x:.1f}" dy="{0 if index == 0 else line_height}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}" '
        f'font-size="{font_size}" font-weight="{weight}" font-family="Inter, Arial, sans-serif">'
        f'{tspans}</text>'
    )


def _icon(category: str, x: float, y: float, color: str) -> str:
    if category == "warning":
        symbol = f'<path d="M12 2 L22 20 H2 Z M12 8 V13 M12 17 V17.2" stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round"/>'
    elif category == "memory":
        symbol = f'<path d="M4 7 C4 4 20 4 20 7 C20 10 4 10 4 7 M4 7 V17 C4 20 20 20 20 17 V7 M4 12 C4 15 20 15 20 12" stroke="{color}" stroke-width="1.8" fill="none"/>'
    elif category == "output":
        symbol = f'<path d="M4 12 L9 17 L20 6" stroke="{color}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    elif category == "input":
        symbol = f'<path d="M4 12 H19 M13 6 L19 12 L13 18" stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    elif category == "process":
        symbol = f'<path d="M5 8 A7 7 0 0 1 18 6 L20 8 M20 8 V3 M20 8 H15 M19 16 A7 7 0 0 1 6 18 L4 16 M4 16 V21 M4 16 H9" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    else:
        symbol = f'<circle cx="12" cy="12" r="7" stroke="{color}" stroke-width="2" fill="none"/><circle cx="12" cy="12" r="2" fill="{color}"/>'
    return f'<g transform="translate({x:.1f} {y:.1f})">{symbol}</g>'


def _callout(
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    description: str,
    color: str,
    ink: str,
    surface: str,
    *,
    shape: str = "rounded",
    font_size: int = 19,
) -> str:
    if shape == "pill":
        radius = min(height / 2, 34)
    elif shape == "circle":
        radius = min(width, height) / 2
    elif shape == "cut":
        radius = 4
    else:
        radius = 18
    title_lines = _wrap(title, max(10, int((width - 36) / (font_size * 0.57))))
    desc_lines = _wrap(description, max(15, int((width - 36) / 8.5))) if description else []
    title_y = y + 34 if shape != "circle" else y + 28
    title_markup = _svg_lines(x + width / 2, title_y, title_lines, font_size=font_size, fill=ink, weight=750, line_height=font_size + 4, anchor="middle")
    markup = (
        f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{radius:.1f}" '
        f'fill="{surface}" stroke="{color}" stroke-width="2.5"/>'
        f'<path d="M {x + 14:.1f} {y + 3:.1f} H {x + width - 14:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
        f'{title_markup}'
    )
    if desc_lines:
        desc_y = title_y + len(title_lines) * (font_size + 4) + 10
        markup += _svg_lines(x + width / 2, desc_y, desc_lines, font_size=14, fill="#536178" if ink != "#F2F5FF" else "#B8C5E0", line_height=19, anchor="middle")
    return markup + "</g>"


def _callout_text_overflows(width: float, height: float, title: str, description: str, font_size: int) -> bool:
    title_lines = _wrap(title, max(10, int((width - 36) / (font_size * 0.57))))
    description_lines = _wrap(description, max(15, int((width - 36) / 8.5))) if description else []
    title_y = 34 + len(title_lines) * (font_size + 4)
    last_baseline = title_y + 10 + max(0, len(description_lines) - 1) * 19
    return last_baseline + 12 > height


def _plant_illustration(cx: float, cy: float, scale: float = 1.0) -> str:
    return (
        f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})">'
        '<ellipse cx="0" cy="214" rx="162" ry="22" fill="#6E9E58" opacity=".2"/>'
        '<path d="M0 190 C-7 125 2 52 0 -18 C-3 -74 7 -122 0 -163" fill="none" stroke="#347A3D" stroke-width="18" stroke-linecap="round"/>'
        '<path d="M0 194 C-42 222 -70 248 -94 282 M0 194 C34 225 62 251 85 282 M-2 198 C-12 236 -20 260 -22 289 M2 198 C12 238 20 261 23 288" fill="none" stroke="#9A6B3C" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M-2 -61 C-112 -139 -183 -89 -149 -32 C-117 21 -49 -6 -2 -47 Z" fill="#55A847" stroke="#347A3D" stroke-width="5"/>'
        '<path d="M2 -106 C101 -193 178 -147 146 -91 C117 -42 50 -58 2 -91 Z" fill="#69B84C" stroke="#347A3D" stroke-width="5"/>'
        '<path d="M-1 4 C-121 -49 -176 8 -133 54 C-99 91 -48 60 -1 19 Z" fill="#78C653" stroke="#347A3D" stroke-width="5"/>'
        '<path d="M2 57 C104 -10 171 38 135 82 C103 122 50 99 2 72 Z" fill="#4B9D43" stroke="#347A3D" stroke-width="5"/>'
        '<path d="M-1 -51 C-57 -72 -101 -70 -145 -47 M4 -94 C57 -121 103 -130 149 -119 M-3 15 C-54 1 -94 8 -135 32 M3 68 C52 48 94 52 137 66" fill="none" stroke="#D8F0B9" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M-39 202 L-28 247 L0 266 L28 247 L39 202 Z" fill="#C77C47" stroke="#9D5736" stroke-width="5"/>'
        '<path d="M-35 216 H35" stroke="#E8B17A" stroke-width="6"/>'
        '<circle cx="15" cy="-111" r="13" fill="#B5E66C"/><circle cx="50" cy="-123" r="10" fill="#B5E66C"/><circle cx="33" cy="-87" r="9" fill="#B5E66C"/>'
        '</g>'
    )


def _cpu_illustration(cx: float, cy: float, scale: float = 1.0, color: str = "#5146C8") -> str:
    return (
        f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="-82" y="-62" width="164" height="124" rx="22" fill="#EEF0FF" stroke-width="8"/>'
        '<rect x="-48" y="-32" width="96" height="64" rx="12" fill="#FFFFFF" stroke-width="5"/>'
        '<path d="M-104 -42 H-82 M-104 -14 H-82 M-104 14 H-82 M-104 42 H-82 M82 -42 H104 M82 -14 H104 M82 14 H104 M82 42 H104 M-54 -84 V-62 M-18 -84 V-62 M18 -84 V-62 M54 -84 V-62 M-54 62 V84 M-18 62 V84 M18 62 V84 M54 62 V84" fill="none" stroke-width="8"/>'
        '<path d="M-28 0 H28 M0 -20 V20" fill="none" stroke="#0786A5" stroke-width="7"/>'
        '</g>'
    )


def _water_scene(cx: float, cy: float, scale: float = 1.0) -> str:
    return (
        f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})">'
        '<circle cx="-165" cy="-127" r="42" fill="#F8C84D"/><path d="M-165 -187 V-168 M-225 -127 H-206 M-124 -168 L-138 -154 M-206 -168 L-192 -154" stroke="#E5A72D" stroke-width="7" stroke-linecap="round"/>'
        '<path d="M-20 -105 C-15 -144 47 -148 63 -110 C104 -125 134 -96 121 -62 H-5 C-28 -69 -38 -92 -20 -105Z" fill="#FFFFFF" stroke="#8FB9D8" stroke-width="6"/>'
        '<path d="M-220 102 Q-105 50 0 102 T220 102 V177 H-220 Z" fill="#5BA9D6"/>'
        '<path d="M-220 132 Q-105 82 0 132 T220 132 M-220 158 Q-105 108 0 158 T220 158" fill="none" stroke="#D9F4FF" stroke-width="7"/>'
        '<path d="M110 100 C95 55 107 11 123 -25 M145 99 C150 52 177 20 196 -4" fill="none" stroke="#39864A" stroke-width="12" stroke-linecap="round"/>'
        '<path d="M119 10 C75 -18 66 8 93 29 M174 26 C202 -5 226 13 194 43" fill="#62B755" stroke="#39864A" stroke-width="5"/>'
        '<path d="M-62 0 C-72 26 -68 39 -62 49 C-56 39 -52 26 -62 0Z M-15 17 C-25 43 -21 56 -15 66 C-9 56 -5 43 -15 17Z" fill="#56A8E8" stroke="#2B83C0" stroke-width="4"/>'
        '</g>'
    )


def _network_illustration(cx: float, cy: float, scale: float = 1.0) -> str:
    layer_x = [-300, -100, 100, 300]
    layer_counts = [3, 4, 4, 2]
    nodes = []
    centers = []
    for x, count in zip(layer_x, layer_counts):
        ys = [(i - (count - 1) / 2) * 90 for i in range(count)]
        centers.append([(x, y) for y in ys])
    for layer in range(len(centers) - 1):
        for x1, y1 in centers[layer]:
            for x2, y2 in centers[layer + 1]:
                nodes.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#8AA0BE" stroke-width="3" opacity=".52"/>')
    for layer_index, layer in enumerate(centers):
        color = ("#2786CF", "#7D57C7", "#1C9B89", "#E0A630")[layer_index]
        for x, y in layer:
            nodes.append(f'<circle cx="{x}" cy="{y}" r="22" fill="#FFFFFF" stroke="{color}" stroke-width="7"/>')
            nodes.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
    return f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})">' + "".join(nodes) + "</g>"


def _machine_learning_illustration(cx: float, cy: float, scale: float = 1.0) -> str:
    return (
        f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})">'
        '<rect x="-250" y="-86" width="154" height="172" rx="22" fill="#FFFFFF" stroke="#2376C9" stroke-width="7"/>'
        '<path d="M-220 -46 H-126 M-220 -16 H-144 M-220 14 H-126 M-220 44 H-154" stroke="#64A7D9" stroke-width="9" stroke-linecap="round"/>'
        '<path d="M-70 0 H36 M18 -18 L38 0 L18 18" fill="none" stroke="#0786A5" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
        '<rect x="54" y="-88" width="150" height="176" rx="24" fill="#F2F0FF" stroke="#7752C9" stroke-width="7"/>'
        '<path d="M88 -38 L128 -5 L172 -44 M88 8 L128 40 L172 8" fill="none" stroke="#9D87DD" stroke-width="5"/>'
        '<circle cx="88" cy="-38" r="13" fill="#2376C9"/><circle cx="128" cy="-5" r="13" fill="#0786A5"/>'
        '<circle cx="172" cy="-44" r="13" fill="#7752C9"/><circle cx="88" cy="8" r="13" fill="#16804A"/>'
        '<circle cx="128" cy="40" r="13" fill="#0786A5"/><circle cx="172" cy="8" r="13" fill="#D87827"/>'
        '<text x="-173" y="126" text-anchor="middle" fill="#536178" font-size="17" font-weight="800" font-family="Inter, Arial, sans-serif">DATA</text>'
        '<text x="129" y="126" text-anchor="middle" fill="#536178" font-size="17" font-weight="800" font-family="Inter, Arial, sans-serif">MODEL</text>'
        '</g>'
    )


def _specialized_poster(
    *,
    title: str,
    diagram_type: str,
    records: Sequence[Dict[str, str]],
    links: Sequence[Dict[str, str]],
    summary: str,
    main_subject: str,
    concepts: Sequence[Any],
    relationships: Sequence[str],
    learning_objectives: Sequence[str],
    key_equations: Sequence[str],
    settings: PosterDesignSettings,
    mock_banner: bool,
) -> Tuple[str, PosterLayoutAudit] | None:
    lowered = title.lower()
    topic = (
        "photosynthesis" if "photosynthesis" in lowered
        else "water_cycle" if "water cycle" in lowered
        else "cpu_pipeline" if "cpu" in lowered and "pipeline" in lowered
        else "neural_network" if "neural network" in lowered
        else "ai_ml_hierarchy" if "deep learning" in lowered and ("artificial intelligence" in lowered or "machine learning" in lowered)
        else "machine_learning" if "machine learning" in lowered
        else None
    )
    if not topic:
        return None
    if len(records) < 3:
        return None

    palette = THEMES[settings.theme]
    roles = choose_subject_palette(
        f"{main_subject} {title}",
        settings.theme,
        settings.color_scheme,
    )
    background, surface, ink, muted = (
        palette["background"], palette["surface"], palette["ink"], palette["muted"]
    )
    width, height = {
        "portrait": (1200, 1600),
        "landscape": (1600, 1000),
        "square": (1200, 1200),
        "presentation_16_9": (1600, 900),
    }[settings.orientation]
    margin = 52 if width <= 1200 else 72

    def find_node(*terms: str) -> Dict[str, str] | None:
        for node in records:
            label = node["label"].lower()
            if any(term in label for term in terms):
                return node
        return None

    def concepts_by_name(*terms: str) -> List[Tuple[str, str]]:
        items = []
        for raw in concepts:
            data = _as_mapping(raw)
            name, definition = str(data.get("name") or "").strip(), str(data.get("definition") or "").strip()
            if name and any(term in name.lower() for term in terms):
                items.append((name, definition))
        return items

    clipped_callouts = 0

    def render_callout(x: float, y: float, w: float, h: float, label: str, description: str, color: str, shape: str, font_size: int) -> str:
        nonlocal clipped_callouts
        if _callout_text_overflows(w, h, label, description, font_size):
            clipped_callouts += 1
        return _callout(x, y, w, h, label, description, color, ink, surface, shape=shape, font_size=font_size)

    def make_callout(node: Dict[str, str] | None, x: float, y: float, w: float, h: float, role: str, shape: str = "rounded", font_size: int = 18) -> str:
        if not node:
            return ""
        label = re.sub(r"^Stage \d+:\s*", "", node["label"])
        return render_callout(x, y, w, h, label, node["description"], roles[role], shape, font_size)

    header_title = "PHOTOSYNTHESIS" if topic == "photosynthesis" else title.upper()
    subtitle = (
        "How green plants convert sunlight into chemical energy."
        if topic == "photosynthesis"
        else summary
    )
    subtitle_lines = _wrap(subtitle, 104 if width == 1200 else 145)
    header_height = 230 if height >= 1200 else 178
    font_title = 48 if height >= 1200 else 43
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="poster-title poster-desc" preserveAspectRatio="xMidYMin meet">',
        f'<title id="poster-title">{html.escape(header_title.title())}</title>',
        f'<desc id="poster-desc">{html.escape(subtitle)}</desc>',
        f'<defs><marker id="topic-arrow" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto"><path d="M0 0 L12 6 L0 12 z" fill="{roles["process"]}"/></marker><linearGradient id="hero-wash" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{roles["input"]}" stop-opacity=".10"/><stop offset="1" stop-color="{roles["output"]}" stop-opacity=".10"/></linearGradient></defs>',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        f'<rect x="0" y="0" width="{width}" height="{header_height}" fill="{surface}"/>',
        f'<rect x="{margin}" y="28" width="12" height="28" rx="6" fill="{palette["accent"]}"/>',
        f'<text x="{margin + 26}" y="49" fill="{muted}" font-size="15" font-weight="800" letter-spacing="1.7" font-family="Inter, Arial, sans-serif">{html.escape(_subject_label(main_subject, title))}</text>',
        _svg_lines(margin, 112 if height >= 1200 else 100, [header_title], font_size=font_title, fill=ink, weight=850, line_height=font_title + 6),
        _svg_lines(margin, 155 if height >= 1200 else 140, subtitle_lines, font_size=18, fill=muted, line_height=25),
        f'<path d="M {margin} {header_height - 12} H {width - margin}" stroke="{palette["accent"]}" stroke-width="4" stroke-linecap="round"/>',
    ]
    if mock_banner:
        parts.append(f'<text x="{width - margin}" y="49" text-anchor="end" fill="{muted}" font-size="12" font-weight="700" font-family="Inter, Arial, sans-serif">STRUCTURED SVG ILLUSTRATION · NOT DIFFUSION</text>')

    rendered = set()
    overlap_count = 0
    layout_strategy = topic
    min_font = 14
    equation_list = list(key_equations or [])
    takeaway_items = [str(item).strip() for item in (learning_objectives or []) if str(item).strip()]
    if topic == "photosynthesis":
        if not equation_list:
            equation_list = ["6CO2 + 6H2O + Light Energy → C6H12O6 + 6O2"]
        sunlight = find_node("sunlight", "light")
        co2 = find_node("carbon dioxide")
        water = find_node("water")
        chlorophyll = find_node("chlorophyll")
        chloroplasts = find_node("chloroplast")
        glucose = find_node("glucose")
        oxygen = find_node("oxygen")
        light_reactions = find_node("light-dependent", "light dependent")
        calvin = find_node("calvin cycle")
        for node in (sunlight, co2, water, chlorophyll, chloroplasts, glucose, oxygen, light_reactions, calvin):
            if node:
                rendered.add(node["id"])
        if not takeaway_items:
            takeaway_items = [
                "Photosynthesis converts light energy into chemical energy.",
                "Chlorophyll absorbs light.",
                "Oxygen is released.",
                "Glucose supports plant growth.",
            ]

        hero_y = header_height + 28
        hero_height = 600 if height >= 1200 else 370
        center_x = width / 2
        plant_scale = 1.0 if height >= 1200 else 0.48
        plant_y = hero_y + hero_height * (0.53 if height >= 1200 else 0.56)
        parts.extend([
            f'<rect x="{margin}" y="{hero_y}" width="{width - margin * 2}" height="{hero_height}" rx="30" fill="url(#hero-wash)"/>',
            f'<circle cx="{center_x - 125:.1f}" cy="{hero_y + 110:.1f}" r="49" fill="#F7C948"/>',
            f'<path d="M{center_x - 125:.1f} {hero_y + 36:.1f} V{hero_y + 14:.1f} M{center_x - 199:.1f} {hero_y + 110:.1f} H{center_x - 221:.1f} M{center_x - 52:.1f} {hero_y + 110:.1f} H{center_x - 30:.1f} M{center_x - 178:.1f} {hero_y + 58:.1f} L{center_x - 194:.1f} {hero_y + 42:.1f} M{center_x - 72:.1f} {hero_y + 58:.1f} L{center_x - 56:.1f} {hero_y + 42:.1f}" stroke="#E4A92C" stroke-width="8" stroke-linecap="round"/>',
            _plant_illustration(center_x, plant_y - 105, plant_scale),
            f'<path d="M{center_x - 300:.1f} {hero_y + 128:.1f} C{center_x - 210:.1f} {hero_y + 132:.1f} {center_x - 164:.1f} {hero_y + 177:.1f} {center_x - 91:.1f} {hero_y + 214:.1f}" fill="none" stroke="#E6AD32" stroke-width="7" stroke-dasharray="11 10" marker-end="url(#topic-arrow)"/>',
            f'<path d="M{center_x - 250:.1f} {hero_y + 342:.1f} C{center_x - 165:.1f} {hero_y + 342:.1f} {center_x - 142:.1f} {hero_y + 330:.1f} {center_x - 96:.1f} {hero_y + 325:.1f}" fill="none" stroke="{roles["input"]}" stroke-width="7" marker-end="url(#topic-arrow)"/>',
            f'<path d="M{center_x + 160:.1f} {hero_y + 302:.1f} C{center_x + 222:.1f} {hero_y + 282:.1f} {center_x + 260:.1f} {hero_y + 252:.1f} {center_x + 310:.1f} {hero_y + 228:.1f}" fill="none" stroke="{roles["output"]}" stroke-width="7" marker-end="url(#topic-arrow)"/>',
        ])
        slot_y = [hero_y + 22, hero_y + 168, hero_y + 314, hero_y + 460] if height >= 1200 else [hero_y + 8, hero_y + 98, hero_y + 188, hero_y + 278]
        left_slots = [sunlight, co2, water, chlorophyll]
        right_slots = [oxygen, glucose, chloroplasts, None]
        slot_h = 126 if height >= 1200 else 82
        slot_w = 298 if width == 1200 else 340
        left_x = margin + 14
        right_x = width - margin - slot_w - 14
        for i, node in enumerate(left_slots):
            if i < len(slot_y):
                parts.append(make_callout(node, left_x, slot_y[i], slot_w, slot_h, ("input", "input", "memory", "process")[i], "pill" if i == 0 else "rounded", 17 if height >= 1200 else 14))
        for i, node in enumerate(right_slots):
            if i < len(slot_y) and node:
                parts.append(make_callout(node, right_x, slot_y[i], slot_w, slot_h, ("output", "output", "process", "concept")[i], "pill" if i == 0 else "rounded", 17 if height >= 1200 else 14))

        if height >= 1200:
            process_y, process_h = hero_y + hero_height + 24, 182
            process_w, process_gap = (width - 2 * margin - 24) / 2, 24
            for idx, (node, title_text, description, color) in enumerate((
                (light_reactions, "Light-Dependent Reactions", "Capture light energy and convert it into chemical energy.", roles["input"]),
                (calvin, "Calvin Cycle", "Uses carbon dioxide and chemical energy to build sugars.", roles["process"]),
            )):
                x = margin + idx * (process_w + process_gap)
                parts.append(render_callout(x, process_y, process_w, process_h, node["label"] if node else title_text, node["description"] if node else description, color, "cut", 20))
            eq_y = process_y + process_h + 22
            eq_h = 90
            takeaway_y = eq_y + eq_h + 24
            takeaway_h = min(170, max(104, (height - takeaway_y - 44)))
        else:
            process_y, process_h = hero_y + hero_height + 8, 92
            process_w, process_gap = (width - 2 * margin - 18) / 2, 18
            for idx, (node, title_text, description, color) in enumerate((
                (light_reactions, "Light-Dependent Reactions", "Capture light energy and form chemical energy.", roles["input"]),
                (calvin, "Calvin Cycle", "Uses carbon dioxide to produce sugar.", roles["process"]),
            )):
                x = margin + idx * (process_w + process_gap)
                parts.append(render_callout(x, process_y, process_w, process_h, node["label"] if node else title_text, node["description"] if node else description, color, "cut", 16))
            eq_y = process_y + process_h + 12
            eq_h = 62
            takeaway_y = eq_y + eq_h + 12
            takeaway_h = max(80, height - takeaway_y - 28)
        parts.append(f'<rect x="{margin}" y="{eq_y}" width="{width - 2 * margin}" height="{eq_h}" rx="24" fill="#FFF2C8" stroke="#E2AD2D" stroke-width="2"/>')
        parts.append(_svg_lines(width / 2, eq_y + (29 if height < 1200 else 35), ["PHOTOSYNTHESIS EQUATION"], font_size=13 if height < 1200 else 15, fill="#7C5B12", weight=800, anchor="middle"))
        parts.append(_svg_lines(width / 2, eq_y + (54 if height < 1200 else 72), _wrap(equation_list[0], 58 if height < 1200 else 74), font_size=19 if height < 1200 else 25, fill="#28331F", weight=800, anchor="middle", line_height=27))
        _append_takeaways(parts, takeaway_items, margin, takeaway_y, width - margin * 2, takeaway_h, palette["accent"], surface, ink, height >= 1200)

    elif topic == "water_cycle":
        cycle_nodes = [
            find_node("evaporation"), find_node("condensation"), find_node("precipitation"),
            find_node("collection"), find_node("transpiration"),
        ]
        cycle_nodes = [node for node in cycle_nodes if node]
        rendered.update(node["id"] for node in cycle_nodes)
        center_x, center_y = width / 2, height * 0.53
        radius = min(width * 0.32, height * 0.27)
        if height < 1100:
            radius = min(width * 0.30, height * 0.24)
        positions = []
        for index, node in enumerate(cycle_nodes):
            angle = -math.pi / 2 + 2 * math.pi * index / max(1, len(cycle_nodes))
            positions.append((center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius, node))
        parts.append(f'<ellipse cx="{center_x:.1f}" cy="{center_y:.1f}" rx="{radius * 1.13:.1f}" ry="{radius * .92:.1f}" fill="none" stroke="{roles["input"]}" stroke-width="9" stroke-dasharray="22 15" marker-end="url(#topic-arrow)"/>')
        parts.append(_water_scene(center_x, center_y, min(width / 1200, height / 1200) * 0.9))
        card_w, card_h = (260, 120) if width == 1200 else (300, 112)
        for x, y, node in positions:
            parts.append(make_callout(node, x - card_w / 2, y - card_h / 2, card_w, card_h, "input" if "evap" in node["label"].lower() else "process", "pill", 19))
        note_y = min(height - 200, center_y + radius + 64)
        parts.append(_svg_lines(width / 2, note_y, _wrap(summary, max(30, int((width - 2 * margin) / 9))), font_size=17, fill=muted, anchor="middle", line_height=23))
        _append_takeaways(parts, takeaway_items, margin, height - 160, width - margin * 2, 95, palette["accent"], surface, ink, False)

    elif topic == "cpu_pipeline":
        stage_terms = ("fetch", "decode", "execution", "memory", "write back")
        stages = [find_node(term) for term in stage_terms]
        stages = [node for node in stages if node]
        rendered.update(node["id"] for node in stages)
        chip_y = header_height + (155 if height >= 1200 else 75)
        chip_scale = 1.1 if height >= 1200 else 0.78
        parts.append(f'<rect x="{margin}" y="{header_height + 20}" width="{width - 2 * margin}" height="{320 if height >= 1200 else 175}" rx="32" fill="url(#hero-wash)"/>')
        parts.append(_cpu_illustration(width / 2, chip_y, chip_scale, roles["process"]))
        parts.append(_svg_lines(width / 2, chip_y + 130 * chip_scale, ["INSTRUCTION FLOW THROUGH THE CPU"], font_size=14 if height < 1200 else 17, fill=muted, weight=800, anchor="middle"))
        stage_y = header_height + (380 if height >= 1200 else 215)
        gap = 12 if width == 1200 else 18
        card_w = (width - 2 * margin - gap * 4) / 5
        card_h = 250 if height >= 1200 else 170
        for index, node in enumerate(stages[:5]):
            x = margin + index * (card_w + gap)
            color = (roles["input"], roles["process"], roles["process"], roles["memory"], roles["output"])[index]
            parts.append(render_callout(x, stage_y, card_w, card_h, node["label"].replace(f"Stage {index + 1}: ", ""), node["description"], color, ("pill" if index == 0 or index == 4 else "rounded"), 19 if width > 1200 else 16))
            if index < min(4, len(stages) - 1):
                parts.append(f'<path d="M{x + card_w + 2:.1f} {stage_y + card_h / 2:.1f} H{x + card_w + gap - 3:.1f}" stroke="{roles["process"]}" stroke-width="7" marker-end="url(#topic-arrow)"/>')
        hazard_nodes = [node for node in records if any(word in node["label"].lower() for word in ("hazard", "throughput", "benefit"))]
        rendered.update(node["id"] for node in hazard_nodes)
        hazard_y = stage_y + card_h + (46 if height >= 1200 else 22)
        parts.append(_svg_lines(margin, hazard_y + 24, ["HAZARDS & PERFORMANCE"], font_size=16, fill=roles["warning"], weight=800))
        haz_gap = 12
        haz_w = (width - margin * 2 - haz_gap * 3) / 4
        for index, node in enumerate(hazard_nodes[:4]):
            role = "output" if "benefit" in node["label"].lower() or "throughput" in node["label"].lower() else "warning"
            parts.append(make_callout(node, margin + index * (haz_w + haz_gap), hazard_y + 42, haz_w, 150, role, "cut", 15))
        _append_takeaways(parts, takeaway_items or [summary], margin, height - 150, width - margin * 2, 92, palette["accent"], surface, ink, False)

    elif topic == "ai_ml_hierarchy":
        layout_strategy = "nested_concepts"
        ai_node = find_node("artificial intelligence", "ai")
        ml_node = find_node("machine learning", "ml")
        deep_node = find_node("deep learning")
        if not (ai_node and ml_node and deep_node):
            return None
        rendered.update(node["id"] for node in (ai_node, ml_node, deep_node))
        center_x = width / 2
        center_y = header_height + (360 if height >= 1200 else 250)
        scale = 0.9 if width == 1200 else 1.0
        outer_r, middle_r, inner_r = 250 * scale, 178 * scale, 105 * scale
        parts.append(f'<rect x="{margin}" y="{header_height + 16}" width="{width - margin * 2}" height="{outer_r * 2 + 64:.1f}" rx="30" fill="url(#hero-wash)"/>')
        parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="{outer_r}" fill="{roles["input"]}" fill-opacity=".12" stroke="{roles["input"]}" stroke-width="5"/>')
        parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="{middle_r}" fill="{roles["process"]}" fill-opacity=".18" stroke="{roles["process"]}" stroke-width="5"/>')
        parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="{inner_r}" fill="{roles["memory"]}" fill-opacity=".26" stroke="{roles["memory"]}" stroke-width="5"/>')
        for node, y, color in (
            (ai_node, center_y - outer_r + 35, roles["input"]),
            (ml_node, center_y - middle_r + 35, roles["process"]),
            (deep_node, center_y - inner_r + 38, roles["memory"]),
        ):
            parts.append(_svg_lines(center_x, y, [node["label"].upper()], font_size=16 if width > 1200 else 13, fill=color, weight=850, anchor="middle"))
        extra_nodes = [node for node in records if node["id"] not in {ai_node["id"], ml_node["id"], deep_node["id"]}]
        info_y = center_y + outer_r + 30
        cols = min(3, max(1, len(extra_nodes)))
        gap = 14
        card_w = (width - 2 * margin - gap * (cols - 1)) / cols
        for index, node in enumerate(extra_nodes):
            rendered.add(node["id"])
            parts.append(make_callout(node, margin + index * (card_w + gap), info_y, card_w, 134, ("input", "process", "memory")[index % 3], "rounded", 16))
        takeaway_y = height - 150
        _append_takeaways(parts, takeaway_items or [summary], margin, takeaway_y, width - margin * 2, 92, palette["accent"], surface, ink, False)

    elif topic == "machine_learning":
        layout_strategy = "horizontal_process"
        rendered.update(node["id"] for node in records)
        hero_y = header_height + 18
        hero_height = 300 if height >= 1200 else 145 if height >= 1000 else 120
        illustration_scale = 1.0 if width > 1200 else 0.72
        parts.append(f'<rect x="{margin}" y="{hero_y}" width="{width - margin * 2}" height="{hero_height}" rx="30" fill="url(#hero-wash)"/>')
        parts.append(_machine_learning_illustration(width / 2, hero_y + hero_height / 2 - 8, illustration_scale))

        columns = 4 if width > 1200 else 2
        gap_x, gap_y = 16, 16
        card_w = (width - margin * 2 - gap_x * (columns - 1)) / columns
        rows = (len(records) + columns - 1) // columns
        stage_y = hero_y + hero_height + 28
        card_h = 176 if height >= 1200 else 160 if height >= 1000 else 136
        stage_end = stage_y + rows * card_h + max(0, rows - 1) * gap_y
        stage_centers: Dict[str, Tuple[float, float]] = {}
        for index, node in enumerate(records):
            row, column = divmod(index, columns)
            if row % 2:
                column = columns - column - 1
            x = margin + column * (card_w + gap_x)
            y = stage_y + row * (card_h + gap_y)
            label = f"{index + 1:02d}  {node['label']}"
            role = ("input", "process", "memory", "output")[index % 4]
            parts.append(render_callout(x, y, card_w, card_h, label, node["description"], roles[role], "cut" if index % 2 else "rounded", 18 if width > 1200 else 16))
            stage_centers[node["id"]] = (x + card_w / 2, y + card_h / 2)

        for left, right in zip(records, records[1:]):
            x1, y1 = stage_centers[left["id"]]
            x2, y2 = stage_centers[right["id"]]
            if abs(y2 - y1) < 1:
                direction = 1 if x2 > x1 else -1
                start_x = x1 + direction * (card_w / 2 + 2)
                end_x = x2 - direction * (card_w / 2 + 3)
                parts.append(f'<path d="M{start_x:.1f} {y1:.1f} H{end_x:.1f}" fill="none" stroke="{roles["process"]}" stroke-width="4" marker-end="url(#topic-arrow)"/>')
            else:
                parts.append(f'<path d="M{x1:.1f} {y1 + card_h / 2:.1f} C{x1:.1f} {y1 + card_h / 2 + 24:.1f} {x2:.1f} {y2 - card_h / 2 - 24:.1f} {x2:.1f} {y2 - card_h / 2 - 4:.1f}" fill="none" stroke="{roles["process"]}" stroke-width="4" marker-end="url(#topic-arrow)"/>')

        summary_y = stage_end + 32
        parts.append(_svg_lines(width / 2, summary_y, _wrap(summary, max(30, int((width - 2 * margin) / 9))), font_size=16, fill=muted, anchor="middle", line_height=22))
        takeaway_y = max(summary_y + 76, height - 150)
        if takeaway_y + 92 > height - 35:
            takeaway_y = height - 145
        _append_takeaways(parts, takeaway_items or [summary], margin, takeaway_y, width - margin * 2, 92, palette["accent"], surface, ink, False)

    elif topic == "neural_network":
        rendered.update(node["id"] for node in records)
        net_cy = header_height + (380 if height >= 1200 else 230)
        scale = 0.88 if width == 1200 else 1.0
        parts.append(f'<rect x="{margin}" y="{header_height + 20}" width="{width - 2 * margin}" height="{650 if height >= 1200 else 420}" rx="30" fill="url(#hero-wash)"/>')
        parts.append(_network_illustration(width / 2, net_cy, scale))
        layer_labels = ["INPUT LAYER", "HIDDEN LAYERS", "HIDDEN LAYERS", "OUTPUT LAYER"]
        for x, label in zip([-300, -100, 100, 300], layer_labels):
            parts.append(_svg_lines(width / 2 + x * scale, net_cy + 230 * scale, [label], font_size=13, fill=muted, weight=800, anchor="middle"))
        info_nodes = [node for node in records if any(k in node["label"].lower() for k in ("weight", "activation", "bias", "neuron"))]
        info_y = header_height + (610 if height >= 1200 else 455)
        cols = min(3, max(1, len(info_nodes)))
        gap = 18
        card_w = (width - 2 * margin - (cols - 1) * gap) / cols
        for idx, node in enumerate(info_nodes):
            rendered.add(node["id"])
            parts.append(make_callout(node, margin + idx * (card_w + gap), info_y, card_w, 144, ("input", "process", "memory")[idx % 3], "rounded", 17))
        _append_takeaways(parts, takeaway_items or [summary], margin, height - 150, width - margin * 2, 92, palette["accent"], surface, ink, False)

    else:
        rendered.update(node["id"] for node in records)
        cols = 4 if width > 1200 else 2
        gap = 20
        card_w = (width - 2 * margin - gap * (cols - 1)) / cols
        top = header_height + 42
        rows = (len(records) + cols - 1) // cols
        card_h = min(210, (height - top - 250) / max(rows, 1))
        for idx, node in enumerate(records):
            x = margin + (idx % cols) * (card_w + gap)
            y = top + (idx // cols) * (card_h + gap)
            parts.append(make_callout(node, x, y, card_w, card_h, _category(node["label"]), "cut" if idx % 2 else "rounded", 19))
        _append_takeaways(parts, takeaway_items or [summary], margin, height - 150, width - margin * 2, 92, palette["accent"], surface, ink, False)

    if topic != "photosynthesis" and relationships:
        rel_lines = _wrap("   •   ".join(relationships[:3]), max(24, int((width - 2 * margin) / 9)))
        rel_y = height - 197
        parts.append(_svg_lines(width / 2, rel_y, rel_lines, font_size=13, fill=muted, anchor="middle", line_height=18))

    parts.append(
        f'<text x="{margin}" y="{height - 20}" fill="{muted}" font-size="11" font-family="Inter, Arial, sans-serif">CourseIllustrate AI · Custom vector educational illustration · Not diffusion generated</text>'
        f'<text x="{width - margin}" y="{height - 20}" text-anchor="end" fill="{muted}" font-size="11" font-family="Inter, Arial, sans-serif">{html.escape(settings.orientation.replace("_", " ").title())}</text>'
    )
    parts.append("</svg>")
    svg = "\n".join(parts)
    try:
        ET.fromstring(svg)
        valid = True
        errors: Tuple[str, ...] = ()
    except ET.ParseError as exc:
        valid = False
        errors = (f"Generated SVG is invalid: {exc}",)
    contrast = _contrast_ratio(ink, surface)
    missing = len(records) - len(rendered)
    if missing or clipped_callouts:
        return None
    audit = PosterLayoutAudit(
        node_count=len(records),
        rendered_node_count=len(rendered),
        relationship_count=len(links),
        overlap_count=overlap_count,
        clipped_text_count=clipped_callouts,
        contrast_ratio=contrast,
        svg_valid=valid,
        errors=errors,
        width=width,
        height=height,
        layout_strategy=layout_strategy,
        balance_score=88.0 if not missing else 45.0,
        min_font_size=min_font,
        illustration_relevance=95.0,
    )
    return svg, audit


def _append_takeaways(
    parts: List[str],
    items: Sequence[str],
    x: float,
    y: float,
    width: float,
    height: float,
    accent: str,
    surface: str,
    ink: str,
    columns: bool,
) -> None:
    usable = [str(item).strip() for item in items if str(item).strip()]
    if not usable or height <= 42:
        return
    parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="{accent}"/>')
    parts.append(_svg_lines(x + 24, y + 28, ["KEY TAKEAWAYS"], font_size=13, fill="#FFFFFF", weight=850))
    count = len(usable)
    for index, item in enumerate(usable[:4]):
        if columns and count > 1:
            col = index % 2
            row = index // 2
            tx = x + 24 + col * (width / 2)
            ty = y + 58 + row * 38
            max_chars = max(20, int(width / 16))
        else:
            tx = x + 24
            ty = y + 58 + index * min(25, max(19, (height - 64) / max(1, count)))
            max_chars = max(20, int(width / 10))
        lines = _wrap(f"• {item}", max_chars)
        parts.append(_svg_lines(tx, ty, lines[:2], font_size=14, fill="#FFFFFF", weight=550, line_height=17))


def build_educational_poster_svg(
    *,
    title: str,
    diagram_type: str,
    nodes: Sequence[Any],
    connections: Sequence[Any],
    summary: str = "",
    main_subject: str = "",
    concepts: Sequence[Any] = (),
    relationships: Sequence[str] = (),
    learning_objectives: Sequence[str] = (),
    key_equations: Sequence[str] = (),
    poster_settings: Any = None,
    mock_banner: bool = False,
) -> Tuple[str, PosterLayoutAudit]:
    """Build a scalable poster SVG and an audit of its deterministic layout."""
    title = (title or "").strip()
    diagram_type = (diagram_type or "").lower()
    if not title:
        raise ValueError("Poster title must not be empty.")
    if diagram_type not in _VALID_DIAGRAM_TYPES:
        raise ValueError(f"Unsupported poster diagram type '{diagram_type}'.")

    settings = _settings(poster_settings)
    records = _node_records(nodes)
    node_by_id = {node["id"]: node for node in records}
    links = _connection_records(connections, set(node_by_id))
    specialized = _specialized_poster(
        title=title,
        diagram_type=diagram_type,
        records=records,
        links=links,
        summary=summary,
        main_subject=main_subject,
        concepts=concepts,
        relationships=relationships,
        learning_objectives=learning_objectives,
        key_equations=key_equations,
        settings=settings,
        mock_banner=mock_banner,
    )
    if specialized:
        return specialized

    layout_style = settings.layout_style
    family = {
        "illustrated_process": "process",
        "concept_map_poster": "concept_map",
        "technical_architecture_poster": "architecture",
    }.get(layout_style, diagram_type)
    if family in ("sequence", "timeline"):
        family = "process"
    if family == "tree":
        family = "hierarchical"

    palette = THEMES[settings.theme]
    role_colors = choose_subject_palette(
        f"{main_subject} {title}",
        settings.theme,
        settings.color_scheme,
    )
    width, target_height = {
        "portrait": (1200, 1600),
        "landscape": (1600, 1000),
        "square": (1200, 1200),
        "presentation_16_9": (1600, 900),
    }[settings.orientation]
    margin = 58 if width < 1200 else 72

    topic_lines = _wrap(title, max(16, int((width - 2 * margin) / 25)))
    subtitle_lines = _wrap(summary, max(30, int((width - 2 * margin) / 9)))
    header_height = 94 + len(topic_lines) * 54 + len(subtitle_lines) * 24
    subject_text = _subject_label(main_subject, title)
    header_height += 50

    root_node = None
    visible_nodes = list(records)
    if family == "mindmap":
        for node in records:
            if node["id"].lower() in ("root", "central") or node["label"].casefold() == title.casefold():
                root_node = node
                visible_nodes.remove(node)
                break

    orientation_columns = {
        "portrait": 1,
        "landscape": 4,
        "square": 2,
        "presentation_16_9": 4,
    }[settings.orientation]
    if family == "mindmap":
        columns = min(3, max(1, len(visible_nodes)))
    elif family == "comparison":
        columns = min(2, max(1, len(visible_nodes)))
    elif family == "architecture":
        columns = min(3 if width >= 1500 else 2, max(1, len(visible_nodes)))
    elif family == "concept_map":
        columns = min(3, max(1, orientation_columns, min(3, len(visible_nodes))))
    else:
        columns = min(max(2, orientation_columns), max(1, len(visible_nodes)))

    complexity_gap = {"introductory": 34, "balanced": 24, "detailed": 18}[settings.visual_complexity]
    gap_x = complexity_gap if width > 1200 else max(16, complexity_gap - 4)
    gap_y = complexity_gap
    card_width = (width - 2 * margin - gap_x * (columns - 1)) / columns
    label_characters = max(12, int((card_width - 44) / 10.5))
    description_characters = max(18, int((card_width - 44) / 7.4))

    prepared = []
    for index, node in enumerate(visible_nodes):
        node_text = f'{node["label"]} {node["description"]}'
        category = _category(node_text)
        label_lines = _wrap(node["label"], label_characters)
        description_lines = _wrap(node["description"], description_characters) if node["description"] else []
        card_height = 60 + len(label_lines) * 28 + (12 + len(description_lines) * 20 if description_lines else 0)
        prepared.append({
            **node,
            "category": category,
            "accent": role_colors[category],
            "label_lines": label_lines,
            "description_lines": description_lines,
            "height": max(124, card_height),
            "index": index,
        })

    body_top = header_height + (144 if family == "mindmap" else 42)
    positions: Dict[str, Dict[str, float]] = {}
    row_heights: Dict[int, float] = {}
    for index, node in enumerate(prepared):
        row = index // columns
        row_heights[row] = max(row_heights.get(row, 0), node["height"])
        positions[node["id"]] = {
            "x": margin + (index % columns) * (card_width + gap_x),
            "y": body_top + sum(row_heights.get(previous, 0) + gap_y for previous in range(row)),
            "width": card_width,
            "height": node["height"],
        }

    if family == "mindmap":
        root_height = 72
        root_box = {
            "x": (width - min(card_width, 380)) / 2,
            "y": header_height + 36,
            "width": min(card_width, 380),
            "height": root_height,
        }
        if root_node:
            positions[root_node["id"]] = root_box
        else:
            positions["__root__"] = root_box

    content_bottom = max(
        [header_height + 40]
        + [box["y"] + box["height"] for box in positions.values()]
    )

    concept_records = []
    for value in concepts or []:
        data = _as_mapping(value)
        name = str(data.get("name") or "").strip()
        definition = str(data.get("definition") or "").strip()
        if name and not any(name.casefold() == n["label"].casefold() for n in records):
            concept_records.append((name, definition))

    support_sections: List[Tuple[str, List[str]]] = []
    if concept_records:
        support_sections.append((
            "Additional concepts",
            [f"{name}: {definition}" if definition else name for name, definition in concept_records],
        ))
    if relationships:
        support_sections.append(("Key relationships", [str(item) for item in relationships if str(item).strip()]))
    if learning_objectives:
        support_sections.append(("Learning objectives", [str(item) for item in learning_objectives if str(item).strip()]))

    support_top = content_bottom + 42
    support_gap = 22
    support_width = (width - 2 * margin - support_gap) / 2
    support_heights = []
    support_row_heights: Dict[int, float] = {}
    support_content: List[Tuple[str, List[str], float, float, float]] = []
    for index, (heading, items) in enumerate(support_sections):
        body_lines = []
        for item in items:
            body_lines.extend(_wrap(f"- {item}", max(24, int((support_width - 40) / 7.2))))
            body_lines.append("")
        while body_lines and not body_lines[-1]:
            body_lines.pop()
        height = 68 + max(1, len(body_lines)) * 20
        col = index % 2
        row = index // 2
        x = margin + col * (support_width + support_gap)
        y = support_top + sum(support_row_heights[previous] + support_gap for previous in range(row))
        support_row_heights[row] = max(support_row_heights.get(row, 0), height)
        support_content.append((heading, body_lines, x, y, height))
        support_heights.append(height)
    support_bottom = max(
        [content_bottom]
        + [item[3] + item[4] for item in support_content]
    )

    takeaway = (learning_objectives[0] if learning_objectives else summary or "").strip()
    takeaway_lines = _wrap(takeaway, max(30, int((width - 2 * margin - 48) / 8))) if takeaway else []
    takeaway_height = 78 + len(takeaway_lines) * 21 if takeaway_lines else 0
    footer_y = support_bottom + (30 if support_content else 18)
    height = max(target_height, int(footer_y + takeaway_height + 92))

    errors: List[str] = []
    overlap_count = 0
    boxes = list(positions.values())
    for index, first in enumerate(boxes):
        for second in boxes[index + 1:]:
            if (
                first["x"] < second["x"] + second["width"]
                and first["x"] + first["width"] > second["x"]
                and first["y"] < second["y"] + second["height"]
                and first["y"] + first["height"] > second["y"]
            ):
                overlap_count += 1
    if overlap_count:
        errors.append(f"Poster layout contains {overlap_count} overlapping nodes.")
    if len(positions) < len(records):
        errors.append("Poster layout omitted one or more structured diagram nodes.")
    if any(box["x"] < 0 or box["x"] + box["width"] > width or box["y"] + box["height"] > height for box in boxes):
        errors.append("Poster content extends beyond the SVG canvas.")

    background = palette["background"]
    surface = palette["surface"]
    ink = palette["ink"]
    muted = palette["muted"]
    contrast = _contrast_ratio(ink, surface)
    if contrast < 4.5:
        errors.append(f"Poster body text contrast is below 4.5:1 ({contrast:.2f}:1).")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="poster-title poster-desc" preserveAspectRatio="xMidYMin meet">',
        f'<title id="poster-title">{html.escape(title)}</title>',
        f'<desc id="poster-desc">{html.escape(summary or f"Educational poster about {title}")}</desc>',
        f'<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="{role_colors["concept"]}"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
        f'<rect x="0" y="0" width="{width}" height="{header_height}" fill="{surface}"/>',
        f'<rect x="0" y="{header_height - 8}" width="{width}" height="8" fill="{palette["accent"]}"/>',
        f'<rect x="{margin}" y="28" width="12" height="28" rx="6" fill="{palette["accent"]}"/>',
        f'<text x="{margin + 26}" y="48" fill="{muted}" font-size="15" font-weight="700" letter-spacing="1.5" font-family="Inter, Arial, sans-serif">{html.escape(subject_text)}</text>',
    ]
    if mock_banner:
        parts.append(
            f'<text x="{width - margin}" y="48" text-anchor="end" fill="{muted}" font-size="13" font-weight="700" font-family="Inter, Arial, sans-serif">DEVELOPMENT CONTENT PREVIEW</text>'
        )

    title_start_y = 112
    parts.append(_svg_lines(margin, title_start_y, topic_lines, font_size=42, fill=ink, weight=800, line_height=50))
    subtitle_y = title_start_y + len(topic_lines) * 50 + 10
    parts.append(_svg_lines(margin, subtitle_y, subtitle_lines, font_size=17, fill=muted, line_height=24))
    theme_label = THEME_LABELS[settings.theme].upper()
    parts.append(
        f'<text x="{width - margin}" y="{header_height - 26}" text-anchor="end" fill="{palette["accent"]}" font-size="12" font-weight="700" letter-spacing="1" font-family="Inter, Arial, sans-serif">{html.escape(theme_label)}</text>'
    )

    if family == "mindmap":
        root_box = positions.get(root_node["id"] if root_node else "__root__")
        center_x = root_box["x"] + root_box["width"] / 2
        root_bottom = root_box["y"] + root_box["height"]
        for node in prepared:
            box = positions[node["id"]]
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"]
            parts.append(
                f'<path d="M {center_x:.1f} {root_bottom:.1f} C {center_x:.1f} {root_bottom + 42:.1f}, {target_x:.1f} {target_y - 42:.1f}, {target_x:.1f} {target_y:.1f}" fill="none" stroke="{node["accent"]}" stroke-width="3" opacity="0.75"/>'
            )
    else:
        for link in links:
            source = positions[link["source"]]
            target = positions[link["target"]]
            sx = source["x"] + source["width"] / 2
            sy = source["y"] + source["height"] / 2
            tx = target["x"] + target["width"] / 2
            ty = target["y"] + target["height"] / 2
            dx, dy = tx - sx, ty - sy
            if abs(dx) >= abs(dy):
                start_x = source["x"] + source["width"] if dx >= 0 else source["x"]
                end_x = target["x"] if dx >= 0 else target["x"] + target["width"]
                control = max(28, abs(end_x - start_x) * 0.35)
                direction = 1 if dx >= 0 else -1
                path = (
                    f"M {start_x:.1f} {sy:.1f} C {start_x + control * direction:.1f} {sy:.1f}, "
                    f"{end_x - control * direction:.1f} {ty:.1f}, {end_x:.1f} {ty:.1f}"
                )
            else:
                start_y = source["y"] + source["height"] if dy >= 0 else source["y"]
                end_y = target["y"] if dy >= 0 else target["y"] + target["height"]
                control = max(28, abs(end_y - start_y) * 0.35)
                direction = 1 if dy >= 0 else -1
                path = (
                    f"M {sx:.1f} {start_y:.1f} C {sx:.1f} {start_y + control * direction:.1f}, "
                    f"{tx:.1f} {end_y - control * direction:.1f}, {tx:.1f} {end_y:.1f}"
                )
            parts.append(
                f'<path d="{path}" fill="none" stroke="{role_colors["concept"]}" stroke-width="3" '
                f'stroke-linecap="round" marker-end="url(#arrow)" opacity="0.8"/>'
            )
            if link["label"]:
                label_lines = _wrap(link["label"], 22)
                label_text = " ".join(label_lines)
                parts.append(
                    f'<text x="{(sx + tx) / 2:.1f}" y="{(sy + ty) / 2 - 7:.1f}" text-anchor="middle" '
                    f'fill="{muted}" stroke="{background}" stroke-width="6" paint-order="stroke" '
                    f'font-size="12" font-weight="600" font-family="Inter, Arial, sans-serif">{html.escape(label_text)}</text>'
                )

    if root_node:
        root_box = positions[root_node["id"]]
        parts.append(
            f'<rect x="{root_box["x"]:.1f}" y="{root_box["y"]:.1f}" width="{root_box["width"]:.1f}" '
            f'height="{root_box["height"]:.1f}" rx="28" fill="{palette["accent"]}"/>'
        )
        root_lines = _wrap(root_node["label"], max(16, int(root_box["width"] / 12)))
        parts.append(_svg_lines(
            root_box["x"] + root_box["width"] / 2,
            root_box["y"] + 43,
            root_lines,
            font_size=20,
            fill="#FFFFFF",
            weight=750,
            line_height=24,
            anchor="middle",
        ))

    for node in prepared:
        box = positions[node["id"]]
        accent = node["accent"]
        radius = 30 if node["category"] in ("input", "output") and family in ("process", "flowchart") else 20
        parts.append(
            f'<g data-node-id="{html.escape(node["id"], quote=True)}">'
            f'<rect x="{box["x"]:.1f}" y="{box["y"]:.1f}" width="{box["width"]:.1f}" height="{box["height"]:.1f}" '
            f'rx="{radius}" fill="{surface}" stroke="{accent}" stroke-width="2.5"/>'
            f'<rect x="{box["x"]:.1f}" y="{box["y"]:.1f}" width="8" height="{box["height"]:.1f}" rx="4" fill="{accent}"/>'
        )
        icon_x, icon_y = box["x"] + 22, box["y"] + 18
        parts.append(_icon(node["category"], icon_x, icon_y, accent))
        parts.append(
            f'<circle cx="{box["x"] + box["width"] - 24:.1f}" cy="{box["y"] + 26:.1f}" r="14" fill="{accent}" opacity="0.12"/>'
            f'<text x="{box["x"] + box["width"] - 24:.1f}" y="{box["y"] + 31:.1f}" text-anchor="middle" '
            f'fill="{accent}" font-size="13" font-weight="800" font-family="Inter, Arial, sans-serif">{node["index"] + 1:02d}</text>'
        )
        parts.append(_svg_lines(
            box["x"] + 54,
            box["y"] + 37,
            node["label_lines"],
            font_size=18,
            fill=ink,
            weight=750,
            line_height=24,
        ))
        if node["description_lines"]:
            desc_y = box["y"] + 52 + len(node["label_lines"]) * 24
            parts.append(_svg_lines(
                box["x"] + 22,
                desc_y,
                node["description_lines"],
                font_size=14,
                fill=muted,
                line_height=19,
            ))
        category_label = node["category"].replace("_", " ").upper()
        parts.append(
            f'<text x="{box["x"] + box["width"] - 18:.1f}" y="{box["y"] + box["height"] - 14:.1f}" '
            f'text-anchor="end" fill="{accent}" font-size="10" font-weight="700" letter-spacing="0.8" '
            f'font-family="Inter, Arial, sans-serif">{category_label}</text></g>'
        )

    for heading, lines, x, y, card_height in support_content:
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{support_width:.1f}" height="{card_height:.1f}" '
            f'rx="18" fill="{surface}" stroke="{palette["accent"]}" stroke-opacity="0.32" stroke-width="1.5"/>'
        )
        parts.append(_svg_lines(x + 20, y + 30, [heading], font_size=15, fill=palette["accent"], weight=750))
        if lines:
            parts.append(_svg_lines(x + 20, y + 58, lines, font_size=13, fill=muted, line_height=19))

    if takeaway_lines:
        takeaway_y = support_bottom + (support_gap + 18 if support_content else 28)
        parts.append(
            f'<rect x="{margin}" y="{takeaway_y:.1f}" width="{width - margin * 2}" height="{takeaway_height}" '
            f'rx="20" fill="{palette["accent"]}"/>'
        )
        parts.append(_svg_lines(
            margin + 24,
            takeaway_y + 30,
            ["KEY TAKEAWAY"],
            font_size=12,
            fill="#FFFFFF",
            weight=800,
        ))
        parts.append(_svg_lines(
            margin + 24,
            takeaway_y + 58,
            takeaway_lines,
            font_size=15,
            fill="#FFFFFF",
            weight=600,
            line_height=21,
        ))

    footer_y = height - 24
    parts.append(
        f'<text x="{margin}" y="{footer_y}" fill="{muted}" font-size="11" font-family="Inter, Arial, sans-serif">CourseIllustrate AI · Educational poster</text>'
        f'<text x="{width - margin}" y="{footer_y}" text-anchor="end" fill="{muted}" font-size="11" font-family="Inter, Arial, sans-serif">{html.escape(settings.orientation.replace("_", " ").title())}</text>'
    )
    parts.append("</svg>")
    svg = "\n".join(parts)
    try:
        ET.fromstring(svg)
        svg_valid = True
    except ET.ParseError as exc:
        svg_valid = False
        errors.append(f"Generated SVG is invalid: {exc}")

    audit = PosterLayoutAudit(
        node_count=len(records),
        rendered_node_count=len(prepared) + (1 if root_node else 0),
        relationship_count=len(links),
        overlap_count=overlap_count,
        clipped_text_count=0,
        contrast_ratio=contrast,
        svg_valid=svg_valid,
        errors=tuple(errors),
        width=width,
        height=height,
        layout_strategy=family,
        balance_score=82.0 if len(positions) > 1 and not overlap_count else 55.0,
        min_font_size=13,
        illustration_relevance=55.0,
    )
    return svg, audit


def render_educational_poster_files(
    *,
    title: str,
    diagram_type: str,
    nodes: Sequence[Any],
    connections: Sequence[Any],
    destination_dir: Path,
    summary: str = "",
    main_subject: str = "",
    concepts: Sequence[Any] = (),
    relationships: Sequence[str] = (),
    learning_objectives: Sequence[str] = (),
    key_equations: Sequence[str] = (),
    poster_settings: Any = None,
    mock_banner: bool = False,
) -> Tuple[Path, Path, Path, int, int, PosterLayoutAudit]:
    """Persist the primary poster SVG and derive printable PNG/PDF assets."""
    svg, audit = build_educational_poster_svg(
        title=title,
        diagram_type=diagram_type,
        nodes=nodes,
        connections=connections,
        summary=summary,
        main_subject=main_subject,
        concepts=concepts,
        relationships=relationships,
        learning_objectives=learning_objectives,
        key_equations=key_equations,
        poster_settings=poster_settings,
        mock_banner=mock_banner,
    )
    if not audit.valid:
        raise ValueError("Poster layout validation failed: " + "; ".join(audit.errors))

    destination_dir.mkdir(parents=True, exist_ok=True)
    svg_path = destination_dir / "poster.svg"
    png_path = destination_dir / "poster.png"
    pdf_path = destination_dir / "poster.pdf"
    svg_path.write_text(svg, encoding="utf-8")

    svg_document = pymupdf.open(stream=svg.encode("utf-8"), filetype="svg")
    pixmap = svg_document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    pixmap.save(str(png_path))
    pdf_path.write_bytes(svg_document.convert_to_pdf())
    svg_document.close()
    return svg_path, png_path, pdf_path, pixmap.width, pixmap.height, audit
