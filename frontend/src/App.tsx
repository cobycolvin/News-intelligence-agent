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
      <div className="mx-auto max-w-6xl space-y-5">
        <h1 className="text-3xl font-bold">Multimodal News Intelligence Agent</h1>
        <p className="text-slate-300">User Input → Retrieval Agent → Vision Agent → Synthesis Agent → Final Report</p>
        <QueryForm onSubmit={runQuery} loading={loading} />
        {error && <p className="rounded bg-red-900/40 p-3 text-red-300">{error}</p>}
        {data && (
          <div className="grid gap-4 lg:grid-cols-2">
            <RetrievalResults articles={data.ranked_articles} />
            <VisualInsightsPanel insights={data.visual_insights} />
            <div className="lg:col-span-2">
              <FinalReportPanel report={data.final_report} />
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

export default App
