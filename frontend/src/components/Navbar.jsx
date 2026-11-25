import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Sparkles, 
  Home,
  LayoutDashboard, 
  Wand2, 
  History,
  Activity, 
  CheckCircle2, 
  AlertCircle,
  Layers
} from 'lucide-react';
import { checkHealth } from '../services/api';

export const Navbar = () => {
  const location = useLocation();
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'healthy' | 'error'

  useEffect(() => {
    let mounted = true;
    const verifyHealth = async () => {
      try {
        const data = await checkHealth();
        if (mounted && data.status === 'healthy') {
          setBackendStatus('healthy');
        }
      } catch (err) {
        if (mounted) setBackendStatus('error');
      }
    };
    verifyHealth();
    const interval = setInterval(verifyHealth, 20000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isActive = (path) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <Link to="/" className="group flex min-w-max items-center gap-2 whitespace-nowrap sm:gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-lg shadow-indigo-500/20 transition-transform group-hover:scale-105 sm:h-10 sm:w-10">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-base font-extrabold text-slate-800 sm:text-lg">
                CourseIllustrate<span className="text-indigo-400"> AI</span>
              </span>
              <span className="hidden xl:inline-block ml-2 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                5-Agent LangGraph
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-0 sm:gap-1.5">
            <Link
              to="/"
              title="Overview"
              aria-label="Overview"
              className={`flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 text-xs font-semibold transition-colors sm:px-2.5 ${
                isActive('/') && location.pathname === '/'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Home className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden lg:inline">Overview</span>
            </Link>

            <Link
              to="/dashboard"
              title="Dashboard"
              aria-label="Dashboard"
              className={`flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 text-xs font-semibold transition-colors sm:px-2.5 ${
                isActive('/dashboard') 
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden lg:inline">Dashboard</span>
            </Link>

            <Link
              to="/studio"
              title="Studio"
              aria-label="Studio"
              className={`flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 text-xs font-semibold transition-colors sm:px-2.5 ${
                isActive('/studio') 
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Wand2 className="w-3.5 h-3.5 text-violet-400" />
              <span className="hidden lg:inline">Studio</span>
            </Link>

            <Link
              to="/history"
              title="History"
              aria-label="History"
              className={`flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 text-xs font-semibold transition-colors sm:px-2.5 ${
                isActive('/history') 
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <History className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden lg:inline">History</span>
            </Link>
          </div>

          {/* Backend Status Indicator */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-slate-400">Backend:</span>
              {backendStatus === 'healthy' && (
                <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Online
                </span>
              )}
              {backendStatus === 'error' && (
                <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                  <AlertCircle className="w-3.5 h-3.5" /> Disconnected
                </span>
              )}
              {backendStatus === 'checking' && (
                <span className="text-amber-400 animate-pulse font-semibold">
                  Connecting...
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
