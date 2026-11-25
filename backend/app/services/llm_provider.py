import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, List

from app.config import settings
from app.schemas.generation import (
    ConceptItem,
    ContentUnderstandingOutput,
    DiagramPlanningOutput,
    DiagramNode,
    DiagramConnection
)

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM generation providers."""

    @abstractmethod
    async def understand_content(
        self,
        raw_text: str,
        custom_focus: Optional[str] = None
    ) -> ContentUnderstandingOutput:
        """Extract structured concepts, title, and pedagogical summary from text."""
        pass

    @abstractmethod
    async def plan_diagram(
        self,
        content: ContentUnderstandingOutput,
        preferred_diagram_type: str = "flowchart",
        custom_focus: Optional[str] = None,
        repair_feedback: Optional[str] = None
    ) -> DiagramPlanningOutput:
        """Generate valid Mermaid.js diagram code matching pedagogical goals."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Realistic mock provider for local development, UI testing, and CI without API keys.
    Dynamically analyzes input text to generate pedagogically coherent concepts
    and verified, error-free Mermaid.js diagrams.
    """

    @property
    def is_mock(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "MockLLMProvider (Offline Development Mode)"

    async def understand_content(
        self,
        raw_text: str,
        custom_focus: Optional[str] = None
    ) -> ContentUnderstandingOutput:
        """
        Dynamically extracts concepts and structure from the input text
        using lightweight NLP heuristics and semantic pattern matching.
        """
        cleaned_text = raw_text.strip()
        lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]

        # 1. Infer Title
        title = "Course Learning Module"
        lower_text = cleaned_text.lower()
        known_topics = (
            ("photosynthesis", "Photosynthesis"),
            ("water cycle", "Water Cycle"),
            ("cpu pipeline", "CPU Pipeline"),
            ("neural network", "Neural Network"),
            ("machine learning", "Machine Learning"),
        )
        for marker, canonical_title in known_topics:
            if marker in lower_text:
                title = canonical_title
                break

        instruction_openers = (
            "create ", "make ", "generate ", "design ", "include ",
            "show ", "add ", "draw ", "build ", "produce ",
        )
        for line in lines[:3]:
            cleaned_line = re.sub(r"^[#\-\*\s]+", "", line)
            if title != "Course Learning Module":
                break
            if cleaned_line.lower().startswith(instruction_openers):
                continue
            if any(cleaned_line.lower().startswith(p) for p in ["course", "lecture", "chapter", "module", "topic"]):
                title = re.sub(r"^(?:course|lecture|chapter|module|topic)\s*:\s*", "", cleaned_line, flags=re.I)
                break
            elif len(cleaned_line) < 60 and not cleaned_line.endswith("."):
                title = cleaned_line
                break

        if "cpu pipeline" in lower_text or ("pipeline" in lower_text and "cpu" in lower_text):
            title = "CPU Pipeline"

        # 2. Extract Key Sentences / Segments
        sentences = re.split(r"(?<=[.!?])\s+", cleaned_text)
        instruction_phrases = (
            "create a", "create an", "include these", "generate an", "generate a",
            "show the following", "show these", "add a key takeaway", "add key takeaway",
            "the resulting poster", "the poster must", "important:",
        )
        sentences = [
            s.strip() for s in sentences
            if len(s.strip()) > 15
            and not any(phrase in s.lower() for phrase in instruction_phrases)
        ]

        # 3. Dynamic concept discovery
        found_concepts: List[ConceptItem] = []

        # Look for explicit definitions or keywords (e.g. "X is...", "X refers to...", "X:")
        for idx, s in enumerate(sentences[:10]):
            match = re.search(r"^([A-Z][A-Za-z0-9\s]{2,30})\s*(?:is|refers to|represents|means|:)\s*(.+)", s, re.IGNORECASE)
            if match:
                c_name = match.group(1).strip()
                c_def = match.group(2).strip()
                c_id = re.sub(r"[^a-z0-9]+", "_", c_name.lower()).strip("_")
                if c_id and not any(c.id == c_id for c in found_concepts):
                    found_concepts.append(
                        ConceptItem(
                            id=c_id,
                            name=c_name.title(),
                            definition=c_def,
                            importance="core" if idx < 3 else "secondary",
                            related_to=[]
                        )
                    )

        # Domain-specific concept catalogs for realistic educational demonstrations
        relationships: List[str] = []
        learning_objectives: List[str] = []
        key_equations: List[str] = []

        if "photosynthesis" in lower_text:
            title = "Photosynthesis"
            found_concepts = [
                ConceptItem(id="sunlight", name="Sunlight", definition="Light energy absorbed by chlorophyll drives the reactions.", importance="core", related_to=["light_dependent_reactions"]),
                ConceptItem(id="chlorophyll", name="Chlorophyll", definition="Green pigment that captures light energy in the leaves.", importance="core", related_to=["light_dependent_reactions"]),
                ConceptItem(id="chloroplasts", name="Chloroplasts", definition="Plant cell organelles where photosynthesis takes place.", importance="core", related_to=["light_dependent_reactions", "calvin_cycle"]),
                ConceptItem(id="carbon_dioxide", name="Carbon Dioxide", definition="CO2 enters leaves through stomata and supplies carbon for sugar.", importance="core", related_to=["calvin_cycle"]),
                ConceptItem(id="water", name="Water", definition="Water absorbed by roots supplies electrons and hydrogen.", importance="core", related_to=["light_dependent_reactions"]),
                ConceptItem(id="light_dependent_reactions", name="Light-Dependent Reactions", definition="Capture light energy and convert it into chemical energy, releasing oxygen.", importance="core", related_to=["calvin_cycle", "oxygen"]),
                ConceptItem(id="calvin_cycle", name="Calvin Cycle", definition="Uses carbon dioxide and chemical energy to build sugar molecules.", importance="core", related_to=["glucose"]),
                ConceptItem(id="glucose", name="Glucose", definition="Energy-rich sugar produced by the plant and used for growth.", importance="core", related_to=[]),
                ConceptItem(id="oxygen", name="Oxygen", definition="Released into the atmosphere as a product of the light-dependent reactions.", importance="core", related_to=[]),
            ]
            relationships = [
                "Chlorophyll in chloroplasts absorbs sunlight",
                "Water enters the light-dependent reactions",
                "Light-dependent reactions release oxygen and supply chemical energy",
                "The Calvin Cycle uses carbon dioxide and chemical energy to produce glucose",
            ]
            learning_objectives = [
                "Photosynthesis converts light energy into chemical energy.",
                "Chlorophyll absorbs light.",
                "Oxygen is released.",
                "Glucose supports plant growth.",
            ]
            key_equations = ["6CO2 + 6H2O + Light Energy → C6H12O6 + 6O2"]
            summary = "How green plants convert sunlight into chemical energy."
        elif "water cycle" in lower_text:
            title = "Water Cycle"
            found_concepts = [
                ConceptItem(id="evaporation", name="Evaporation", definition="Sunlight warms surface water, changing liquid water into vapor.", importance="core", related_to=["condensation"]),
                ConceptItem(id="transpiration", name="Transpiration", definition="Plants release water vapor from their leaves into the atmosphere.", importance="core", related_to=["condensation"]),
                ConceptItem(id="condensation", name="Condensation", definition="Water vapor cools and forms tiny droplets in clouds.", importance="core", related_to=["precipitation"]),
                ConceptItem(id="precipitation", name="Precipitation", definition="Water falls from clouds as rain, snow, sleet, or hail.", importance="core", related_to=["collection"]),
                ConceptItem(id="collection", name="Collection", definition="Water gathers in rivers, lakes, oceans, and groundwater.", importance="core", related_to=["evaporation"]),
            ]
            relationships = [
                "Evaporation and transpiration add vapor to the atmosphere",
                "Condensation forms clouds",
                "Precipitation returns water to Earth's surface",
                "Collection feeds evaporation and groundwater",
            ]
            learning_objectives = ["Solar energy drives the continuous movement of water through Earth's systems."]
            summary = "Water continually moves between Earth's surface and atmosphere."
        elif "neural network" in lower_text:
            title = "Neural Network"
            found_concepts = [
                ConceptItem(id="input_layer", name="Input Layer", definition="Receives the features presented to the network.", importance="core", related_to=["hidden_layers"]),
                ConceptItem(id="neurons", name="Neurons", definition="Units that combine incoming signals and compute an output.", importance="core", related_to=["activation_functions"]),
                ConceptItem(id="weights_biases", name="Weights & Biases", definition="Learnable parameters that scale and shift neuron inputs.", importance="core", related_to=["activation_functions"]),
                ConceptItem(id="activation_functions", name="Activation Functions", definition="Introduce nonlinear transformations between network layers.", importance="core", related_to=["hidden_layers"]),
                ConceptItem(id="hidden_layers", name="Hidden Layers", definition="Intermediate neuron layers that learn representations.", importance="core", related_to=["output_layer"]),
                ConceptItem(id="output_layer", name="Output Layer", definition="Produces the network's final prediction.", importance="core", related_to=[]),
            ]
            relationships = [
                "Input features flow into neurons",
                "Weights and biases shape each neuron's signal",
                "Activation functions transform signals between hidden layers",
                "The output layer produces the prediction",
            ]
            learning_objectives = ["Trace how learned parameters transform inputs into predictions."]
            summary = "A neural network transforms input features through connected layers of learnable neurons."
        elif "machine learning" in lower_text:
            title = "Machine Learning Workflow"
            found_concepts = [
                ConceptItem(id="data_collection", name="Data Collection", definition="Gather representative examples for the task.", importance="core", related_to=["data_cleaning"]),
                ConceptItem(id="data_cleaning", name="Data Cleaning", definition="Fix missing, inconsistent, or incorrect records.", importance="core", related_to=["feature_engineering"]),
                ConceptItem(id="feature_engineering", name="Feature Engineering", definition="Prepare useful input signals for a model.", importance="core", related_to=["train_test_split"]),
                ConceptItem(id="train_test_split", name="Train-Test Split", definition="Separate examples for fitting and unbiased evaluation.", importance="core", related_to=["model_training"]),
                ConceptItem(id="model_training", name="Model Training", definition="Fit model parameters using the training examples.", importance="core", related_to=["model_evaluation"]),
                ConceptItem(id="model_evaluation", name="Model Evaluation", definition="Measure predictive quality on held-out examples.", importance="core", related_to=["hyperparameter_tuning"]),
                ConceptItem(id="hyperparameter_tuning", name="Hyperparameter Tuning", definition="Select settings that improve validation performance.", importance="secondary", related_to=["prediction"]),
                ConceptItem(id="prediction", name="Prediction", definition="Apply the selected model to new inputs.", importance="core", related_to=[]),
            ]
            relationships = [f"{found_concepts[i].name} leads to {found_concepts[i+1].name}" for i in range(len(found_concepts) - 1)]
            learning_objectives = ["Follow data preparation, model evaluation, and prediction as one repeatable workflow."]
            summary = "A disciplined workflow turns raw data into a tested model and useful predictions."
        elif "cpu pipeline" in lower_text or ("pipeline" in lower_text and "cpu" in lower_text):
            found_concepts = [
                ConceptItem(id="instruction_fetch", name="Instruction Fetch", definition="Retrieves instructions sequentially from instruction cache or main memory.", importance="core", related_to=["instruction_decode"]),
                ConceptItem(id="instruction_decode", name="Instruction Decode", definition="Decodes machine opcode, reads register operands, and resolves control signals.", importance="core", related_to=["execution"]),
                ConceptItem(id="execution", name="Execution", definition="Executes arithmetic/logical operations via the ALU and evaluates branch conditions.", importance="core", related_to=["memory_access"]),
                ConceptItem(id="memory_access", name="Memory Access", definition="Reads data operands from or commits updates to the data memory bus.", importance="core", related_to=["write_back"]),
                ConceptItem(id="write_back", name="Write Back", definition="Writes ALU results or retrieved memory data back into the register file.", importance="core", related_to=[]),
                ConceptItem(id="data_hazard", name="Data Hazards", definition="An instruction depends on a result that an earlier instruction has not yet written.", importance="secondary"),
                ConceptItem(id="control_hazard", name="Control Hazards", definition="A branch changes which instruction should enter the pipeline next.", importance="secondary"),
                ConceptItem(id="structural_hazard", name="Structural Hazards", definition="Two stages compete for the same hardware resource in one cycle.", importance="secondary"),
                ConceptItem(id="pipeline_benefit", name="Throughput Benefit", definition="Overlapping instruction stages increases completed instructions per unit time.", importance="secondary")
            ]
            relationships = [
                "Instruction Fetch precedes Instruction Decode",
                "Instruction Decode precedes Execution",
                "Execution precedes Memory Access",
                "Memory Access precedes Write Back"
            ]
            learning_objectives = [
                "Understand how instruction throughput is maximized via pipelined overlapping execution stages.",
                "Identify potential pipeline hazards: structural, data, and control."
            ]
            summary = "CPU pipelining overlaps instruction processing stages to dramatically increase clock-cycle instruction throughput."

        elif len(found_concepts) < 4:
            if any(k in lower_text for k in ["gradient", "neural", "learning", "model", "train", "loss"]):
                found_concepts = [
                    ConceptItem(id="input_data", name="Training Features", definition="Raw input representations fed into computational tensor layers.", importance="core", related_to=["forward_pass"]),
                    ConceptItem(id="forward_pass", name="Forward Propagation", definition="Sequential calculation of layer outputs and candidate predictions.", importance="core", related_to=["loss_calculation"]),
                    ConceptItem(id="loss_calculation", name="Objective Loss Metric", definition="Quantification of prediction error relative to ground truth labels.", importance="core", related_to=["backpropagation"]),
                    ConceptItem(id="backpropagation", name="Gradient Backpropagation", definition="Computing partial derivatives via chain rule for parameter updates.", importance="core", related_to=["optimizer"]),
                    ConceptItem(id="optimizer", name="Gradient Optimization", definition="Applying parameter adjustments (SGD, Adam) to minimize empirical risk.", importance="secondary", related_to=[])
                ]
                relationships = [
                    "Training Features input into Forward Propagation",
                    "Forward Propagation predictions evaluated by Objective Loss Metric",
                    "Objective Loss Metric backpropagated via Gradient Backpropagation",
                    "Gradient Backpropagation computes gradients for Gradient Optimization"
                ]
                learning_objectives = [
                    "Understand iterative optimization loop in supervised neural networks.",
                    "Master forward inference vs backpropagation gradient flow."
                ]
            elif any(k in lower_text for k in ["binary search", "algorithm", "sort", "tree", "graph"]):
                found_concepts = [
                    ConceptItem(id="input_sequence", name="Ordered Sequence", definition="Sorted list or array fulfilling monotonic invariant constraints.", importance="core", related_to=["midpoint_eval"]),
                    ConceptItem(id="midpoint_eval", name="Midpoint Evaluation", definition="Bisecting current search interval to test candidate target.", importance="core", related_to=["binary_branching"]),
                    ConceptItem(id="binary_branching", name="Interval Elimination", definition="Discarding one half of search space based on comparator.", importance="core", related_to=["termination_check"]),
                    ConceptItem(id="termination_check", name="Convergence Condition", definition="Verifying target match or empty interval boundary condition.", importance="core", related_to=[])
                ]
                relationships = [
                    "Ordered Sequence enables Midpoint Evaluation",
                    "Midpoint Evaluation branches into Interval Elimination",
                    "Interval Elimination recurses toward Convergence Condition"
                ]
                learning_objectives = [
                    "Analyze logarithmic O(log N) time complexity guarantees of divide-and-conquer search.",
                    "Implement interval boundary pointer updates without off-by-one errors."
                ]
            else:
                found_concepts = [
                    ConceptItem(
                        id=f"concept_{i+1}",
                        name=f"Key Principle {i+1}",
                        definition=s,
                        importance="core" if i < 2 else "secondary",
                        related_to=[f"concept_{i+2}"] if i < min(len(sentences), 4) - 1 else []
                    )
                    for i, s in enumerate(sentences[:4])
                ]
                if not found_concepts:
                    found_concepts = [
                        ConceptItem(id="foundations", name="Core Foundations", definition="Essential principles and theoretical baseline of the topic.", importance="core", related_to=["methodology"]),
                        ConceptItem(id="methodology", name="Methodology & Process", definition="Primary procedural steps and execution logic.", importance="core", related_to=["evaluation"]),
                        ConceptItem(id="evaluation", name="Evaluation & Verification", definition="Assessing correctness, performance, and key takeaways.", importance="secondary", related_to=[])
                    ]
                relationships = [
                    f"{found_concepts[i].name} leads to {found_concepts[i+1].name}"
                    for i in range(len(found_concepts) - 1)
                ]
                learning_objectives = [
                    f"Master core principles of {title}.",
                    "Apply conceptual relationships in practical educational problem-solving."
                ]

            summary = (
                f"This learning module covers {title}. The content introduces {len(found_concepts)} essential "
                f"conceptual building blocks, progressing from fundamental foundations toward practical application."
            )
        else:
            relationships = [
                f"{found_concepts[i].name} precedes {found_concepts[i+1].name}"
                for i in range(len(found_concepts) - 1)
            ]
            learning_objectives = [
                f"Understand fundamental concepts of {title}.",
                "Analyze structural dependencies across key ideas."
            ]
            summary = (
                f"Educational overview of {title}, covering {len(found_concepts)} core concepts."
            )

        subtopics = [c.name for c in found_concepts if c.importance != "core"] or [c.name for c in found_concepts[2:]]

        return ContentUnderstandingOutput(
            title=title,
            summary=summary,
            key_concepts=found_concepts[:12],
            suggested_diagram_type="flowchart",
            pedagogical_notes="Review core conceptual dependencies sequentially before studying secondary relations.",
            main_subject=title,
            topics=[title],
            subtopics=subtopics,
            relationships=relationships,
            learning_objectives=learning_objectives,
            key_equations=key_equations,
            is_mock=True,
            provider_info=self.provider_name
        )

    async def plan_diagram(
        self,
        content: ContentUnderstandingOutput,
        preferred_diagram_type: str = "flowchart",
        custom_focus: Optional[str] = None,
        repair_feedback: Optional[str] = None
    ) -> DiagramPlanningOutput:
        """
        Generates clean, validated Mermaid.js diagram code and structured
        DiagramNode/DiagramConnection objects for all 7 supported diagram types.
        """
        dtype = preferred_diagram_type.lower()
        if dtype == "auto":
            dtype = content.suggested_diagram_type or "flowchart"

        concepts = content.key_concepts or [
            ConceptItem(id="step_a", name="Primary Concept", definition="First phase", importance="core"),
            ConceptItem(id="step_b", name="Secondary Concept", definition="Second phase", importance="core")
        ]

        nodes: List[DiagramNode] = []
        connections: List[DiagramConnection] = []

        # 1. Flowchart
        if dtype == "flowchart":
            lines = ["flowchart TD"]
            prev_id = None
            for c in concepts:
                safe_name = c.name.replace('"', "'")
                lines.append(f'    {c.id}["{safe_name}"]')
                if prev_id:
                    lines.append(f"    {prev_id} --> {c.id}")
                nodes.append(DiagramNode(id=c.id, label=c.name, description=c.definition))
                if prev_id:
                    connections.append(DiagramConnection(source=prev_id, target=c.id, label="proceeds to"))
                prev_id = c.id

            lines.append("    classDef default fill:#f1f3ff,stroke:#6d63df,stroke-width:2px,color:#263248;")
            lines.append("    classDef accent fill:#e9e7ff,stroke:#5145cd,stroke-width:2px,color:#263248;")
            mermaid_code = "\n".join(lines)
            explanation = "Sequential flowchart depicting the logical execution flow and prerequisites between concepts."

        # 2. Mind Map
        elif dtype == "mindmap":
            safe_title = content.title.replace('"', "'")
            lines = [
                "mindmap",
                f"  root(({safe_title}))"
            ]
            nodes.append(DiagramNode(id="root", label=content.title, description="Root topic"))
            for c in concepts:
                safe_name = c.name.replace('"', "'")
                lines.append(f"    {safe_name}")
                lines.append(f"      {c.importance.capitalize()} Concept")
                nodes.append(DiagramNode(id=c.id, label=c.name, description=c.definition, parent_id="root"))
                connections.append(DiagramConnection(source="root", target=c.id, label="branch"))
            mermaid_code = "\n".join(lines)
            explanation = "Hierarchical mind map visually grouping topics from core principles out to details."

        # 3. Concept Map
        elif dtype == "concept_map":
            lines = [
                "flowchart LR",
                f'    Central(("<b>{content.title}</b>"))'
            ]
            nodes.append(DiagramNode(id="Central", label=content.title, description="Central Subject"))
            for c in concepts:
                safe_name = c.name.replace('"', "'")
                relation_label = "involves" if c.importance == "core" else "supports"
                lines.append(f'    {c.id}["{safe_name}"]')
                lines.append(f"    Central -->|{relation_label}| {c.id}")
                nodes.append(DiagramNode(id=c.id, label=c.name, description=c.definition))
                connections.append(DiagramConnection(source="Central", target=c.id, label=relation_label))
            lines.append("    classDef default fill:#f8fafc,stroke:#38bdf8,stroke-width:2px,color:#263248;")
            lines.append("    classDef central fill:#eef0ff,stroke:#6d63df,stroke-width:3px,color:#263248;")
            lines.append("    class Central central;")
            mermaid_code = "\n".join(lines)
            explanation = "Relational concept map illustrating inter-conceptual semantic connections."

        # 4. Architecture Diagram
        elif dtype == "architecture":
            lines = [
                "flowchart TB",
                '    subgraph Core_Layer ["1. Foundation & Conceptual Inputs"]',
            ]
            core_concepts = [c for c in concepts if c.importance == "core"] or concepts[:2]
            sec_concepts = [c for c in concepts if c.importance != "core"] or concepts[2:]

            for c in core_concepts:
                lines.append(f'        c_{c.id}["{c.name}"]')
                nodes.append(DiagramNode(id=f"c_{c.id}", label=c.name, description=c.definition))
            lines.append("    end")

            lines.append('    subgraph Process_Layer ["2. Operational Mechanics & Processing"]')
            for c in sec_concepts:
                lines.append(f'        s_{c.id}["{c.name}"]')
                nodes.append(DiagramNode(id=f"s_{c.id}", label=c.name, description=c.definition))
            lines.append("    end")

            if core_concepts and sec_concepts:
                lines.append(f"    c_{core_concepts[0].id} ==> s_{sec_concepts[0].id}")
                connections.append(DiagramConnection(source=f"c_{core_concepts[0].id}", target=f"s_{sec_concepts[0].id}", label="integrates"))

            lines.append("    classDef default fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1.5px,color:#263248;")
            mermaid_code = "\n".join(lines)
            explanation = "Multi-tier architectural block diagram segregating inputs, processing, and outcomes."

        # 5. Process Diagram
        elif dtype == "process":
            lines = ["flowchart LR"]
            prev_id = None
            for idx, c in enumerate(concepts):
                p_id = f"step_{idx+1}"
                lines.append(f'    {p_id}["Stage {idx+1}: {c.name}"]')
                nodes.append(DiagramNode(id=p_id, label=f"Stage {idx+1}: {c.name}", description=c.definition))
                if prev_id:
                    lines.append(f"    {prev_id} --> {p_id}")
                    connections.append(DiagramConnection(source=prev_id, target=p_id, label="advances"))
                prev_id = p_id
            lines.append("    classDef default fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#263248;")
            mermaid_code = "\n".join(lines)
            explanation = "Linear process diagram showing chronological transformation through each educational stage."

        # 6. Hierarchical Diagram
        elif dtype == "hierarchical":
            lines = [
                "flowchart TD",
                f'    Root["<b>{content.title}</b>"]'
            ]
            nodes.append(DiagramNode(id="Root", label=content.title, description="Top-level taxonomy"))
            core_concepts = [c for c in concepts if c.importance == "core"] or concepts[:2]
            sec_concepts = [c for c in concepts if c.importance != "core"] or concepts[2:]

            for c in core_concepts:
                lines.append(f'    {c.id}["{c.name}"]')
                lines.append(f"    Root --> {c.id}")
                nodes.append(DiagramNode(id=c.id, label=c.name, description=c.definition, parent_id="Root"))
                connections.append(DiagramConnection(source="Root", target=c.id, label="tier 1"))

            for idx, c in enumerate(sec_concepts):
                parent = core_concepts[idx % len(core_concepts)].id if core_concepts else "Root"
                lines.append(f'    {c.id}["{c.name}"]')
                lines.append(f"    {parent} --> {c.id}")
                nodes.append(DiagramNode(id=c.id, label=c.name, description=c.definition, parent_id=parent))
                connections.append(DiagramConnection(source=parent, target=c.id, label="tier 2"))

            lines.append("    classDef default fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#263248;")
            mermaid_code = "\n".join(lines)
            explanation = "Hierarchical taxonomy diagram dividing top concepts into specialized sub-elements."

        # 7. Comparison Diagram
        elif dtype == "comparison":
            lines = [
                "flowchart TD",
                '    subgraph Core_Principles ["Core / Primary Aspects"]'
            ]
            core_concepts = [c for c in concepts if c.importance == "core"] or concepts[:2]
            sec_concepts = [c for c in concepts if c.importance != "core"] or concepts[2:]

            for c in core_concepts:
                lines.append(f'        left_{c.id}["{c.name}"]')
                nodes.append(DiagramNode(id=f"left_{c.id}", label=c.name, description=c.definition))
            lines.append("    end")

            lines.append('    subgraph Secondary_Aspects ["Secondary / Advanced Aspects"]')
            for c in sec_concepts:
                lines.append(f'        right_{c.id}["{c.name}"]')
                nodes.append(DiagramNode(id=f"right_{c.id}", label=c.name, description=c.definition))
            lines.append("    end")

            if core_concepts and sec_concepts:
                lines.append(f"    left_{core_concepts[0].id} <-.->|vs / comparison| right_{sec_concepts[0].id}")
                connections.append(DiagramConnection(source=f"left_{core_concepts[0].id}", target=f"right_{sec_concepts[0].id}", label="vs"))

            lines.append("    classDef default fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#263248;")
            mermaid_code = "\n".join(lines)
            explanation = "Comparative breakdown contrasting fundamental concepts against advanced applications."

        else:
            # Fallback
            lines = [
                "flowchart TD",
                f'    A["{content.title}"] --> B["Core Theory"]',
                '    B --> C["Practical Application"]'
            ]
            mermaid_code = "\n".join(lines)
            explanation = "Standard sequential educational diagram."
            nodes = [
                DiagramNode(id="A", label=content.title, description="Root"),
                DiagramNode(id="B", label="Core Theory", description="Theory"),
                DiagramNode(id="C", label="Practical Application", description="Application")
            ]
            connections = [
                DiagramConnection(source="A", target="B", label="leads to"),
                DiagramConnection(source="B", target="C", label="applies to")
            ]

        # Apply repair feedback note if regenerated
        if repair_feedback:
            explanation += f" (Refined based on quality review: {repair_feedback[:80]})"

        return DiagramPlanningOutput(
            diagram_type=dtype,  # type: ignore
            mermaid_code=mermaid_code,
            explanation=explanation,
            node_count=len(concepts),
            pedagogical_focus=custom_focus or f"Visual structure for {content.title}",
            title=content.title,
            nodes=nodes,
            connections=connections,
            layout_instructions=f"Arranged using {dtype} layout with {len(nodes)} conceptual nodes and {len(connections)} edges.",
            is_mock=True,
            provider_info=self.provider_name
        )


class GeminiLLMProvider(BaseLLMProvider):
    """
    Production LLM provider utilizing Google Gemini API with structured outputs.
    Activated whenever GEMINI_API_KEY is configured and USE_MOCK_LLM is False.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        # Lazy import of google-genai
        from google import genai
        self.client = genai.Client(api_key=api_key)

    @property
    def is_mock(self) -> bool:
        return False

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model_name})"

    async def understand_content(
        self,
        raw_text: str,
        custom_focus: Optional[str] = None
    ) -> ContentUnderstandingOutput:
        """Call Gemini model with structured output schema for content understanding."""
        prompt = (
            f"Analyze the following user-provided educational request. Separate the subject matter from "
            f"the user's design and formatting instructions. Derive a concise title from the actual "
            f"educational topic, not from an imperative opening such as 'Create an infographic'. "
            f"Extract 4 to 12 factual topic concepts with definitions, hierarchy, and interrelations. "
            f"Never emit instructions such as 'Include these components', 'Create a poster', 'Start', "
            f"'Outcome', or 'Key Takeaway' as concepts. Include equations explicitly stated or standard "
            f"for the named educational subject in key_equations.\n\n"
            f"Focus: {custom_focus or 'General pedagogical comprehension'}\n\n"
            f"Content:\n{raw_text[:12000]}"
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ContentUnderstandingOutput
            }
        )

        output: ContentUnderstandingOutput = response.parsed  # type: ignore
        output.is_mock = False
        output.provider_info = self.provider_name
        return output

    async def plan_diagram(
        self,
        content: ContentUnderstandingOutput,
        preferred_diagram_type: str = "flowchart",
        custom_focus: Optional[str] = None,
        repair_feedback: Optional[str] = None
    ) -> DiagramPlanningOutput:
        """Call Gemini model to generate validated Mermaid.js diagram code."""
        repair_note = f"\nCorrection instructions from previous validation: {repair_feedback}\n" if repair_feedback else ""
        prompt = (
            f"You are an expert educational visual designer. Create a validated, complete, and syntactically "
            f"clean Mermaid.js diagram of type '{preferred_diagram_type}' for the topic: '{content.title}'.\n\n"
            f"Summary: {content.summary}\n"
            f"Concepts: {[c.name for c in content.key_concepts]}\n"
            f"Custom angle: {custom_focus or 'Ensure maximum pedagogical clarity'}\n"
            f"{repair_note}\n"
            f"Rules:\n"
            f"- Output strictly valid Mermaid syntax.\n"
            f"- Do not use syntax brackets inside node text without quotes.\n"
            f"- Use concise node labels (concept names or short stage names); do not put definitions or clipped text in nodes.\n"
            f"- Put complete educational explanations in the structured node descriptions and overall explanation.\n"
            f"- Preserve all important concepts and accurate relationships.\n"
            f"- Keep user design prompts out of concept labels; never add nodes named Start, Outcome, "
            f"Include These Components, Create a Poster, or Key Takeaway unless those are literal course concepts."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": DiagramPlanningOutput
            }
        )

        output: DiagramPlanningOutput = response.parsed  # type: ignore
        output.is_mock = False
        output.provider_info = self.provider_name
        return output


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function returning the active LLM provider.
    Automatically returns MockLLMProvider if GEMINI_API_KEY is not set or USE_MOCK_LLM is enabled.
    """
    if settings.GEMINI_API_KEY and not settings.USE_MOCK_LLM:
        try:
            logger.info("Initializing Google Gemini provider (%s)...", settings.GEMINI_MODEL)
            return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini provider (%s). Falling back to Mock provider.", exc)
            return MockLLMProvider()

    logger.info("Using MockLLMProvider (Offline Development Mode).")
    return MockLLMProvider()
