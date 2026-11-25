from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.schemas.generation import (
    DiagramNode,
    DiagramConnection,
    PosterDesignSettings,
)
from app.services.poster_renderer import (
    build_educational_poster_svg,
    choose_subject_palette,
    render_educational_poster_files,
)
from app.services.llm_provider import MockLLMProvider


def cpu_nodes():
    return [
        DiagramNode(id="fetch", label="Instruction Fetch", description="Retrieves the next instruction."),
        DiagramNode(id="decode", label="Instruction Decode", description="Decodes opcode and reads operands."),
        DiagramNode(id="execute", label="Execution", description="Performs arithmetic and logic operations."),
        DiagramNode(id="memory", label="Memory Access", description="Reads or writes data operands."),
        DiagramNode(id="writeback", label="Write Back", description="Stores results in registers."),
    ]


def cpu_connections():
    return [
        DiagramConnection(source="fetch", target="decode", label="advances"),
        DiagramConnection(source="decode", target="execute", label="supplies operands"),
        DiagramConnection(source="execute", target="memory", label="accesses data"),
        DiagramConnection(source="memory", target="writeback", label="stores result"),
    ]


def test_poster_svg_is_valid_and_export_files_exist(tmp_path):
    svg, audit = build_educational_poster_svg(
        title="CPU Pipeline",
        diagram_type="process",
        nodes=cpu_nodes(),
        connections=cpu_connections(),
        summary="Overlapping CPU stages increase instruction throughput.",
        main_subject="Computer Science",
    )
    ET.fromstring(svg)
    assert "<svg" in svg
    assert audit.valid
    assert audit.node_count == 5
    assert audit.relationship_count == 4

    svg_path, png_path, pdf_path, width, height, final_audit = render_educational_poster_files(
        title="CPU Pipeline",
        diagram_type="process",
        nodes=cpu_nodes(),
        connections=cpu_connections(),
        destination_dir=tmp_path,
        summary="Overlapping CPU stages increase instruction throughput.",
        main_subject="Computer Science",
    )
    assert svg_path.read_text(encoding="utf-8").startswith("<svg")
    assert png_path.read_bytes().startswith(b"\x89PNG")
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert width >= 2000
    assert height >= 1000
    assert final_audit.valid


@pytest.mark.parametrize("diagram_type", [
    "flowchart", "mindmap", "concept_map", "hierarchical",
    "process", "architecture", "comparison",
])
def test_all_supported_poster_layout_types(diagram_type):
    svg, audit = build_educational_poster_svg(
        title="Photosynthesis",
        diagram_type=diagram_type,
        nodes=[
            DiagramNode(id="sun", label="Sunlight", description="Provides energy."),
            DiagramNode(id="chlorophyll", label="Chlorophyll", description="Absorbs light."),
            DiagramNode(id="glucose", label="Glucose", description="Stores chemical energy."),
        ],
        connections=[
            DiagramConnection(source="sun", target="chlorophyll", label="energizes"),
            DiagramConnection(source="chlorophyll", target="glucose", label="produces"),
        ],
        summary="Plants convert light energy into stored chemical energy.",
        main_subject="Biology",
    )
    ET.fromstring(svg)
    assert audit.valid


@pytest.mark.parametrize("theme", [
    "vibrant_educational", "science_technology", "creative_classroom",
    "professional_infographic", "nature_biology", "dark_neon_learning",
])
def test_poster_theme_selection(theme):
    svg, audit = build_educational_poster_svg(
        title="Water Cycle",
        diagram_type="process",
        nodes=[
            DiagramNode(id="evaporation", label="Evaporation", description="Water becomes vapour."),
            DiagramNode(id="collection", label="Collection", description="Water gathers in bodies."),
        ],
        connections=[DiagramConnection(source="evaporation", target="collection", label="cycles")],
        poster_settings=PosterDesignSettings(theme=theme),
        main_subject="Biology",
    )
    assert audit.valid


@pytest.mark.parametrize("orientation", ["portrait", "landscape", "square", "presentation_16_9"])
def test_poster_orientation(orientation):
    svg, audit = build_educational_poster_svg(
        title="Neural Network",
        diagram_type="architecture",
        nodes=cpu_nodes(),
        connections=cpu_connections(),
        poster_settings=PosterDesignSettings(orientation=orientation),
        main_subject="Machine Learning",
    )
    ET.fromstring(svg)
    assert audit.valid
    assert audit.width > 1000
    assert audit.height > 700


