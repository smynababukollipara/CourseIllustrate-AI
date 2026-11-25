import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, BarChart3, Image, FileText, Download,
  CheckCircle2, XCircle, Clock, AlertTriangle, RefreshCw,
  ChevronDown, ChevronUp, Cpu, Layers, Lightbulb,
  Sparkles, Eye, Share2, Trash2, Info
} from 'lucide-react';
import { getGeneration, deleteGeneration, getExportUrl, getAssetUrl } from '../services/api';
import MermaidViewer from '../components/studio/MermaidViewer';

const AGENT_LABELS = {
  content_understanding: 'Content Understanding',
  diagram_planning: 'Diagram Planning',
  prompt_engineering: 'Prompt Engineering',
  image_generation: 'Image Generation',
  quality_evaluation: 'Quality Evaluation',
};

const AGENT_ICONS = {
  content_understanding: <Cpu className="w-4 h-4" />,
  diagram_planning: <BarChart3 className="w-4 h-4" />,
  prompt_engineering: <Lightbulb className="w-4 h-4" />,
  image_generation: <Image className="w-4 h-4" />,
  quality_evaluation: <Eye className="w-4 h-4" />,
};

const STATUS_STYLES = {
  completed: 'bg-emerald-900/40 text-emerald-300 border-emerald-700',
  failed: 'bg-red-900/40 text-red-300 border-red-700',
  running: 'bg-amber-900/40 text-amber-300 border-amber-700',
  skipped: 'bg-slate-800 text-slate-400 border-slate-700',
  pending: 'bg-slate-800 text-slate-500 border-slate-700',
};

const STATUS_ICON = {
  completed: <CheckCircle2 className="w-3.5 h-3.5" />,
  failed: <XCircle className="w-3.5 h-3.5" />,
  running: <Clock className="w-3.5 h-3.5 animate-spin" />,
  skipped: <ChevronDown className="w-3.5 h-3.5" />,
  pending: <Clock className="w-3.5 h-3.5" />,
};

