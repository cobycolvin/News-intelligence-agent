import { useState } from 'react'
import { analyzeNews } from './api/client'
import { FinalReportPanel } from './components/FinalReportPanel'
import { QueryForm } from './components/QueryForm'
import { RetrievalResults } from './components/RetrievalResults'
import { VisualInsightsPanel } from './components/VisualInsightsPanel'
import type { PipelineResponse } from './types'

function App() {
  const [data, setData] = useState<PipelineResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runQuery = async (query: string, maxArticles: number, reportDepth: 'brief' | 'in_depth') => {
    setLoading(true)
    setError(null)
    try {
      const response = await analyzeNews({ query, max_articles: maxArticles, report_depth: reportDepth })
      setData(response)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6">
      {/* Subtle background radial glow for depth */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(56,189,248,0.06)_0%,_transparent_60%)]" />

      <div className="relative mx-auto max-w-screen-xl space-y-6">

        {/* Header */}
        <div className="border-b border-slate-800 pb-4">
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Multimodal News <span className="text-cyan-400">Intelligence Agent</span>
          </h1>
          <p className="mt-1 text-sm text-slate-400 tracking-wide">
            User Input → Retrieval Agent → Vision Agent → Synthesis Agent → Final Report
          </p>
        </div>

        {/* Query Form */}
        <QueryForm onSubmit={runQuery} loading={loading} />

        {/* Error */}
        {error && (
          <p className="rounded-lg border border-red-800 bg-red-900/30 p-3 text-red-300 text-sm">
            {error}
          </p>
        )}

        {/* Three-column dashboard */}
        {data && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_280px]">

            {/* LEFT — Retrieval Agent */}
            <aside className="flex flex-col gap-4">
              <SectionLabel>Retrieval Agent</SectionLabel>
              <RetrievalResults articles={data.ranked_articles} />
            </aside>

            {/* CENTER — Final Report (main stage) */}
            <section
              className="flex flex-col gap-4 rounded-xl border border-cyan-500/30 bg-slate-900/60 p-4 shadow-[0_0_30px_rgba(56,189,248,0.08)] backdrop-blur-sm"
            >
              <SectionLabel accent>Final Report</SectionLabel>
              <FinalReportPanel report={data.final_report} />
            </section>

            {/* RIGHT — Vision Agent */}
            <aside className="flex flex-col gap-4">
              <SectionLabel>Vision Agent</SectionLabel>
              <VisualInsightsPanel insights={data.visual_insights} articles={data.ranked_articles} />
            </aside>

          </div>
        )}
      </div>
    </main>
  )
}

// Small reusable label for each column header
function SectionLabel({ children, accent }: { children: React.ReactNode; accent?: boolean }) {
  return (
    <p className={`text-xs font-semibold uppercase tracking-widest ${accent ? 'text-cyan-400' : 'text-slate-500'}`}>
      {children}
    </p>
  )
}

export default App