def test_subject_aware_colour_selection():
    computer = choose_subject_palette("CPU Pipeline Computer Science", "vibrant_educational")
    biology = choose_subject_palette("Photosynthesis Biology", "vibrant_educational")
    machine = choose_subject_palette("Machine Learning Neural Network", "vibrant_educational")
    assert computer["input"] == "#2376C9"
    assert biology["output"] == "#D09B26"
    assert machine["process"] == "#0786A5"


@pytest.mark.asyncio
async def test_topic_specific_poster_compositions():
    cases = [
        (
            "Create an infographic explaining Photosynthesis - How Plants Make Their Food. Include These Components: Sunlight, Chlorophyll, Chloroplasts, Carbon Dioxide, Water, Light-Dependent Reactions, Calvin Cycle, Glucose, Oxygen.",
            "flowchart",
            "photosynthesis",
        ),
        (
            "Create a water cycle poster showing Evaporation, Transpiration, Condensation, Precipitation, and Collection.",
            "process",
            "water_cycle",
        ),
        (
            "Explain the five stage CPU pipeline: Fetch, Decode, Execute, Memory Access, Write Back, and data, control, and structural hazards.",
            "process",
            "cpu_pipeline",
        ),
        (
            "Create a neural network educational poster with input layer, hidden layers, neurons, weights, biases, activation functions, and output layer.",
            "architecture",
            "neural_network",
        ),
        (
            "Create a machine learning workflow infographic for data collection, data cleaning, feature engineering, train-test split, model training, model evaluation, hyperparameter tuning, and prediction.",
            "process",
            "horizontal_process",
        ),
    ]
    provider = MockLLMProvider()
    for source, diagram_type, strategy in cases:
        content = await provider.understand_content(source)
        plan = await provider.plan_diagram(content, preferred_diagram_type=diagram_type)
        svg, audit = build_educational_poster_svg(
            title=content.title,
            diagram_type=plan.diagram_type,
            nodes=plan.nodes,
            connections=plan.connections,
            summary=content.summary,
            main_subject=content.main_subject,
            concepts=content.key_concepts,
            relationships=content.relationships,
            learning_objectives=content.learning_objectives,
            key_equations=content.key_equations,
        )
        ET.fromstring(svg)
        assert audit.valid, (content.title, audit.errors)
        assert audit.layout_strategy == strategy

        if strategy == "photosynthesis":
            assert content.title == "Photosynthesis"
            assert "How green plants convert sunlight into chemical energy." in svg
            assert "PHOTOSYNTHESIS EQUATION" in svg
            assert "6CO2 + 6H2O + Light Energy" in svg
            assert "Light-Dependent Reactions" in svg and "Calvin Cycle" in svg
            assert "M0 190" in svg
        elif strategy == "water_cycle":
            assert "stroke-dasharray=\"22 15\"" in svg
            assert "Evaporation" in svg and "Transpiration" in svg
        elif strategy == "cpu_pipeline":
            assert "INSTRUCTION FLOW THROUGH THE CPU" in svg
            assert "Data Hazards" in svg and "Control Hazards" in svg
            assert "Memory Access" in svg and "Write Back" in svg
        elif strategy == "neural_network":
            assert "INPUT LAYER" in svg and "OUTPUT LAYER" in svg
            assert "<circle cx=" in svg
        else:
            assert "Data Collection" in svg and "Model Evaluation" in svg
            assert "DATA</text>" in svg and "MODEL</text>" in svg
            assert "marker-end=\"url(#topic-arrow)\"" in svg


def test_ai_ml_deep_learning_uses_nested_concept_layout():
    nodes = [
        DiagramNode(id="ai", label="Artificial Intelligence", description="The broad field of machine intelligence."),
        DiagramNode(id="ml", label="Machine Learning", description="Learns patterns from data."),
        DiagramNode(id="deep", label="Deep Learning", description="Uses multi-layer neural networks."),
    ]
    svg, audit = build_educational_poster_svg(
        title="Artificial Intelligence vs Machine Learning vs Deep Learning",
        diagram_type="comparison",
        nodes=nodes,
        connections=[
            DiagramConnection(source="ai", target="ml", label="contains"),
            DiagramConnection(source="ml", target="deep", label="contains"),
        ],
        main_subject="Computer Science",
    )
    ET.fromstring(svg)
    assert audit.valid
    assert audit.layout_strategy == "nested_concepts"
    assert svg.count("<circle cx=") >= 3
    assert all(node.label.upper() in svg for node in nodes)


