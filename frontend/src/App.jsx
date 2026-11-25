import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import StudioPage from './pages/StudioPage';
import HistoryPage from './pages/HistoryPage';
import GenerationDetailPage from './pages/GenerationDetailPage';

export function App() {
  return (
    <Router>
      <div className="app-shell min-h-screen bg-slate-950 flex flex-col text-slate-100">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/studio" element={<StudioPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/generations/:id" element={<GenerationDetailPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-center text-xs text-slate-500">
          CourseIllustrate AI &copy; {new Date().getFullYear()} &mdash; Educational Diagram & Illustration Platform
        </footer>
      </div>
    </Router>
  );
}

export default App;
