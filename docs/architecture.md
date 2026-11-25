# CourseIllustrate AI - System Architecture Documentation

## Overview
CourseIllustrate AI is an online course diagram and illustration generator that ingests educational text descriptions and uploaded PDF course materials, extracting conceptual structures and rendering:
1. **Accurate Educational Diagrams**: Flowcharts, mind maps, concept maps, and architecture diagrams via Mermaid.js and SVG.
2. **AI Illustrations**: Pedagogical visual metaphors and concept artwork generated via diffusion models (Stable Diffusion / Hugging Face).

## Multi-Agent Architecture (Phase 2 Preview)
The core intelligence engine uses LangGraph with 5 specialized agents:
1. **Content Understanding Agent**: Extracts key concepts, terminology, and hierarchical relationships from course materials.
2. **Diagram Planning Agent**: Formulates diagram syntax (Mermaid DSL) tailored to the pedagogical goal.
3. **Prompt Engineering Agent**: Crafts descriptive, style-consistent prompts for diffusion generation.
4. **Image Generation Agent**: Coordinates calls to diffusion APIs with negative prompting and style anchors.
5. **Quality Evaluation Agent**: Evaluates diagram syntax validity and semantic coverage, cycling back for automated repair if errors are detected.

## Database Schema (SQLite)
- `projects`: id (UUID), title, description, created_at
- `documents`: id (UUID), project_id, filename, extracted_text, page_count, created_at
- `generations`: id (UUID), project_id, topic, diagram_type, diagram_code, image_path, status, created_at
