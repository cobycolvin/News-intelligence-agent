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
    <form
      className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(query, maxArticles, reportDepth)
      }}
    >
      <h2 className="text-xl font-semibold">News Intelligence Query</h2>
      <textarea className="w-full rounded-md bg-slate-800 p-3" rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-300">Report mode</span>
        <button
          type="button"
          onClick={() => setReportDepth('brief')}
          className={`rounded px-3 py-1 text-sm ${reportDepth === 'brief' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-200'}`}
        >
          Quick Brief
        </button>
        <button
          type="button"
          onClick={() => setReportDepth('in_depth')}
          className={`rounded px-3 py-1 text-sm ${reportDepth === 'in_depth' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-200'}`}
        >
          In-Depth
        </button>
      </div>
      <div className="flex items-center gap-3">
        <label className="text-sm">Articles</label>
        <input type="number" min={1} max={10} className="w-20 rounded bg-slate-800 p-2" value={maxArticles} onChange={(e) => setMaxArticles(Number(e.target.value))} />
        <button disabled={loading} className="rounded bg-cyan-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-60">
          {loading ? 'Analyzing...' : 'Run Pipeline'}
        </button>
      </div>
    </form>
  )
}
