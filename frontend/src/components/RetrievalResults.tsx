import type { RankedArticle } from '../types'

export function RetrievalResults({ articles }: { articles: RankedArticle[] }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-lg font-semibold">Retrieval Agent Output</h3>
      <div className="space-y-3">
        {articles.map((a) => (
          <article key={a.id} className="rounded border border-slate-700 p-3">
            <a href={a.url} className="font-medium text-cyan-300" target="_blank" rel="noreferrer">{a.title}</a>
            <p className="text-sm text-slate-400">{a.source} · {a.date} · score {a.relevance_score}</p>
            <p className="text-sm mt-1">{a.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
