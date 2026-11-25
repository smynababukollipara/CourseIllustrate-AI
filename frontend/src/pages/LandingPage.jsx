import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Sparkles, 
  ArrowRight, 
  Layers, 
  Cpu, 
  Network, 
  CheckCircle, 
  BrainCircuit, 
  Palette, 
  ShieldCheck, 
  FileText, 
  Download,
  BookOpen,
  GitBranch,
  FileCheck2,
  Workflow
} from 'lucide-react';

export const LandingPage = () => {
  const exampleDiagrams = [
    {
      title: "5-Stage CPU Pipeline",
      category: "Computer Architecture",
      diagramType: "Process Diagram",
      description: "Overlaps instruction fetch, decode, execute, memory access, and write-back cycles to maximize throughput.",
      tags: ["IF", "ID", "EX", "MEM", "WB"]
    },
    {
      title: "Neural Network Backpropagation",
      category: "Machine Learning",
      diagramType: "Flowchart & Math Graph",
      description: "Traces forward inference prediction loss and multivariable chain-rule gradient flow.",
      tags: ["Forward Pass", "Loss Metric", "Chain Rule", "SGD Update"]
    },
    {
      title: "Binary Search Divide & Conquer",
      category: "Algorithms & Data Structures",
      diagramType: "Hierarchical Tree",
      description: "Visualizes O(log N) search interval bisection, comparator branching, and boundary convergence.",
      tags: ["Sorted Array", "Midpoint", "Prune Half", "O(log N)"]
    },
    {
      title: "Microservices Event-Driven Mesh",
      category: "Distributed Systems",
      diagramType: "Architecture Diagram",
      description: "Decoupled domain services communicating via transactional message brokers and API gateways.",
      tags: ["API Gateway", "Kafka Bus", "Read Replicas", "Circuit Breaker"]
    }
  ];

  const workflowSteps = [
    {
      number: "01",
      title: "Content Ingestion",
      agent: "Content Understanding Agent",
      desc: "Ingests raw educational lecture text or extracts multi-page PDF documents page by page via PyMuPDF."
    },
    {
      number: "02",
      title: "Pedagogical Planning",
      agent: "Diagram Planning Agent",
      desc: "Synthesizes structured Mermaid diagram specifications matching flowcharts, mind maps, concept maps, or architecture."
    },
    {
      number: "03",
      title: "Quality Repair Loop",
      agent: "Quality Evaluation Agent",
      desc: "Deterministically audits syntax and concept coverage. If incomplete, triggers up to two automated repair cycles."
    },
    {
      number: "04",
      title: "Educational Illustration",
      agent: "Prompt & Image Generation Agents",
      desc: "Transforms pedagogical goals into detailed diffusion prompts to generate high-resolution educational concept art."
    }
  ];

  return (
    <div className="space-y-24 py-10">
      {/* Hero Section */}
      <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 sm:pt-16">
        <div className="relative z-10 text-center max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Specialized Educational Diagram & Illustration Platform</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
            Turn Educational Text & PDFs into{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Accurate Visual Course Diagrams
            </span>
          </h1>

          <p className="text-slate-300 text-lg sm:text-xl max-w-3xl mx-auto leading-relaxed">
            CourseIllustrate AI replaces slow, costly custom art commissions with a 5-agent LangGraph pipeline:
            generating syntactically verified vector diagrams and complementary educational illustrations for online course creators.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <Link
              to="/studio"
              className="inline-flex items-center gap-2 px-7 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-lg shadow-indigo-600/30 transition-all hover:translate-y-[-1px] text-sm"
            >
              <span>Launch Generation Studio</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold border border-slate-800 text-sm transition-all"
            >
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>View Dashboard & Stats</span>
            </Link>
          </div>

          {/* Problem Statement Callout Banner */}
          <div className="mt-12 p-5 rounded-2xl bg-slate-900/40 border border-slate-800 text-left max-w-3xl mx-auto">
            <div className="flex items-start gap-3">
              <BookOpen className="w-5 h-5 text-indigo-400 mt-1 shrink-0" />
              <div className="text-xs text-slate-400 leading-relaxed">
                <strong className="text-slate-200">The Core Problem:</strong> "Course-content teams need custom illustrations and diagrams across many topics, but commissioning original art for every lesson is slow and costly. A tool generating topic-specific diagrams and illustrations from text descriptions via diffusion would speed course-content."
              </div>
            </div>
          </div>
        </div>

        {/* Ambient background glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />
      </section>

      {/* How It Works Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto space-y-3 mb-16">
          <h2 className="text-3xl font-extrabold text-white">How CourseIllustrate AI Works</h2>
          <p className="text-slate-400 text-sm">
            Coordinated by a LangGraph state machine with an automated quality validation repair loop.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {workflowSteps.map((step) => (
            <div
              key={step.number}
              className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-indigo-500/40 transition-colors space-y-4 relative"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl font-black text-indigo-400/40">{step.number}</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  Agent
                </span>
              </div>
              <h3 className="text-base font-bold text-white">{step.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{step.desc}</p>
              <div className="pt-2 border-t border-slate-800/80">
                <span className="text-[11px] font-mono text-indigo-300 flex items-center gap-1">
                  <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" />
                  {step.agent}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Hybrid Architecture Highlight */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-8 sm:p-12 rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 border border-slate-800 space-y-8">
          <div className="max-w-3xl space-y-3">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-widest">
              Core Architectural Innovation
            </span>
            <h2 className="text-3xl font-extrabold text-white">
              Structured Diagrams & Educational Illustrations
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Provider-generated illustrations can complement precise technical diagrams. CourseIllustrate AI pairs <strong className="text-white">Output A (Verified Vector Diagram)</strong> with <strong className="text-white">Output B (Educational Illustration)</strong>; in development mode, Output B is clearly labeled as a local preview.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800/80 space-y-3">
              <div className="flex items-center gap-2 text-indigo-400 font-bold text-sm">
                <GitBranch className="w-4 h-4" />
                <span>Output A: Structured Vector Diagram</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Rendered with Mermaid.js, SVG, and structured JSON specifications. Guaranteed readable technical labels, explicit stage prerequisites, and deterministic syntax validation.
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800/80 space-y-3">
              <div className="flex items-center gap-2 text-violet-400 font-bold text-sm">
                <Palette className="w-4 h-4" />
                <span>Output B: Educational Illustration</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Uses the configured image provider when available. Local development previews are labeled and are not represented as generated diffusion images.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Example Topics Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h2 className="text-3xl font-extrabold text-white">Preset Educational Demonstrations</h2>
            <p className="text-slate-400 text-sm mt-1">Explore real diagrams generated across computer science and STEM domains.</p>
          </div>
          <Link to="/studio" className="text-xs font-bold text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">
            <span>Try these in Studio</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {exampleDiagrams.map((ex, i) => (
            <div
              key={i}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                  {ex.category}
                </span>
                <h3 className="text-base font-bold text-white">{ex.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{ex.description}</p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 space-y-2">
                <div className="flex flex-wrap gap-1.5">
                  {ex.tags.map((t, idx) => (
                    <span key={idx} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Technology Stack Badges */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-900 pt-16">
        <div className="text-center max-w-xl mx-auto space-y-3 mb-8">
          <h3 className="text-lg font-bold text-white">Production AI Architecture</h3>
          <p className="text-xs text-slate-400">Constructed on proven generative AI and vector orchestration frameworks.</p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          {[
            "LangGraph StateGraph",
            "Google Gemini API",
            "Stable Diffusion",
            "Hugging Face Inference",
            "Mermaid.js",
            "PyMuPDF",
            "FastAPI Async",
            "SQLAlchemy + SQLite",
            "React 18 + Vite",
            "Tailwind CSS"
          ].map((tech, i) => (
            <span
              key={i}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
