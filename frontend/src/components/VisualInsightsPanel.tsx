import type { RankedArticle, VisualInsight } from '../types'

function getConfidenceColor(score: number): { ring: string; text: string } {
  if (score >= 0.7) return { ring: '#22c55e', text: 'text-green-400' }
  if (score >= 0.4) return { ring: '#f59e0b', text: 'text-amber-400' }
  return { ring: '#f87171', text: 'text-red-400' }
}

function ConfidenceRing({ score }: { score: number }) {
  const { ring, text } = getConfidenceColor(score)
  const radius = 12
  const circumference = 2 * Math.PI * radius
  const filled = circumference * score

  return (
    <div className="flex flex-col items-center gap-0.5 shrink-0">
      <svg width="30" height="30" viewBox="0 0 30 30">
        <circle cx="15" cy="15" r={radius} fill="none" stroke="#1e293b" strokeWidth="3" />
        <circle
          cx="15" cy="15" r={radius}
          fill="none"
          stroke={ring}
          strokeWidth="3"
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeLinecap="round"
          transform="rotate(-90 15 15)"
        />
      </svg>
      <span className={`text-[10px] font-semibold ${text}`}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  )
}

interface Props {
  insights: VisualInsight[]
  articles: RankedArticle[]
}

export function VisualInsightsPanel({ insights, articles }: Props) {
  // Build a quick lookup map so we don't search the array repeatedly
  const articleMap = Object.fromEntries(articles.map(a => [a.id, a]))

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/60 backdrop-blur-sm p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        Visual Analysis
      </h3>
      <div className="space-y-3">
        {insights.map((insight) => {
          const article = articleMap[insight.article_id]
          const { text: confText } = getConfidenceColor(insight.confidence_score)

          return (
            <div
              key={insight.article_id}
              className="group rounded-lg border border-slate-700 bg-slate-800/50 p-3 transition-all duration-200 hover:border-cyan-500/50 hover:bg-slate-800 hover:shadow-[0_0_12px_rgba(56,189,248,0.07)]"
            >
              {/* Linked article title + confidence ring */}
              <div className="flex items-start gap-2 mb-2">
                <div className="flex-1 min-w-0">
                  {article ? (
                    
                     <a href={article.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] font-medium text-cyan-300 hover:text-cyan-200 transition-colors leading-snug line-clamp-2"
                    >
                      {article.title}
                    </a>
                  ) : (
                    <span className="text-[11px] text-slate-500 italic">Unknown source</span>
                  )}
                </div>
                <ConfidenceRing score={insight.confidence_score} />
              </div>

              {/* Theme pill */}
              <div className="mb-2">
                <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
                  {insight.detected_theme}
                </span>
              </div>

              {/* Summary */}
              <p className="text-[11px] text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors line-clamp-3">
                {insight.image_summary}
              </p>

              {/* Visual elements as pills */}
              {insight.notable_visual_elements.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {insight.notable_visual_elements.map((el) => (
                    <span
                      key={el}
                      className="rounded-full bg-slate-700/60 px-2 py-0.5 text-[10px] text-slate-400"
                    >
                      {el}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
