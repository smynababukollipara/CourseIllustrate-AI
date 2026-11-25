import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen, Search, Filter, Trash2, ExternalLink,
  ChevronDown, ChevronUp, RefreshCw, BarChart3,
  Image, FileText, Clock, CheckCircle2, XCircle,
  AlertTriangle, Eye, Download
} from 'lucide-react';
import { listGenerations, deleteGeneration, getExportUrl, getAssetUrl } from '../services/api';

const DIAGRAM_TYPE_LABELS = {
  flowchart: 'Flowchart',
  mindmap: 'Mind Map',
  concept_map: 'Concept Map',
  architecture: 'Architecture',
  process: 'Process',
  hierarchical: 'Hierarchical',
  comparison: 'Comparison',
};

const STATUS_ICON = {
  completed: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
  processing: <Clock className="w-4 h-4 text-amber-400 animate-spin" />,
};

function QualityBadge({ score }) {
  if (score == null) return <span className="text-slate-500 text-xs">—</span>;
  const pct = Math.round(score);
  const color = pct >= 75 ? 'text-emerald-700' : pct >= 50 ? 'text-amber-700' : 'text-red-700';
  return <span className={`font-mono text-xs font-semibold ${color}`}>{pct}%</span>;
}

export default function HistoryPage() {
  const [generations, setGenerations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [sortField, setSortField] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [deleting, setDeleting] = useState(null);
  const [page, setPage] = useState(1);
  const PER_PAGE = 15;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 200, offset: 0 };
      if (search.trim()) params.search = search.trim();
      if (filterType) params.diagram_type = filterType;
      const data = await listGenerations(params);
      setGenerations(data || []);
    } catch (e) {
      setError(e.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, [search, filterType]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const handleDelete = async (id, topic) => {
    if (!window.confirm(`Delete generation "${topic}"? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await deleteGeneration(id);
      setGenerations(prev => prev.filter(g => g.id !== id));
    } catch (e) {
      alert('Failed to delete: ' + (e.message || 'Unknown error'));
    } finally {
      setDeleting(null);
    }
  };

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const sorted = [...generations].sort((a, b) => {
    let av = a[sortField], bv = b[sortField];
    if (sortField === 'quality_score') { av = av ?? -1; bv = bv ?? -1; }
    if (sortField === 'created_at') { av = new Date(av); bv = new Date(bv); }
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const pageCount = Math.ceil(sorted.length / PER_PAGE);
  const paginated = sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ChevronDown className="w-3 h-3 opacity-30" />;
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3 text-violet-400" /> : <ChevronDown className="w-3 h-3 text-violet-400" />;
  };

  const formatDate = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) +
      ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-10 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-violet-400" />
              Generation History
            </h1>
            <p className="text-slate-400 mt-1">Browse, search, and manage all your generated diagrams and illustrations.</p>
          </div>
          <button
            onClick={fetchHistory}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="relative flex-1 min-w-56">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by topic or description…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-violet-500"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={filterType}
              onChange={e => { setFilterType(e.target.value); setPage(1); }}
              className="pl-9 pr-8 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm focus:outline-none focus:border-violet-500 appearance-none"
            >
              <option value="">All types</option>
              {Object.entries(DIAGRAM_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="text-xs text-slate-500 flex items-center px-3">
            {generations.length} record{generations.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 p-4 bg-red-950/50 border border-red-800 rounded-lg mb-6">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center justify-end gap-2 text-xs">
          <span className="text-slate-500">Sort by</span>
          {[
            { field: 'created_at', label: 'Date' },
            { field: 'topic', label: 'Topic' },
            { field: 'quality_score', label: 'Quality' },
          ].map(({ field, label }) => (
            <button
              key={field}
              type="button"
              onClick={() => toggleSort(field)}
              className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 ${
                sortField === field
                  ? 'border-indigo-200 bg-indigo-50 text-indigo-700'
                  : 'border-slate-200 bg-white text-slate-600'
              }`}
            >
              {label} <SortIcon field={field} />
            </button>
          ))}
        </div>

        {/* Visual gallery */}
        {loading ? (
          <div className="rounded-2xl border border-slate-800 bg-white py-16 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading history…
          </div>
        ) : paginated.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-white py-16 text-center text-slate-500">
            <BarChart3 className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p>No generations found.</p>
            {(search || filterType) && (
              <button
                onClick={() => { setSearch(''); setFilterType(''); }}
                className="mt-2 text-violet-400 hover:underline text-xs"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
            {paginated.map((g) => (
              <article key={g.id} className="overflow-hidden rounded-2xl border border-slate-800 bg-white shadow-sm">
                <Link to={`/generations/${g.id}`} className="group block">
                  <div className="relative aspect-[16/10] bg-slate-100">
                    {g.thumbnail_url ? (
                      <img
                        src={getAssetUrl(g.thumbnail_url)}
                        alt={`Preview of ${g.topic}`}
                        className="h-full w-full object-cover"
                        onError={(event) => event.currentTarget.remove()}
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center">
                        <BarChart3 className="h-10 w-10 text-indigo-300" />
                      </div>
                    )}
                    <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm">
                      {DIAGRAM_TYPE_LABELS[g.diagram_type] || g.diagram_type || 'Diagram'}
                    </span>
                  </div>
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <h2 className="line-clamp-2 text-base font-bold text-slate-800 group-hover:text-indigo-700">
                        {g.topic || 'Untitled generation'}
                      </h2>
                      <span className="shrink-0">{STATUS_ICON[g.status] || <Clock className="w-4 h-4 text-slate-500" />}</span>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                      <span>{formatDate(g.created_at)}</span>
                      <span className="font-semibold">Quality <QualityBadge score={g.quality_score} /></span>
                    </div>
                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                      <span className="flex items-center gap-2 text-xs text-slate-500">
                        {g.image_url && <span className="inline-flex items-center gap-1"><Image className="h-3.5 w-3.5" /> Illustration</span>}
                        {g.document_id && <span className="inline-flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> PDF source</span>}
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700">
                        View result <ExternalLink className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </div>
                </Link>
                <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-3">
                  <a
                    href={getExportUrl(g.id, 'svg')}
                    download
                    className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                    title="Download SVG"
                  >
                    <Download className="h-3.5 w-3.5" /> SVG
                  </a>
                  <button
                    onClick={() => handleDelete(g.id, g.topic)}
                    disabled={deleting === g.id}
                    className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-40"
                    title="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}

          {/* Pagination */}
          {pageCount > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800 text-xs text-slate-400">
              <span>Page {page} of {pageCount} ({sorted.length} total)</span>
              <div className="flex gap-1">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 rounded bg-slate-800 disabled:opacity-30 hover:bg-slate-700"
                >
                  Prev
                </button>
                <button
                  disabled={page === pageCount}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 rounded bg-slate-800 disabled:opacity-30 hover:bg-slate-700"
                >
                  Next
                </button>
              </div>
            </div>
          )}
      </div>
    </div>
  );
}