@pytest.mark.parametrize(
    "orientation,expected",
    [
        ("portrait", (1200, 1600)),
        ("landscape", (1600, 1000)),
        ("square", (1200, 1200)),
        ("presentation_16_9", (1600, 900)),
    ],
)
def test_specialized_poster_aspect_ratios(orientation, expected):
    svg, audit = build_educational_poster_svg(
        title="Photosynthesis",
        diagram_type="process",
        nodes=[
            DiagramNode(id="sunlight", label="Sunlight", description="Supplies energy."),
            DiagramNode(id="oxygen", label="Oxygen", description="Released to the atmosphere."),
            DiagramNode(id="chlorophyll", label="Chlorophyll", description="Captures light."),
            DiagramNode(id="chloroplasts", label="Chloroplasts", description="Host the process."),
            DiagramNode(id="water", label="Water", description="Absorbed by roots."),
            DiagramNode(id="carbon", label="Carbon Dioxide", description="Enters through leaves."),
            DiagramNode(id="glucose", label="Glucose", description="Supports growth."),
            DiagramNode(id="light", label="Light-Dependent Reactions", description="Capture energy."),
            DiagramNode(id="calvin", label="Calvin Cycle", description="Builds sugars."),
        ],
        connections=[
            DiagramConnection(source="sunlight", target="light"),
            DiagramConnection(source="water", target="light"),
            DiagramConnection(source="carbon", target="calvin"),
        ],
        poster_settings=PosterDesignSettings(orientation=orientation),
    )
    assert (audit.width, audit.height) == expected


def test_long_specialized_callout_falls_back_to_fit_to_content_layout():
    long_explanation = "Plants convert absorbed energy into chemical energy during photosynthesis. " * 18
    svg, audit = build_educational_poster_svg(
        title="Photosynthesis",
        diagram_type="process",
        nodes=[
            DiagramNode(id="sunlight", label="Sunlight", description=long_explanation),
            DiagramNode(id="water", label="Water", description="Water enters through the roots."),
            DiagramNode(id="glucose", label="Glucose", description="Glucose supports plant growth."),
        ],
        connections=[
            DiagramConnection(source="sunlight", target="water"),
            DiagramConnection(source="water", target="glucose"),
        ],
        summary="Plants convert light energy into chemical energy.",
    )
    ET.fromstring(svg)
    assert audit.valid
    assert audit.layout_strategy != "photosynthesis"
    assert audit.clipped_text_count == 0


@pytest.mark.parametrize("layout_style", [
    "educational_infographic", "scientific_poster", "illustrated_process",
    "concept_map_poster", "technical_architecture_poster",
])
def test_poster_layout_style(layout_style):
    svg, audit = build_educational_poster_svg(
        title="Machine Learning Workflow",
        diagram_type="process",
        nodes=[
            DiagramNode(id="data", label="Data Collection", description="Gather representative examples."),
            DiagramNode(id="train", label="Model Training", description="Fit parameters to examples."),
        ],
        connections=[DiagramConnection(source="data", target="train", label="trains")],
        poster_settings=PosterDesignSettings(layout_style=layout_style),
        main_subject="Machine Learning",
    )
    assert audit.valid
    ET.fromstring(svg)


def test_long_topic_and_empty_or_invalid_specs():
    long_title = "Advanced Distributed Machine Learning Systems " * 12
    svg, audit = build_educational_poster_svg(
        title=long_title,
        diagram_type="process",
        nodes=[DiagramNode(id="one", label="Data Collection", description="Collect representative data.")],
        connections=[],
        main_subject="Computer Science",
        poster_settings=PosterDesignSettings(orientation="presentation_16_9"),
    )
    ET.fromstring(svg)
    assert audit.valid
    assert long_title not in svg or len(svg) > 100

    with pytest.raises(ValueError):
        build_educational_poster_svg(title="Invalid", diagram_type="process", nodes=[], connections=[])
    with pytest.raises(ValueError):
        build_educational_poster_svg(
            title="Invalid",
            diagram_type="process",
            nodes=[DiagramNode(id="a", label="A")],
            connections=[DiagramConnection(source="missing", target="a")],
        )
