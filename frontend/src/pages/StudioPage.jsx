import React, { useRef, useState } from 'react';
import { 
  UploadCloud, 
  AlertCircle, 
  Loader2, 
  FileText, 
  Image,
  Download,
  Sparkles, 
  GitBranch, 
  Layers, 
  Network, 
  Cpu, 
  BrainCircuit, 
  Palette,
  Sliders,
  CheckCircle2,
  RefreshCw,
  BookOpen
} from 'lucide-react';
import { uploadDocument, generateDiagram, getAssetUrl, getExportUrl } from '../services/api';
import MermaidViewer from '../components/studio/MermaidViewer';
import AgentMonitor from '../components/studio/AgentMonitor';

export const StudioPage = () => {
  // Input Selection
  const [activeTab, setActiveTab] = useState('text'); // 'text' | 'pdf'
  const [topic, setTopic] = useState('');
  const [lectureText, setLectureText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const fileInputRef = useRef(null);

  // Diagram & Illustration Settings
  const [diagramType, setDiagramType] = useState('flowchart');
  const [illustrationStyle, setIllustrationStyle] = useState('professional_educational');
  const [complexityLevel, setComplexityLevel] = useState('intermediate');
  const [generateIllustration, setGenerateIllustration] = useState(true);
  const [customFocus, setCustomFocus] = useState('');
  const [posterTheme, setPosterTheme] = useState('vibrant_educational');
  const [posterLayout, setPosterLayout] = useState('educational_infographic');
  const [posterOrientation, setPosterOrientation] = useState('portrait');
  const [posterColorScheme, setPosterColorScheme] = useState('subject_aware');
  const [posterComplexity, setPosterComplexity] = useState('balanced');

  // Execution States
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [agentStatus, setAgentStatus] = useState({});
  const [error, setError] = useState(null);
  const [generationResult, setGenerationResult] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState('poster');
  const [editDiagramRequest, setEditDiagramRequest] = useState(0);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [posterLoadFailed, setPosterLoadFailed] = useState(false);

  // Preset example prompts
  const presets = [
    {
      name: "CPU Pipeline",
      type: "process",
      style: "isometric",
      text: "Explain the working of a five-stage CPU pipeline: Instruction Fetch (IF), Instruction Decode (ID), Execution (EX), Memory Access (MEM), and Write Back (WB). Emphasize sequential stage dependencies."
    },
    {
      name: "Neural Network Backprop",
      type: "flowchart",
      style: "3d",
      text: "Explain Forward Propagation and Backpropagation in deep neural networks. Show how error gradients are calculated using the multivariable chain rule to update weights via gradient descent."
    },
    {
      name: "Binary Search",
      type: "hierarchical",
      style: "minimalist",
      text: "Explain the Binary Search algorithm on a sorted array. Contrast the midpoint evaluation with interval elimination to demonstrate O(log N) logarithmic convergence."
    },
    {
      name: "Microservices Architecture",
      type: "architecture",
      style: "flat_vector",
      text: "Explain an event-driven microservices architecture featuring an API gateway, auth service, orders service, inventory service, Kafka message bus, and distributed databases."
    }
  ];

  const applyPreset = (preset) => {
    setActiveTab('text');
    setTopic(preset.name);
    setLectureText(preset.text);
    setDiagramType(preset.type);
    setIllustrationStyle(preset.style);
    setError(null);
  };

  const clearInput = () => {
    setActiveTab('text');
    setTopic('');
    setLectureText('');
    setSelectedFile(null);
    setUploadedDoc(null);
    setCustomFocus('');
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Handle PDF file selection
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a valid PDF file (.pdf)');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setUploadedDoc(null);
      setError(null);
    }
  };

  // Upload PDF material
  const handlePdfUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const data = await uploadDocument(selectedFile);
      setUploadedDoc(data);
    } catch (err) {
      console.error('Upload failed:', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to extract PDF.';
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Trigger LangGraph 5-Agent Pipeline
  const handleGenerate = async () => {
    setError(null);
    setIsGenerating(true);
    setAgentStatus({});

    try {
      const payload = {
        topic: topic.trim() || undefined,
        diagram_type: diagramType,
        illustration_style: illustrationStyle,
        complexity_level: complexityLevel,
        generate_illustration: generateIllustration,
        poster_settings: {
          theme: posterTheme,
          layout_style: posterLayout,
          orientation: posterOrientation,
          color_scheme: posterColorScheme,
          visual_complexity: posterComplexity
        },
        custom_focus: customFocus.trim() || undefined,
        ...(activeTab === 'pdf' && uploadedDoc
          ? { document_id: uploadedDoc.document_id }
          : { text_input: lectureText.trim() })
      };

      const res = await generateDiagram(payload);

      setGenerationResult(res);
      setActiveOutputTab('poster');
      setImageLoadFailed(false);
      setPosterLoadFailed(false);
      setAgentStatus(res.agent_status || {});
    } catch (err) {
      console.error('Diagram generation error:', err);
      const msg = err.response?.data?.detail || err.message || 'Multi-agent diagram generation failed.';
      setError(msg);
      const failedAgent = [
        ['content_understanding', 'Content Understanding Agent failed'],
        ['diagram_planning', 'Diagram Planning Agent failed'],
        ['quality_evaluation', 'Quality Evaluation Agent failed'],
        ['prompt_engineering', 'Prompt Engineering Agent failed'],
        ['image_generation', 'Image Generation Agent failed'],
      ].find(([, marker]) => String(msg).includes(marker));
      if (failedAgent) setAgentStatus({ [failedAgent[0]]: 'failed' });
    } finally {
      setIsGenerating(false);
    }
  };

  const diagramTypes = [
    { id: 'flowchart', name: 'Flowchart', icon: GitBranch, desc: 'Logical flow & prerequisites' },
    { id: 'mindmap', name: 'Mind Map', icon: Network, desc: 'Hierarchical taxonomy' },
    { id: 'concept_map', name: 'Concept Map', icon: Layers, desc: 'Relational semantic links' },
    { id: 'architecture', name: 'Architecture', icon: Cpu, desc: 'Layered component blocks' },
    { id: 'process', name: 'Process', icon: GitBranch, desc: 'Sequential chronologic steps' },
    { id: 'hierarchical', name: 'Hierarchy', icon: Layers, desc: 'Multi-level taxonomy' },
    { id: 'comparison', name: 'Comparison', icon: Sliders, desc: 'Side-by-side contrasting' }
  ];

  const styles = [
    { id: 'professional_educational', name: 'Professional Educational' },
    { id: 'minimalist', name: 'Minimalist Modern' },
    { id: 'scientific', name: 'Scientific Schematic' },
    { id: '3d', name: '3D Octane Render' },
    { id: 'hand_drawn', name: 'Academic Hand-Drawn' },
    { id: 'flat_vector', name: 'Flat Vector Art' },
    { id: 'isometric', name: 'Isometric Diorama' }
  ];

  return (
    <div className="studio-page mx-auto max-w-[1440px] px-4 py-8 sm:px-6 lg:px-8">
      {/* Studio Header */}
      <header className="studio-header flex flex-col gap-5 border-b border-slate-200 pb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-indigo-700">
              <Sparkles className="h-3.5 w-3.5" /> AI learning studio
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              Create Amazing Learning Visuals
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
              Transform educational ideas into beautifully illustrated diagrams and learning posters using AI.
            </p>
          </div>
          <div
            className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-xs font-bold ${
              isGenerating
                ? 'border-indigo-200 bg-indigo-50 text-indigo-700'
                : generationResult
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-slate-200 bg-white text-slate-600'
            }`}
            role="status"
          >
            <span className={`h-2 w-2 rounded-full ${isGenerating ? 'animate-pulse bg-indigo-600' : generationResult ? 'bg-emerald-500' : 'bg-slate-400'}`} />
            {isGenerating ? 'Generation in progress' : generationResult ? 'Visuals generated' : 'Ready to create'}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500">
            <BookOpen className="h-3.5 w-3.5 text-indigo-600" /> Start with an example
          </span>
          {presets.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => applyPreset(p)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              {p.name}
            </button>
          ))}
        </div>
      </header>

      <div className="mt-7 space-y-8">
        {/* Educational Input Workspace */}
        <section aria-labelledby="input-workspace-title" className="studio-panel rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">01 · Start with your material</p>
              <h2 id="input-workspace-title" className="mt-1 text-xl font-bold text-slate-900">Educational Input Workspace</h2>
            </div>
            <button
              type="button"
              onClick={clearInput}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              <RefreshCw className="h-4 w-4" /> Clear input
            </button>
          </div>
          <div className="space-y-5">
            {/* 1. Input Tab Selection */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Choose an input source
              </span>
              <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-100 p-1 text-sm" role="tablist" aria-label="Educational input source">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'text'}
                  onClick={() => setActiveTab('text')}
                  className={`px-3 py-1 rounded-md font-semibold transition-colors ${
                    activeTab === 'text'
                      ? 'bg-[#4934C6] text-white shadow-sm'
                      : 'bg-transparent text-slate-700 hover:bg-white'
                  }`}
                >
                  Direct Text
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'pdf'}
                  onClick={() => setActiveTab('pdf')}
                  className={`px-3 py-1 rounded-md font-semibold transition-colors ${
                    activeTab === 'pdf'
                      ? 'bg-[#4934C6] text-white shadow-sm'
                      : 'bg-transparent text-slate-700 hover:bg-white'
                  }`}
                >
                  Course PDF
                </button>
              </div>
            </div>

            {activeTab === 'text' ? (
              <div className="grid gap-4 lg:grid-cols-[minmax(220px,0.75fr)_minmax(0,1.8fr)]">
                <label className="space-y-2 text-sm font-semibold text-slate-700">
                  Educational topic
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Photosynthesis"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <label className="space-y-2 text-sm font-semibold text-slate-700">
                  Detailed description
                  <textarea
                    rows={5}
                    value={lectureText}
                    onChange={(e) => setLectureText(e.target.value)}
                    placeholder="Enter a topic or describe the educational concept you want to visualize..."
                    className="w-full resize-y rounded-xl border border-slate-300 bg-white p-3.5 text-sm leading-relaxed text-slate-800 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
              </div>
            ) : (
              <div className="space-y-3">
                <label className="block max-w-md space-y-2 text-sm font-semibold text-slate-700">
                  Educational topic (optional)
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Photosynthesis"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <form onSubmit={handlePdfUpload} className="space-y-3">
                  <div className="relative cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition-colors hover:border-indigo-400 hover:bg-indigo-50/40">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf"
                      onChange={handleFileChange}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      disabled={isUploading}
                    />
                    <div className="space-y-1.5 pointer-events-none">
                      <FileText className="mx-auto h-8 w-8 text-indigo-600" />
                      {selectedFile ? (
                        <p className="text-sm font-semibold text-slate-800">{selectedFile.name}</p>
                      ) : (
                        <p className="text-sm text-slate-600">Choose or drop course PDF</p>
                      )}
                    </div>
                  </div>

                  {selectedFile && !uploadedDoc && (
                    <button
                      type="submit"
                      disabled={isUploading}
                      className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#4934C6] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#3826A8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Extracting text via PyMuPDF...</span>
                        </>
                      ) : (
                        <>
                          <UploadCloud className="w-3.5 h-3.5" />
                          <span>Extract PDF Pages</span>
                        </>
                      )}
                    </button>
                  )}
                </form>

                {uploadedDoc && (
                  <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                    <span className="font-semibold truncate max-w-[200px]">{uploadedDoc.filename}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 font-bold">{uploadedDoc.page_count} Pages</span>
                  </div>
                )}
              </div>
            )}

            {/* 2. Diagram Type Selector */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Diagram type
              </span>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
                {diagramTypes.map((type) => {
                  const Icon = type.icon;
                  const isSelected = diagramType === type.id;
                  return (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setDiagramType(type.id)}
                      className={`p-2.5 rounded-xl text-left border transition-all ${
                        isSelected
                          ? 'border-[#4934C6] bg-[#4934C6] text-white shadow-md shadow-indigo-900/15'
                          : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50'
                      }`}
                      aria-pressed={isSelected}
                    >
                      <div className="flex items-center gap-1.5">
                        <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-white' : 'text-indigo-700'}`} />
                        <span className="text-xs font-bold">{type.name}</span>
                      </div>
                      <p className={`mt-1 text-[10px] leading-snug ${isSelected ? 'text-indigo-100' : 'text-slate-600'}`}>{type.desc}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Illustration & Style Settings */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700">
                  <Palette className="h-3.5 w-3.5 text-violet-700" />
                  <span>Illustration options</span>
                </span>
                <label className="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={generateIllustration}
                    onChange={(e) => setGenerateIllustration(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0 focus:outline-none"
                  />
                  <span className="text-xs font-semibold text-slate-700">Generate illustration</span>
                </label>
              </div>

              {generateIllustration && (
                <div className="grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">
                      Illustration Artistic Style
                    </label>
                    <select
                      value={illustrationStyle}
                      onChange={(e) => setIllustrationStyle(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    >
                      {styles.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-700">
                      Complexity Level
                    </label>
                    <div className="grid grid-cols-3 gap-2 text-xs" role="group" aria-label="Illustration complexity">
                      {['introductory', 'intermediate', 'advanced'].map((lvl) => (
                        <button
                          key={lvl}
                          type="button"
                          onClick={() => setComplexityLevel(lvl)}
                          className={`py-1.5 rounded-lg font-medium capitalize border transition-all ${
                            complexityLevel === lvl
                              ? 'border-[#4934C6] bg-[#4934C6] font-bold text-white'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-300'
                          }`}
                          aria-pressed={complexityLevel === lvl}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Optional Pedagogical Angle */}
            <div className="space-y-1 pt-1">
              <label className="text-xs font-semibold text-slate-700">
                Optional Custom Focus or Angle
              </label>
              <input
                type="text"
                value={customFocus}
                onChange={(e) => setCustomFocus(e.target.value)}
                placeholder="e.g., Emphasize clock cycles and pipeline stalls"
                className="w-full rounded-xl border border-slate-300 bg-white p-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            <details className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <summary className="cursor-pointer text-sm font-bold text-slate-800">
                Poster design settings
              </summary>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-slate-700">Poster Theme</span>
                  <select value={posterTheme} onChange={(e) => setPosterTheme(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800">
                    <option value="vibrant_educational">Vibrant Educational</option>
                    <option value="science_technology">Science &amp; Technology</option>
                    <option value="creative_classroom">Creative Classroom</option>
                    <option value="professional_infographic">Professional Infographic</option>
                    <option value="nature_biology">Nature &amp; Biology</option>
                    <option value="dark_neon_learning">Dark Neon Learning</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-slate-700">Layout Style</span>
                  <select value={posterLayout} onChange={(e) => setPosterLayout(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800">
                    <option value="educational_infographic">Educational Infographic</option>
                    <option value="scientific_poster">Scientific Poster</option>
                    <option value="illustrated_process">Illustrated Process</option>
                    <option value="concept_map_poster">Concept Map Poster</option>
                    <option value="technical_architecture_poster">Technical Architecture Poster</option>
                  </select>
                </label>
                <label className="space-y-1">
                    <span className="text-xs font-semibold text-slate-700">Orientation</span>
                    <select value={posterOrientation} onChange={(e) => setPosterOrientation(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800">
                      <option value="portrait">Portrait</option>
                      <option value="landscape">Landscape</option>
                      <option value="square">Square</option>
                      <option value="presentation_16_9">Presentation 16:9</option>
                    </select>
                </label>
                <label className="space-y-1">
                    <span className="text-xs font-semibold text-slate-700">Visual Complexity</span>
                    <select value={posterComplexity} onChange={(e) => setPosterComplexity(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800">
                      <option value="introductory">Introductory</option>
                      <option value="balanced">Balanced</option>
                      <option value="detailed">Detailed</option>
                    </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-semibold text-slate-700">Colour Scheme</span>
                  <select value={posterColorScheme} onChange={(e) => setPosterColorScheme(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-800">
                    <option value="subject_aware">Subject-aware</option>
                    <option value="theme_palette">Theme palette</option>
                  </select>
                </label>
              </div>
            </details>

            {error && (
              <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
            )}

            {/* Generate Action Button */}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || (activeTab === 'pdf' && !uploadedDoc) || (activeTab === 'text' && !lectureText.trim() && !topic.trim())}
              className={`flex w-full items-center justify-center gap-2 rounded-xl py-4 text-sm font-extrabold transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700 ${
                isGenerating || (activeTab === 'pdf' && !uploadedDoc) || (activeTab === 'text' && !lectureText.trim() && !topic.trim())
                  ? 'cursor-not-allowed bg-slate-200 text-slate-500'
                  : 'bg-[#4934C6] text-white shadow-lg shadow-indigo-900/20 hover:-translate-y-0.5 hover:bg-[#3826A8]'
              }`}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Executing 5-Agent Pipeline...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Learning Visual</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Actual backend statuses are shown in fixed visual order. */}
        <section aria-label="AI agent execution">
          <AgentMonitor
            agentStatus={agentStatus}
            executionLogs={generationResult?.execution_logs || []}
            retryCount={generationResult?.retry_count || 0}
            isGenerating={isGenerating}
          />
        </section>

        {/* Generated visuals are intentionally placed after input and execution. */}
        <section aria-labelledby="visuals-title" className="studio-output space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">03 · Explore and export</p>
              <h2 id="visuals-title" className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
                Your Learning Visuals
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {generationResult
                  ? 'Your educational poster, structured diagram and AI illustration are ready.'
                  : 'Your poster, structured diagram and illustration previews will appear here after generation.'}
              </p>
            </div>
            {generationResult && (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-emerald-800">
                {generationResult.topic}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-2" aria-label="Download and edit controls">
              {[
                { format: 'svg', label: 'Download SVG', Icon: Download },
                { format: 'png', label: 'Download PNG', Icon: Image },
                { format: 'pdf', label: 'Download PDF', Icon: FileText }
              ].map(({ format, label, Icon }) => (
                generationResult ? (
                  <a
                    key={format}
                    href={getExportUrl(generationResult.generation_id, format)}
                    download
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                  >
                    <Icon className="h-4 w-4 text-indigo-700" /> {label}
                  </a>
                ) : (
                  <button
                    key={format}
                    type="button"
                    disabled
                    className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-400"
                  >
                    <Icon className="h-4 w-4" /> {label}
                  </button>
                )
              ))}
              <button
                type="button"
                disabled={!generationResult}
                onClick={() => {
                  setActiveOutputTab('diagram');
                  setEditDiagramRequest((request) => request + 1);
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 disabled:cursor-not-allowed disabled:text-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              >
                <GitBranch className="h-4 w-4 text-indigo-700" /> Edit Diagram
              </button>
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || (activeTab === 'pdf' && !uploadedDoc) || (activeTab === 'text' && !lectureText.trim() && !topic.trim())}
              className="inline-flex items-center gap-2 rounded-lg bg-[#4934C6] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#3826A8] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700"
            >
              <RefreshCw className="h-4 w-4" /> Regenerate
            </button>
          </div>

          <nav className="flex flex-wrap gap-2 border-b border-slate-200 pb-2" role="tablist" aria-label="Generated output">
            {[
              { id: 'poster', label: 'Educational Poster', icon: BookOpen },
              { id: 'diagram', label: 'Diagram Canvas', icon: GitBranch },
              { id: 'illustration', label: 'AI Illustration', icon: Image }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeOutputTab === tab.id}
                  aria-controls={`output-${tab.id}`}
                  disabled={!generationResult}
                  onClick={() => setActiveOutputTab(tab.id)}
                  className={`inline-flex items-center gap-2 rounded-t-xl border-b-[3px] px-4 py-3 text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 ${
                    activeOutputTab === tab.id
                      ? 'border-[#4934C6] bg-indigo-50 text-[#3826A8]'
                      : 'border-transparent bg-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <Icon className="h-4 w-4" /> {tab.label}
                </button>
              );
            })}
          </nav>

          {generationResult ? (
            <div className="space-y-6">
              {activeOutputTab === 'poster' ? (
                <div id="output-poster" role="tabpanel" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                  {generationResult.poster_url && !posterLoadFailed ? (
                    <img
                      src={getAssetUrl(generationResult.poster_url)}
                      alt={`Educational poster for ${generationResult.topic}`}
                      onError={() => setPosterLoadFailed(true)}
                      className="block h-[72vh] min-h-[620px] max-h-[1050px] w-full rounded-2xl bg-slate-50 object-contain"
                    />
                  ) : (
                    <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-600">
                      {posterLoadFailed ? 'The saved poster preview is currently unavailable.' : 'Poster preview was not available.'}
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                    <span>OUTPUT A: Educational poster</span>
                    {generationResult.poster_settings && (
                      <span>{generationResult.poster_settings.theme?.replace(/_/g, ' ')}</span>
                    )}
                  </div>
                </div>
              ) : activeOutputTab === 'diagram' ? (
                <div id="output-diagram" role="tabpanel" className="min-h-[640px]">
                <MermaidViewer
                  code={generationResult.mermaid_code}
                  diagramType={generationResult.diagram_type}
                  title={generationResult.topic}
                  generationId={generationResult.generation_id}
                  editRequest={editDiagramRequest}
                />
                </div>
              ) : (
                <div id="output-illustration" role="tabpanel" className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Palette className="w-5 h-5 text-violet-400" />
                      <h3 className="text-base font-bold text-white">Educational illustration</h3>
                    </div>
                    <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-violet-50 text-violet-700 border border-violet-100">
                      {generationResult.image_is_mock ? 'Development preview' : 'Generated image'}
                    </span>
                  </div>

                  {generationResult.image_url && !imageLoadFailed ? (
                    <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-50 flex items-center justify-center min-h-64 max-h-[560px]">
                      <img
                        src={getAssetUrl(generationResult.image_url)}
                        alt={`Educational illustration for ${generationResult.topic}`}
                        className="w-full h-auto object-contain max-h-[560px]"
                        onError={() => setImageLoadFailed(true)}
                      />
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-10 text-center">
                      <Image className="w-9 h-9 mx-auto mb-3 text-slate-400" />
                      <p className="text-sm font-semibold text-slate-700">
                        {imageLoadFailed
                          ? 'The saved illustration is currently unavailable.'
                          : generationResult.image_error || 'No illustration was generated.'}
                      </p>
                    </div>
                  )}

                  {generationResult.image_is_mock && generationResult.image_url && (
                    <p className="text-xs text-amber-700">
                      Development preview only — this image was not generated by a diffusion provider.
                    </p>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Image provider</p>
                      <p className="text-sm font-semibold text-slate-800">
                        {generationResult.image_provider || 'Not configured'}
                      </p>
                    </div>
                    {generationResult.image_url && (
                      <a
                        href={getAssetUrl(generationResult.image_url)}
                        download={`${generationResult.topic || 'illustration'}.png`}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                      >
                        <Download className="h-4 w-4" /> Download image
                      </a>
                    )}
                  </div>

                  {generationResult.image_error === 'Image generation provider is not configured.' && (
                    <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                      Image generation provider is not configured.
                    </p>
                  )}

                  {generationResult.prompt && (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                        Prompt Synthesized by Agent 3:
                      </span>
                      <p className="text-slate-600 font-mono text-[11px] leading-relaxed">
                        {generationResult.prompt}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <section className="rounded-2xl border border-slate-800 bg-white p-6 shadow-sm">
                <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Educational explanation</h2>
                <p className="mt-2 text-sm leading-7 text-slate-700">{generationResult.summary}</p>
              </section>

              {/* Quality Evaluation Report Card */}
              {generationResult.quality && (
                <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <h3 className="text-base font-bold text-white">Quality Evaluation Report</h3>
                    </div>
                    <span className="text-lg font-black text-emerald-700">
                      {generationResult.quality.overall_score}/100
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {generationResult.quality.criteria.map((crit, idx) => (
                      <div key={idx} className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-slate-300">{crit.name}</span>
                          <span className="font-bold text-indigo-400">{crit.score}/100</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">{crit.notes}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Concepts & Summary Drawer */}
              <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <h3 className="text-base font-bold text-white">{generationResult.topic}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{generationResult.summary}</p>
                  </div>
                  <span className="text-xs font-mono text-indigo-400">
                    {generationResult.execution_time_ms} ms
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Extracted Pedagogical Concepts ({generationResult.concepts?.length || 0})
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {generationResult.concepts?.map((concept) => (
                      <div
                        key={concept.id}
                        className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white">{concept.name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            {concept.importance}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed">{concept.definition}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[420px] flex-col items-center justify-center space-y-4 rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-indigo-100 bg-indigo-50 text-indigo-700">
                <BrainCircuit className="h-8 w-8" />
              </div>
              <div className="max-w-md space-y-2">
                <h3 className="text-lg font-bold text-slate-900">Your next great lesson starts here</h3>
                <p className="text-sm leading-relaxed text-slate-600">
                  Add an educational topic or course PDF above. Your poster, Mermaid diagram and image-provider result will appear in this workspace after the five-agent workflow completes.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default StudioPage;
