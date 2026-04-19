import type { RankedArticle } from '../types'

// Determine color theme based on relevance score
function getScoreColor(score: number): { ring: string; text: string; bg: string } {
  if (score >= 0.4) return { ring: '#22c55e', text: 'text-green-400', bg: 'bg-green-400/10' }
  if (score >= 0.25) return { ring: '#f59e0b', text: 'text-amber-400', bg: 'bg-amber-400/10' }
  return { ring: '#f87171', text: 'text-red-400', bg: 'bg-red-400/10' }
}

// Small SVG circular progress ring
function ScoreRing({ score }: { score: number }) {
  const { ring, text } = getScoreColor(score)
  const radius = 14
  const circumference = 2 * Math.PI * radius
  const filled = circumference * score
  const gap = circumference - filled

  return (
    <div className="flex flex-col items-center gap-0.5 shrink-0">
      <svg width="36" height="36" viewBox="0 0 36 36">
        {/* Track */}
        <circle
          cx="18" cy="18" r={radius}
          fill="none" stroke="#1e293b" strokeWidth="3"
        />
        {/* Progress */}
        <circle
          cx="18" cy="18" r={radius}
          fill="none"
          stroke={ring}
          strokeWidth="3"
          strokeDasharray={`${filled} ${gap}`}
          strokeLinecap="round"
          transform="rotate(-90 18 18)"
        />
      </svg>
      <span className={`text-[10px] font-semibold ${text}`}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  )
}

export function RetrievalResults({ articles }: { articles: RankedArticle[] }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/60 backdrop-blur-sm p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        Sources
      </h3>
      <div className="space-y-3">
        {articles.map((a) => {
          const { text: scoreText, bg: scoreBg } = getScoreColor(a.relevance_score)
          return (
            <article
              key={a.id}
              className="group rounded-lg border border-slate-700 bg-slate-800/50 p-3 transition-all duration-200 hover:border-cyan-500/50 hover:bg-slate-800 hover:shadow-[0_0_12px_rgba(56,189,248,0.07)] cursor-pointer"
            >
              {/* Title + Score Ring */}
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={a.url}
                    className="font-medium text-cyan-300 text-sm leading-snug hover:text-cyan-200 transition-colors"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {a.title}
                  </a>
                </div>
                <ScoreRing score={a.relevance_score} />
              </div>

              {/* Source + Date pills */}
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
                  {a.source}
                </span>
                <span className="rounded-full bg-slate-700/60 px-2 py-0.5 text-[10px] text-slate-400">
                  {a.date}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${scoreText} ${scoreBg}`}>
                  {a.relevance_score >= 0.4 ? 'High' : a.relevance_score >= 0.25 ? 'Medium' : 'Low'} relevance
                </span>
              </div>

              {/* Snippet */}
              <p className="mt-2 text-xs text-slate-400 leading-relaxed line-clamp-2 group-hover:text-slate-300 transition-colors">
                {a.snippet}
              </p>
            </article>
          )
        })}
      </div>
    </section>
  )
}