function AgentStatusCard({ agentKey, status }) {
  const [open, setOpen] = useState(false);
  const statusValue = typeof status === 'string' ? status : status?.status;
  const logs = typeof status === 'object' && status !== null ? status.logs : [];
  const style = STATUS_STYLES[statusValue] || STATUS_STYLES.pending;
  return (
    <div className={`border rounded-lg overflow-hidden ${style}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:opacity-80 transition-opacity"
      >
        <div className="flex items-center gap-2 font-medium text-sm">
          {AGENT_ICONS[agentKey]}
          {AGENT_LABELS[agentKey] || agentKey}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {STATUS_ICON[statusValue] || STATUS_ICON.pending}
          <span className="capitalize">{statusValue || 'pending'}</span>
          {logs?.length > 0 && (open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
        </div>
      </button>
      {open && logs?.length > 0 && (
        <div className="border-t border-current/20 px-4 py-2 text-xs font-mono space-y-1 opacity-80">
          {logs.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
    </div>
  );
}

function QualityReport({ report }) {
  if (!report) return null;
  const pct = Math.round(report.overall_score ?? 0);
  const color = pct >= 75 ? 'text-emerald-700' : pct >= 50 ? 'text-amber-700' : 'text-red-700';
  const bar = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Eye className="w-4 h-4 text-violet-400" /> Quality Evaluation
      </h3>
      <div className="flex items-center gap-4 mb-4">
        <span className={`text-4xl font-black font-mono ${color}`}>{pct}%</span>
        <div className="flex-1">
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className={`h-2 rounded-full ${bar} transition-all`} style={{ width: `${pct}%` }} />
          </div>
          <p className="text-xs text-slate-400 mt-1">Overall quality score</p>
        </div>
      </div>
      {report.criteria?.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
          {report.criteria.map((criterion) => (
            <div key={criterion.name} className="bg-slate-800/60 rounded-lg px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-slate-700">{criterion.name}</span>
                <span className="text-xs font-bold text-indigo-700">{Math.round(criterion.score)}/100</span>
              </div>
              {criterion.notes && <p className="mt-1 text-[11px] text-slate-500">{criterion.notes}</p>}
            </div>
          ))}
        </div>
      )}
      {report.problems?.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-slate-500 mb-1 font-medium">Issues:</p>
          <ul className="space-y-1">
            {report.problems.map((issue, i) => (
              <li key={i} className="text-xs text-amber-300 flex items-start gap-1.5">
                <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />{issue}
              </li>
            ))}
          </ul>
        </div>
      )}
      {report.suggestions?.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-slate-500 mb-1 font-medium">Suggestions:</p>
          <ul className="space-y-1">
            {report.suggestions.map((s, i) => (
              <li key={i} className="text-xs text-sky-300 flex items-start gap-1.5">
                <Lightbulb className="w-3 h-3 mt-0.5 shrink-0" />{s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function GenerationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [conceptsOpen, setConceptsOpen] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await getGeneration(id);
      setData(detail);
      setImageLoadFailed(false);
    } catch (e) {
      setError(e.message || 'Failed to load generation');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const handleDelete = async () => {
    if (!window.confirm('Delete this generation? This cannot be undone.')) return;
    setDeleting(true);
    try {
      await deleteGeneration(id);
      navigate('/history');
    } catch (e) {
      alert('Failed to delete: ' + (e.message || 'Unknown error'));
      setDeleting(false);
    }
  };

  const formatDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric',
      year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" />
        <p>Loading generation…</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center max-w-md">
        <XCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-red-300 font-medium mb-2">{error}</p>
        <div className="flex gap-2 justify-center mt-4">
          <button onClick={fetchDetail} className="px-4 py-2 bg-slate-800 rounded-lg text-sm hover:bg-slate-700">
            Retry
          </button>
          <Link to="/history" className="px-4 py-2 bg-violet-700 hover:bg-violet-600 rounded-lg text-sm">
            Back to History
          </Link>
        </div>
      </div>
    </div>
  );

  const g = data;
  const qualityPct = g?.quality_score != null ? Math.round(g.quality_score) : null;
  const agentStatusMap = g?.agent_status || {};
  const agentKeys = ['content_understanding', 'diagram_planning', 'quality_evaluation', 'prompt_engineering', 'image_generation'];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
          <Link to="/history" className="hover:text-violet-400 flex items-center gap-1 transition-colors">
            <ArrowLeft className="w-4 h-4" /> History
          </Link>
          <span>/</span>
          <span className="text-slate-300 truncate max-w-xs">{g?.topic || id}</span>
        </div>

        {/* Top header */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-100">{g?.topic || 'Generation Detail'}</h1>
            {g?.summary && (
            <p className="text-slate-600 mt-2 max-w-3xl leading-relaxed">{g.summary}</p>
            )}
            <div className="flex flex-wrap items-center gap-3 mt-3 text-xs">
              {g?.diagram_type && (
                <span className="px-2 py-1 bg-slate-800 rounded text-slate-300 capitalize">
                  {g.diagram_type.replace(/_/g, ' ')}
                </span>
              )}
              {g?.illustration_style && (
                <span className="px-2 py-1 bg-slate-800 rounded text-slate-300 capitalize">
                  {g.illustration_style.replace(/_/g, ' ')}
                </span>
              )}
              {qualityPct != null && (
                <span className={`px-2 py-1 rounded font-mono font-semibold ${qualityPct >= 75 ? 'bg-emerald-900/50 text-emerald-300' : qualityPct >= 50 ? 'bg-amber-900/50 text-amber-300' : 'bg-red-900/50 text-red-300'}`}>
                  Quality: {qualityPct}%
                </span>
              )}
              <span className="text-slate-500">{formatDate(g?.created_at)}</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {g?.id && (
              <>
                <a
                  href={getExportUrl(g.id, 'svg')}
                  download={`${g.topic || 'diagram'}.svg`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> SVG
                </a>
                <a
                  href={getExportUrl(g.id, 'png')}
                  download={`${g.topic || 'diagram'}.png`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> PNG
                </a>
                <a
                  href={getExportUrl(g.id, 'pdf')}
                  download={`${g.topic || 'diagram'}.pdf`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </a>
                <Link
                  to="/studio"
                  className="flex items-center gap-1.5 px-3 py-2 bg-violet-700 hover:bg-violet-600 rounded-lg text-xs transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" /> New in Studio
                </Link>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-1.5 px-3 py-2 bg-red-900/50 hover:bg-red-900 border border-red-700 rounded-lg text-xs text-red-300 transition-colors disabled:opacity-40"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </button>
              </>
            )}
          </div>
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* Left — Diagram + Illustration */}
          <div className="xl:col-span-2 space-y-6">

            {g?.poster_url && (
              <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                  <h2 className="flex items-center gap-2 font-semibold text-slate-200">
                    <Sparkles className="h-4 w-4 text-violet-400" /> OUTPUT A: Educational Poster
                  </h2>
                  <span className="text-xs text-slate-500">Custom SVG infographic</span>
                </div>
                <object
                  data={getAssetUrl(g.poster_url)}
                  type="image/svg+xml"
                  title={`Educational poster for ${g.topic}`}
                  className="block h-[620px] w-full bg-slate-50"
                />
              </div>
            )}

            {/* Mermaid Diagram */}
            {g?.diagram_code ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-violet-400" /> Diagram
                  </h2>
                  <span className="text-xs text-slate-500 font-mono">Mermaid.js</span>
                </div>
                <MermaidViewer code={g.diagram_code} diagramType={g.diagram_type} title={g.topic} />
              </div>
            ) : (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center text-slate-500">
                <BarChart3 className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No diagram available for this generation.</p>
              </div>
            )}

            {/* Illustration */}
            {g?.image_url && !imageLoadFailed ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                    <Image className="w-4 h-4 text-sky-400" /> Illustration
                  </h2>
                  {g?.image_provider && (
                    <span className="text-xs text-slate-500 capitalize">{g.image_provider}</span>
                  )}
                </div>
                <div className="p-4 bg-slate-950 flex items-center justify-center min-h-48">
                  <img
                    src={getAssetUrl(g.image_url)}
                    alt={`Illustration for ${g.topic}`}
                    className="max-w-full max-h-96 rounded-lg object-contain"
                    onError={() => setImageLoadFailed(true)}
                  />
                </div>
                {g?.image_is_mock && (
                  <div className="px-4 py-2 bg-amber-950/40 border-t border-amber-800 flex items-center gap-2">
                    <Info className="w-4 h-4 text-amber-400 shrink-0" />
                    <span className="text-xs text-amber-300">
                      Development preview only — this image was not generated by a diffusion provider.
                    </span>
                  </div>
                )}
                {g?.prompt_text && (
                  <div className="px-4 py-3 border-t border-slate-800">
                    <p className="text-xs text-slate-500 font-medium mb-1">Image Prompt</p>
                    <p className="text-xs text-slate-400 leading-relaxed">{g.prompt_text}</p>
                  </div>
                )}
                <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-slate-800 text-xs">
                  <span className="text-slate-500">Provider: <strong className="text-slate-700">{g.image_provider || 'Not configured'}</strong></span>
                  <a href={getAssetUrl(g.image_url)} download className="inline-flex items-center gap-1 font-semibold text-indigo-700">
                    <Download className="h-3.5 w-3.5" /> Download image
                  </a>
                </div>
              </div>
            ) : g?.generate_illustration === true ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
                <Image className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">
                  {imageLoadFailed
                    ? 'The saved illustration is currently unavailable.'
                    : g.image_error || 'Illustration was not generated.'}
                </p>
              </div>
            ) : null}
          </div>

          {/* Right sidebar */}
          <div className="space-y-5">

            {/* Quality report */}
            {g?.quality && <QualityReport report={g.quality} />}

            {/* Agent pipeline status */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-violet-400" /> Agent Pipeline
              </h3>
              <div className="space-y-2">
                {agentKeys.map(key => (
                  <AgentStatusCard
                    key={key}
                    agentKey={key}
                    status={agentStatusMap[key] || { status: 'pending', logs: [] }}
                  />
                ))}
              </div>
              {g?.retry_count > 0 && (
                <div className="mt-3 text-xs text-amber-400 flex items-center gap-1.5">
                  <RefreshCw className="w-3 h-3" /> Quality retries: {g.retry_count}
                </div>
              )}
            </div>

            {/* Concepts */}
            {g?.concepts?.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <button
                  onClick={() => setConceptsOpen(o => !o)}
                  className="w-full flex items-center justify-between font-semibold text-slate-200 mb-1"
                >
                  <span className="flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-400" /> Concepts ({g.concepts.length})
                  </span>
                  {conceptsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {conceptsOpen && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {g.concepts.map((c, i) => (
                      <div key={c.id || i} className="w-full rounded-lg bg-slate-50 p-3">
                        <strong className="text-xs text-slate-700">{c.name || c}</strong>
                        {c.definition && <p className="mt-1 text-xs leading-relaxed text-slate-500">{c.definition}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Execution logs */}
            {g?.execution_logs?.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <button
                  onClick={() => setLogsOpen(o => !o)}
                  className="w-full flex items-center justify-between font-semibold text-slate-200"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400" /> Logs ({g.execution_logs.length})
                  </span>
                  {logsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {logsOpen && (
                  <div className="mt-3 space-y-1 max-h-48 overflow-y-auto">
                    {g.execution_logs.map((log, i) => (
                      <div key={i} className="text-xs font-mono text-slate-400 leading-snug">
                        {typeof log === 'string' ? log : log.action || log.agent || JSON.stringify(log)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Raw metadata */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-xs text-slate-500 space-y-1 font-mono">
              <div><span className="text-slate-600">ID: </span>{g?.id}</div>
              <div><span className="text-slate-600">Status: </span>{g?.status}</div>
              <div><span className="text-slate-600">Image provider: </span>{g?.image_provider || 'none'}</div>
              {g?.source_pdf && <div><span className="text-slate-600">PDF: </span>{g.source_pdf}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
