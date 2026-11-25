import React from 'react';
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  Circle,
  GitBranch,
  Image,
  Loader2,
  Palette,
  ShieldCheck,
  SkipForward,
  Sparkles,
} from 'lucide-react';

const AGENTS = [
  {
    key: 'content_understanding',
    name: 'Content Understanding',
    description: 'Finds the topic, concepts and learning goals.',
    icon: BrainCircuit,
  },
  {
    key: 'diagram_planning',
    name: 'Diagram Planning',
    description: 'Maps concepts into a clear visual structure.',
    icon: GitBranch,
  },
  {
    key: 'prompt_engineering',
    name: 'Prompt Engineering',
    description: 'Prepares the illustration prompt and style.',
    icon: Sparkles,
  },
  {
    key: 'image_generation',
    name: 'Image Generation',
    description: 'Creates the image or reports provider status.',
    icon: Image,
  },
  {
    key: 'quality_evaluation',
    name: 'Quality Evaluation',
    description: 'Checks coverage, relationships and quality.',
    icon: ShieldCheck,
  },
];

const STATUS_PRESENTATION = {
  pending: {
    label: 'Pending',
    className: 'border-slate-200 bg-slate-50 text-slate-600',
    icon: Circle,
  },
  running: {
    label: 'Running',
    className: 'border-indigo-200 bg-indigo-50 text-indigo-800',
    icon: Loader2,
  },
  completed: {
    label: 'Completed',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    icon: CheckCircle2,
  },
  failed: {
    label: 'Failed',
    className: 'border-rose-200 bg-rose-50 text-rose-800',
    icon: AlertCircle,
  },
  skipped: {
    label: 'Skipped',
    className: 'border-amber-200 bg-amber-50 text-amber-800',
    icon: SkipForward,
  },
};

const getAgentLog = (logs, agentKey) => {
  const phrase = agentKey.replaceAll('_', ' ').toLowerCase();
  return [...(logs || [])].reverse().find((log) => {
    const agent = typeof log.agent === 'string' ? log.agent.toLowerCase() : '';
    return agent.includes(phrase);
  });
};

export const AgentMonitor = ({
  agentStatus = {},
  executionLogs = [],
  retryCount = 0,
  isGenerating = false,
}) => (
  <div className="agent-monitor rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">02 · AI workflow</p>
        <h2 className="mt-1 text-xl font-bold text-slate-900">Five-agent execution</h2>
        <p className="mt-1 text-sm text-slate-600">
          Status and run details are taken from the backend execution report.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {isGenerating && (
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-800">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Waiting for workflow report
          </span>
        )}
        {retryCount > 0 && (
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
            <Palette className="h-3.5 w-3.5" /> Quality repairs: {retryCount}
          </span>
        )}
      </div>
    </div>

    <ol className="agent-timeline">
      {AGENTS.map((agent, index) => {
        const statusKey = agentStatus[agent.key] || 'pending';
        const presentation = STATUS_PRESENTATION[statusKey] || STATUS_PRESENTATION.pending;
        const Icon = agent.icon;
        const StatusIcon = presentation.icon;
        const log = getAgentLog(executionLogs, agent.key);

        return (
          <li className="agent-timeline-step" key={agent.key}>
            <div className="agent-step-marker" aria-hidden="true">
              <span>{String(index + 1).padStart(2, '0')}</span>
            </div>
            <article className="agent-step-card">
              <div className="flex min-w-0 items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
                  <Icon className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Agent {index + 1}
                  </p>
                  <h3 className="mt-0.5 break-words text-sm font-bold leading-snug text-slate-900">
                    {agent.name}
                  </h3>
                </div>
              </div>
              <p className="mt-3 min-h-[40px] text-xs leading-5 text-slate-600">
                {agent.description}
              </p>
              <span className={`mt-3 inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide ${presentation.className}`}>
                <StatusIcon className={`h-3 w-3 ${statusKey === 'running' ? 'animate-spin' : ''}`} />
                {presentation.label}
              </span>
              {log ? (
                <details className="mt-3 border-t border-slate-100 pt-2">
                  <summary className="cursor-pointer text-xs font-semibold text-indigo-700">
                    Execution details
                  </summary>
                  <div className="mt-2 space-y-1 break-words text-[11px] leading-4 text-slate-600">
                    {log.action && <p>{log.action}</p>}
                    <p>
                      {[log.provider, log.duration_ms != null ? `${log.duration_ms} ms` : null]
                        .filter(Boolean)
                        .join(' · ') || 'Backend execution recorded'}
                    </p>
                  </div>
                </details>
              ) : (
                <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] leading-4 text-slate-500">
                  {statusKey === 'pending' && isGenerating
                    ? 'Execution result has not been reported yet.'
                    : 'No execution details reported.'}
                </p>
              )}
            </article>
          </li>
        );
      })}
    </ol>
  </div>
);

export default AgentMonitor;
