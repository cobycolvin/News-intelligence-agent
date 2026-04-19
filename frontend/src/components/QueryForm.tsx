import { useState } from 'react'

interface Props {
  onSubmit: (query: string, maxArticles: number, reportDepth: 'brief' | 'in_depth') => Promise<void>
  loading: boolean
}

export function QueryForm({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState('What are the latest developments in Red Sea shipping disruptions?')
  const [maxArticles, setMaxArticles] = useState(5)
  const [reportDepth, setReportDepth] = useState<'brief' | 'in_depth'>('brief')

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/60 backdrop-blur-sm p-5 space-y-4">

      {/* Header */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Intelligence Query
        </p>
        <h2 className="text-lg font-bold text-white">News Intelligence Query</h2>
      </div>

      {/* Textarea */}
      <textarea
        className="w-full rounded-lg border border-slate-700 bg-slate-800/60 p-3 text-sm text-slate-200 placeholder-slate-500 transition-all focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 resize-none"
        rows={3}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {/* Controls row */}
      <div className="flex flex-wrap items-center justify-between gap-3">

        {/* Left: Report mode + Articles */}
        <div className="flex flex-wrap items-center gap-3">

          {/* Report mode toggle */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-400 mr-1">Report mode</span>
            <button
              type="button"
              onClick={() => setReportDepth('brief')}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                reportDepth === 'brief'
                  ? 'bg-cyan-500 text-slate-950 shadow-[0_0_10px_rgba(56,189,248,0.3)]'
                  : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:text-white'
              }`}
            >
              Quick Brief
            </button>
            <button
              type="button"
              onClick={() => setReportDepth('in_depth')}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                reportDepth === 'in_depth'
                  ? 'bg-cyan-500 text-slate-950 shadow-[0_0_10px_rgba(56,189,248,0.3)]'
                  : 'border border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:text-white'
              }`}
            >
              In-Depth
            </button>
          </div>

          {/* Articles count */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">Articles</label>
            <input
              type="number"
              min={1}
              max={10}
              className="w-16 rounded-lg border border-slate-600 bg-slate-800 p-1.5 text-center text-sm text-slate-200 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
              value={maxArticles}
              onChange={(e) => setMaxArticles(Number(e.target.value))}
            />
          </div>
        </div>

        {/* Right: Submit button */}
        <button
          disabled={loading}
          onClick={() => onSubmit(query, maxArticles, reportDepth)}
          className="rounded-lg bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 transition-all hover:bg-cyan-400 hover:shadow-[0_0_16px_rgba(56,189,248,0.4)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Analyzing...
            </span>
          ) : 'Run Pipeline'}
        </button>

      </div>
    </div>
  )
}
