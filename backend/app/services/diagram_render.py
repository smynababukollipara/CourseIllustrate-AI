"""Render stored PNG, SVG, and PDF diagram files from a diagram plan."""
import html
import textwrap
from pathlib import Path
from typing import List, Sequence, Tuple, Optional, Any

import pymupdf

from app.schemas.generation import DiagramNode, DiagramConnection


def _safe(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def render_diagram_files(
    *,
    title: str,
    diagram_type: str,
    nodes: Sequence[DiagramNode],
    connections: Sequence[DiagramConnection],
    destination_dir: Path,
    attempt: int,
    mock_banner: bool,
) -> Tuple[Path, Path, Path, int, int]:
    """
    Write a real PNG, SVG, and PDF for this attempt.
    Filenames include the attempt number so earlier images are not overwritten.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    stem = f"diagram-a{attempt}"
    png_path = destination_dir / f"{stem}.png"
    svg_path = destination_dir / f"{stem}.svg"
    pdf_path = destination_dir / f"{stem}.pdf"

    page_w, page_h = 1200, 860
    layout = _layout(list(nodes)[:8], page_w, page_h)
    _write_png(
        png_path, title, diagram_type, layout, list(connections), page_w, page_h, mock_banner
    )
    _write_svg(svg_path, title, diagram_type, layout, list(connections), page_w, page_h, mock_banner)
    _write_pdf(pdf_path, png_path, page_w, page_h)

    with pymupdf.open(png_path) as image_doc:
        pix = image_doc[0].get_pixmap()
        width, height = pix.width, pix.height
    return png_path, svg_path, pdf_path, width, height


def _layout(nodes: List[DiagramNode], page_w: int, page_h: int):
    margin_x = 70
    top = 150
    box_w = 280
    box_h = 110
    gap_x = 40
    gap_y = 36
    columns = 3 if len(nodes) > 3 else max(len(nodes), 1)
    placed = []
    for index, node in enumerate(nodes):
        col = index % columns
        row = index // columns
        x = margin_x + col * (box_w + gap_x)
        y = top + row * (box_h + gap_y)
        if x + box_w > page_w - 40:
            x = margin_x
        placed.append({"node": node, "x": x, "y": y, "w": box_w, "h": box_h})
    return placed


def _write_png(path, title, diagram_type, layout, connections, page_w, page_h, mock_banner):
    doc = pymupdf.open()
    page = doc.new_page(width=page_w, height=page_h)
    page.draw_rect(pymupdf.Rect(0, 0, page_w, page_h), color=(0.97, 0.98, 1), fill=(0.97, 0.98, 1))
    page.draw_rect(pymupdf.Rect(0, 0, page_w, 108), color=(1, 1, 1), fill=(1, 1, 1))
    page.insert_text((48, 48), _safe(title, 70), fontsize=26, fontname="helv", color=(0.12, 0.16, 0.25))
    page.insert_text(
        (48, 82),
        f"{diagram_type.replace('_', ' ').title()}  ·  educational diagram",
        fontsize=13,
        fontname="helv",
        color=(0.35, 0.38, 0.52),
    )
    if mock_banner:
        page.insert_text(
            (page_w - 280, 82),
            "MOCK OUTPUT",
            fontsize=12,
            fontname="helv",
            color=(0.55, 0.37, 0.02),
        )

    centers = {}
    for item in layout:
        node = item["node"]
        rect = pymupdf.Rect(item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"])
        page.draw_rect(rect, color=(0.39, 0.35, 0.82), fill=(0.93, 0.94, 1), width=1.6)
        label = "\n".join(textwrap.wrap(node.label, width=28, break_long_words=False))
        page.insert_textbox(
            pymupdf.Rect(rect.x0 + 12, rect.y0 + 12, rect.x1 - 12, rect.y1 - 10),
            label,
            fontsize=13,
            fontname="helv",
            color=(0.12, 0.16, 0.25),
        )
        centers[node.id] = ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)

    for link in connections:
        if link.source in centers and link.target in centers:
            page.draw_line(centers[link.source], centers[link.target], color=(0.39, 0.35, 0.82), width=1.4)

    pdf_bytes = doc.tobytes()
    doc.close()
    # Rebuild a true PNG pixmap from the in-memory vector page without file locking
    vector = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pix = vector[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    vector.close()
    pix.save(str(path))


def _write_svg(path, title, diagram_type, layout, connections, page_w, page_h, mock_banner):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}" height="{page_h}" viewBox="0 0 {page_w} {page_h}">',
        '<rect width="100%" height="100%" fill="#f8f9fd"/>',
        f'<rect width="{page_w}" height="108" fill="#ffffff"/>',
        f'<text x="48" y="52" fill="#1e293b" font-size="26" font-family="Arial, sans-serif">{html.escape(_safe(title, 70))}</text>',
        f'<text x="48" y="84" fill="#586174" font-size="13" font-family="Arial, sans-serif">{html.escape(diagram_type.replace("_", " ").title())}</text>',
    ]
    if mock_banner:
        parts.append(
            f'<text x="{page_w - 280}" y="84" fill="#8a5d00" font-size="12" font-family="Arial, sans-serif">MOCK OUTPUT</text>'
        )
    centers = {}
    for item in layout:
        node = item["node"]
        centers[node.id] = (item["x"] + item["w"] / 2, item["y"] + item["h"] / 2)
    for link in connections:
        if link.source in centers and link.target in centers:
            x1, y1 = centers[link.source]
            x2, y2 = centers[link.target]
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#7066d2" stroke-width="2"/>'
            )
    for item in layout:
        node = item["node"]
        parts.append(
            f'<rect x="{item["x"]}" y="{item["y"]}" width="{item["w"]}" height="{item["h"]}" rx="12" fill="#eef0ff" stroke="#7066d2" stroke-width="2"/>'
        )
        lines = textwrap.wrap(node.label, width=28, break_long_words=False) or [""]
        tspans = "".join(
            f'<tspan x="{item["x"] + 16}" dy="{0 if index == 0 else 20}">{html.escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        parts.append(
            f'<text x="{item["x"] + 16}" y="{item["y"] + 34}" fill="#1e293b" font-size="15" font-family="Arial, sans-serif">{tspans}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _write_pdf(pdf_path: Path, png_path: Path, page_w: int, page_h: int) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=page_w, height=page_h)
    page.insert_image(page.rect, filename=str(png_path))
    doc.save(pdf_path)
    doc.close()


def validate_png(path: Path) -> bool:
    if not path.is_file():
        return False
    data = path.read_bytes()
    return len(data) > 256 and data.startswith(b"\x89PNG\r\n\x1a\n")


def build_course_export_pdf(
    pdf_path: Path,
    title: str,
    diagram_type: str,
    summary: str,
    concepts: list,
    relationships: list,
    diagram_png_path: Optional[Path] = None,
    illustration_png_path: Optional[Path] = None,
    quality_score: Optional[float] = None,
    provider_info: Optional[str] = None,
    prompt: Optional[str] = None,
    created_at_str: Optional[str] = None,
    image_provider: Optional[str] = None,
    image_is_mock: bool = False,
) -> Path:
    """
    Builds a professional multi-page educational PDF package:
    - Title & Overview
    - High-resolution Structured Diagram
    - Extracted Educational Concepts & Relationships
    - AI-Generated Educational Illustration
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page_w, page_h = 800, 1050

    # Page 1: Cover, Executive Summary, Concepts, and Metrics
    p1 = doc.new_page(width=page_w, height=page_h)
    p1.draw_rect(pymupdf.Rect(0, 0, page_w, page_h), color=(0.04, 0.05, 0.1), fill=(0.04, 0.05, 0.1))
    p1.draw_rect(pymupdf.Rect(0, 0, page_w, 140), color=(0.1, 0.12, 0.25), fill=(0.1, 0.12, 0.25))

    p1.insert_text((48, 55), "CourseIllustrate AI — Educational Learning Module", fontsize=15, fontname="helv", color=(0.65, 0.7, 0.95))
    p1.insert_text((48, 92), _safe(title, 60), fontsize=26, fontname="helv", color=(1, 1, 1))
    p1.insert_text((48, 120), f"Format: {diagram_type.replace('_', ' ').title()}  ·  Generated: {created_at_str or 'Recent'}", fontsize=11, fontname="helv", color=(0.7, 0.75, 0.9))

    # Quality Badge
    if quality_score is not None:
        p1.draw_rect(pymupdf.Rect(page_w - 200, 40, page_w - 48, 100), color=(0.2, 0.6, 0.4), fill=(0.08, 0.2, 0.14), width=1.5)
        p1.insert_text((page_w - 188, 65), "QUALITY SCORE", fontsize=9, fontname="helv", color=(0.4, 0.9, 0.6))
        p1.insert_text((page_w - 188, 90), f"{quality_score}/100", fontsize=18, fontname="helv", color=(1, 1, 1))

    # Summary section
    p1.insert_text((48, 175), "EDUCATIONAL SUMMARY", fontsize=12, fontname="helv", color=(0.5, 0.6, 0.95))
    p1.draw_rect(pymupdf.Rect(48, 190, page_w - 48, 280), color=(0.2, 0.22, 0.4), fill=(0.08, 0.09, 0.18), width=1)
    p1.insert_textbox(pymupdf.Rect(60, 202, page_w - 60, 268), summary or "Comprehensive educational overview.", fontsize=11, fontname="helv", color=(0.9, 0.92, 0.98))

    # Key Concepts Table
    p1.insert_text((48, 310), f"EXTRACTED PEDAGOGICAL CONCEPTS ({len(concepts)})", fontsize=12, fontname="helv", color=(0.5, 0.6, 0.95))
    cy = 330
    for idx, c in enumerate(concepts[:6]):
        c_name = getattr(c, "name", str(c.get("name") if isinstance(c, dict) else c))
        c_def = getattr(c, "definition", str(c.get("definition") if isinstance(c, dict) else ""))
        rect = pymupdf.Rect(48, cy, page_w - 48, cy + 54)
        p1.draw_rect(rect, color=(0.18, 0.2, 0.38), fill=(0.06, 0.07, 0.14), width=1)
        p1.insert_text((60, cy + 22), f"{idx+1}. {c_name}", fontsize=12, fontname="helv", color=(1, 1, 1))
        p1.insert_textbox(pymupdf.Rect(60, cy + 28, page_w - 60, cy + 50), c_def[:120], fontsize=9, fontname="helv", color=(0.75, 0.8, 0.9))
        cy += 60

    # Relationships
    if relationships:
        p1.insert_text((48, cy + 15), "CONCEPTUAL RELATIONSHIPS", fontsize=12, fontname="helv", color=(0.5, 0.6, 0.95))
        cy += 30
        for r in relationships[:4]:
            p1.insert_text((60, cy + 10), f"• {r}", fontsize=10, fontname="helv", color=(0.85, 0.88, 0.95))
            cy += 20

    # Footer
    p1.insert_text((48, page_h - 25), f"CourseIllustrate AI  ·  Provider: {provider_info or 'Multi-Agent Engine'}", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.6))

    # Page 2: Structured Diagram
    if diagram_png_path and diagram_png_path.is_file():
        p2 = doc.new_page(width=page_w, height=page_h)
        p2.draw_rect(pymupdf.Rect(0, 0, page_w, page_h), color=(0.04, 0.05, 0.1), fill=(0.04, 0.05, 0.1))
        p2.insert_text((48, 50), "OUTPUT A: STRUCTURED EDUCATIONAL DIAGRAM", fontsize=14, fontname="helv", color=(0.5, 0.6, 0.95))
        p2.insert_text((48, 75), f"{diagram_type.replace('_', ' ').title()} Representation with Pedagogical Connectors", fontsize=11, fontname="helv", color=(0.75, 0.8, 0.9))

        diag_rect = pymupdf.Rect(48, 100, page_w - 48, page_h - 60)
        p2.insert_image(diag_rect, filename=str(diagram_png_path))
        p2.insert_text((48, page_h - 25), "Vector Diagram  ·  Verified Syntax & Concept Hierarchy", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.6))

    # Page 3: Illustration (if available)
    if illustration_png_path and illustration_png_path.is_file():
        p3 = doc.new_page(width=page_w, height=page_h)
        p3.draw_rect(pymupdf.Rect(0, 0, page_w, page_h), color=(0.04, 0.05, 0.1), fill=(0.04, 0.05, 0.1))
        p3.insert_text((48, 50), "OUTPUT B: EDUCATIONAL ILLUSTRATION", fontsize=14, fontname="helv", color=(0.5, 0.6, 0.95))
        if image_is_mock:
            p3.insert_text(
                (48, 75),
                "DEVELOPMENT PREVIEW — NOT GENERATED BY A DIFFUSION PROVIDER",
                fontsize=10,
                fontname="helv",
                color=(0.95, 0.72, 0.25),
            )
        else:
            p3.insert_text(
                (48, 75),
                f"Image provider: {image_provider or 'Configured provider'}",
                fontsize=11,
                fontname="helv",
                color=(0.75, 0.8, 0.9),
            )

        img_rect = pymupdf.Rect(48, 100, page_w - 48, page_h - 220)
        p3.insert_image(img_rect, filename=str(illustration_png_path))

        # Prompt & Notes section
        p3.insert_text((48, page_h - 190), "IMAGE PROMPT USED", fontsize=11, fontname="helv", color=(0.5, 0.6, 0.95))
        p3.draw_rect(pymupdf.Rect(48, page_h - 175, page_w - 48, page_h - 45), color=(0.2, 0.22, 0.4), fill=(0.08, 0.09, 0.18))
        p3.insert_textbox(pymupdf.Rect(58, page_h - 165, page_w - 58, page_h - 55), prompt or "Educational diffusion prompt.", fontsize=9, fontname="helv", color=(0.8, 0.85, 0.95))

        p3.insert_text(
            (48, page_h - 20),
            f"Image Provider: {image_provider or 'Local development preview'}",
            fontsize=9,
            fontname="helv",
            color=(0.4, 0.45, 0.6),
        )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path

