import type { VisualInsight } from '../types'

export function VisualInsightsPanel({ insights }: { insights: VisualInsight[] }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-lg font-semibold">Vision Agent Output</h3>
      <div className="space-y-3">
        {insights.map((insight) => (
          <div key={insight.article_id} className="rounded border border-slate-700 p-3 text-sm">
            <p><span className="font-semibold">Theme:</span> {insight.detected_theme}</p>
            <p><span className="font-semibold">Summary:</span> {insight.image_summary}</p>
            <p><span className="font-semibold">Elements:</span> {insight.notable_visual_elements.join(', ')}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
