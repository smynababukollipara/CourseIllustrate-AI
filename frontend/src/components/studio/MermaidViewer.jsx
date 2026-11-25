import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Code, 
  Eye, 
  Copy, 
  Check, 
  AlertTriangle,
  Download,
  Maximize2,
  Minimize2,
  Play,
  FileDown
} from 'lucide-react';

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif',
  themeVariables: {
    darkMode: false,
    background: '#ffffff',
    primaryColor: '#eef0ff',
    primaryTextColor: '#27324a',
    primaryBorderColor: '#6d63df',
    lineColor: '#7269d2',
    secondaryColor: '#f1efff',
    tertiaryColor: '#f8fafc',
  }
});

export const MermaidViewer = ({ 
  code: initialCode, 
  diagramType, 
  title, 
  generationId, 
  onCodeChange,
  editRequest = 0,
}) => {
  const containerRef = useRef(null);
  const [editableCode, setEditableCode] = useState(initialCode || '');
  const [renderedCode, setRenderedCode] = useState(initialCode || '');
  const [svgContent, setSvgContent] = useState('');
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState('visual'); // 'visual' | 'code'
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    setEditableCode(initialCode || '');
    setRenderedCode(initialCode || '');
  }, [initialCode]);

  useEffect(() => {
    if (editRequest > 0) setViewMode('code');
  }, [editRequest]);

  const handleFitToScreen = () => {
    const wrapper = containerRef.current;
    const svg = wrapper?.querySelector('svg');
    const canvas = wrapper?.parentElement;
    if (!svg || !canvas) {
      setZoom(1);
      return;
    }
    const viewBox = svg.viewBox?.baseVal;
    const width = viewBox?.width || Number.parseFloat(svg.getAttribute('width')) || svg.getBoundingClientRect().width;
    const height = viewBox?.height || Number.parseFloat(svg.getAttribute('height')) || svg.getBoundingClientRect().height;
    if (!width || !height) {
      setZoom(1);
      return;
    }
    setZoom(Math.min(1, (canvas.clientWidth - 48) / width, (canvas.clientHeight - 48) / height));
  };

  useEffect(() => {
    let isMounted = true;
    if (!renderedCode) {
      setSvgContent('');
      return;
    }

    const renderDiagram = async () => {
      try {
        setError(null);
        const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(uniqueId, renderedCode);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err) {
        console.error('Mermaid render error:', err);
        if (isMounted) {
          setError(err.message || 'Failed to render Mermaid diagram syntax.');
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [renderedCode]);

  const handleCopy = () => {
    navigator.clipboard.writeText(editableCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApplyCode = () => {
    setRenderedCode(editableCode);
    if (onCodeChange) onCodeChange(editableCode);
  };

  // Export current rendered SVG directly to client
  const handleDownloadSvg = () => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'diagram').replace(/\s+/g, '_')}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Export raster PNG from the rendered SVG
  const handleDownloadPng = () => {
    if (!svgContent) return;
    const svgBlob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const URLObject = window.URL || window.webkitURL || window;
    const blobURL = URLObject.createObjectURL(svgBlob);
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = image.width || 1200;
      canvas.height = image.height || 800;
      const context = canvas.getContext('2d');
      context.fillStyle = '#ffffff';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0);
      const png = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.download = `${(title || 'diagram').replace(/\s+/g, '_')}.png`;
      a.href = png;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URLObject.revokeObjectURL(blobURL);
    };
    image.src = blobURL;
  };

  return (
    <div className={`flex flex-col rounded-2xl bg-slate-900/70 border border-slate-800 overflow-hidden transition-all ${
      isFullscreen ? 'fixed inset-4 z-50 shadow-2xl shadow-black/80' : 'h-full'
    }`}>
      {/* Viewer Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-slate-800/80 bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            {diagramType || 'diagram'}
          </span>
          <span className="text-sm font-bold text-slate-200 truncate max-w-[200px] sm:max-w-xs md:max-w-md">
            {title || 'Generated Educational Diagram'}
          </span>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {/* Mode Switcher */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-800/90 border border-slate-700/60 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('visual')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-semibold transition-colors ${
                viewMode === 'visual'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Canvas</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('code')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-semibold transition-colors ${
                viewMode === 'code'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              <span>Edit Mermaid</span>
            </button>
          </div>

          {/* Quick Copy */}
          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors"
            title="Copy Mermaid Code"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>

          {/* Direct Downloads */}
          <button
            type="button"
            onClick={handleDownloadSvg}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors flex items-center gap-1 text-xs px-2"
            title="Download SVG"
          >
            <Download className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">SVG</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadPng}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors flex items-center gap-1 text-xs px-2"
            title="Download PNG"
          >
            <FileDown className="w-3.5 h-3.5 text-violet-400" />
            <span className="hidden sm:inline">PNG</span>
          </button>

          {/* Zoom Controls */}
          {viewMode === 'visual' && (
            <div className="hidden sm:flex items-center gap-1 pl-2 border-l border-slate-800">
              <button
                type="button"
                onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleFitToScreen}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                title="Fit to Screen"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Preview"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4 text-amber-400" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className={`flex-1 min-h-[460px] p-6 flex items-center justify-center overflow-auto bg-slate-950/70 relative ${
        isFullscreen ? 'h-[calc(100%-60px)]' : ''
      }`}>
        {viewMode === 'visual' ? (
          error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm max-w-md flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Mermaid Syntax Warning</p>
                <p className="text-xs text-rose-400/80 mt-1">{error}</p>
                <button
                  onClick={() => setViewMode('code')}
                  className="mt-3 px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold"
                >
                  Edit Code in Editor
                </button>
              </div>
            </div>
          ) : svgContent ? (
            <div
              ref={containerRef}
              style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
              className="transition-transform duration-150 ease-out max-w-full flex justify-center items-center select-none"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <div className="text-slate-500 text-sm animate-pulse">Rendering diagram...</div>
          )
        ) : (
          <div className="w-full h-full flex flex-col space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span>Edit Mermaid source code below and click <strong className="text-indigo-400">Re-render Diagram</strong></span>
              <button
                type="button"
                onClick={handleApplyCode}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all shadow-md shadow-indigo-600/30"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Re-render Diagram</span>
              </button>
            </div>
            <textarea
              value={editableCode}
              onChange={(e) => setEditableCode(e.target.value)}
              rows={16}
              className="w-full flex-1 p-4 rounded-xl bg-slate-950 border border-slate-800 text-indigo-300 font-mono text-xs focus:border-indigo-500 focus:outline-none leading-relaxed resize-none"
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default MermaidViewer;
