import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  Sparkles, 
  ArrowRight,
  Database,
  Layers,
  Palette,
  Award,
  Clock,
  ExternalLink,
  PlusCircle,
  FileCheck2,
  RefreshCw
} from 'lucide-react';
import { getGenerationStats, checkHealth } from '../services/api';

export const DashboardPage = () => {
  const [stats, setStats] = useState({
    total_generations: 0,
    total_illustrations: 0,
    total_documents: 0,
    average_quality_score: 0,
    recent_generations: []
  });
  const [healthInfo, setHealthInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [statsData, healthData] = await Promise.all([
        getGenerationStats().catch(() => ({
          total_generations: 0,
          total_illustrations: 0,
          total_documents: 0,
          average_quality_score: 0,
          recent_generations: []
        })),
        checkHealth().catch(() => null)
      ]);
      setStats(statsData);
      setHealthInfo(healthData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Top Banner & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Course Visuals Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time analytics and generation history from SQLite database.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
            title="Refresh statistics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
          <Link
            to="/studio"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all hover:translate-y-[-1px]"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create New Diagram</span>
          </Link>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Total Generations */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total Generations
            </span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {stats.total_generations}
          </div>
          <p className="text-[11px] text-slate-500">Diagrams generated across all modules</p>
        </div>

        {/* Total Illustrations */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Educational Illustrations
            </span>
            <div className="w-8 h-8 rounded-lg bg-violet-500/10 text-violet-400 flex items-center justify-center">
              <Palette className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {stats.total_illustrations}
          </div>
          <p className="text-[11px] text-slate-500">Generated images and development previews</p>
        </div>

        {/* Average Quality Score */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Average Quality
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">
            {stats.average_quality_score > 0 ? `${stats.average_quality_score}/100` : '—'}
          </div>
          <p className="text-[11px] text-slate-500">Syntax & concept coverage score</p>
        </div>

        {/* Uploaded Documents */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Course PDFs Ingested
            </span>
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {stats.total_documents}
          </div>
          <p className="text-[11px] text-slate-500">Processed page by page via PyMuPDF</p>
        </div>
      </div>

      {/* Recent Generations Table */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Recent Generations</h2>
            <p className="text-xs text-slate-400 mt-0.5">Most recent diagrams and illustrations generated.</p>
          </div>
          <Link
            to="/history"
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <span>View All History</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {stats.recent_generations && stats.recent_generations.length > 0 ? (
          <div className="divide-y divide-slate-800/80">
            {stats.recent_generations.map((item) => (
              <div
                key={item.id}
                className="py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:bg-slate-900/80 rounded-xl px-2 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{item.topic}</span>
                    <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {item.diagram_type}
                    </span>
                    {item.has_illustration && (
                      <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">
                        Illustration
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {item.quality_score && (
                      <span className="text-emerald-400 font-medium">
                        Score: {item.quality_score}/100
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <Link
                    to={`/generations/${item.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
                  >
                    <span>Inspect</span>
                    <ExternalLink className="w-3.5 h-3.5 text-indigo-400" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center space-y-3">
            <Layers className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-sm text-slate-400">No generations yet in database.</p>
            <Link
              to="/studio"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-400 hover:text-indigo-300"
            >
              <span>Create your first diagram now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </div>

      {/* System Health Card */}
      <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Database & Persistence Engine</h3>
            <p className="text-xs text-slate-400">
              SQLite + SQLAlchemy with non-destructive migrations enabled.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-slate-300">
          <div>
            App: <span className="text-indigo-300">{healthInfo?.application || 'CourseIllustrate AI'}</span>
          </div>
          <div>
            API: <span className="text-emerald-400">{healthInfo?.status || 'Active'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
