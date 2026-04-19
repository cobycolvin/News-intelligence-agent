import type { FinalReport } from '../types'

export function FinalReportPanel({ report }: { report: FinalReport }) {
  const downloadMarkdown = () => {
    const blob = new Blob([report.markdown_export], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'news-intelligence-report.md'
    link.click()
    URL.revokeObjectURL(url)
  }

  const openPrintable = () => {
    const html =`
    <html>
      <head>
        <title>Intelligence Report</title>
        <style>
          body { font-family: sans-serif; padding: 40px; line-height: 1.6; color: #1a1a1a; }
          h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }
          pre { white-space: pre-wrap; font-family: inherit; font-size: 14px; }
        </style>
      </head>
      <body>
        <h1>Intelligence Report</h1>
        <pre>${report.markdown_export}</pre>
      </body>
    </html>`;

  const win = window.open('', '_blank')
  if (win) {
    win.document.write(html)
    win.document.close()
    
    // Small timeout ensures styles are loaded before the print dialog pops up
    setTimeout(() => {
      win.print()
    }, 250)
    }
  }

  return (
    <section className="flex flex-col gap-5">

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-cyan-400">
            Synthesis Agent
          </p>
          <h3 className="text-xl font-bold text-white leading-tight">Final Report</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={downloadMarkdown}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 transition-all hover:border-slate-500 hover:bg-slate-700 hover:text-white"
          >
            Export Markdown
          </button>
          <button
            onClick={openPrintable}
            className="rounded-lg border border-cyan-600 bg-cyan-600/20 px-3 py-1.5 text-xs text-cyan-300 transition-all hover:bg-cyan-600/40 hover:text-white"
          >
            Printable View
          </button>
        </div>
      </div>

      {/* Executive summary */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
          Executive Summary
        </p>
        <p className="text-sm text-slate-300 leading-relaxed">{report.executive_summary}</p>
      </div>

      {/* Report sections */}
      <div className="flex flex-col gap-3">
        {report.sections.map((section) => (
          <div
            key={section.heading}
            className="group rounded-lg border border-slate-700 bg-slate-800/40 p-4 transition-all duration-200 hover:border-slate-600 hover:bg-slate-800/70"
          >
            {/* Section heading */}
            <h4 className="text-sm font-semibold text-white mb-2">{section.heading}</h4>

            {/* Section content */}
            <p className="text-sm text-slate-300 leading-relaxed">{section.content}</p>

            {/* Evidence chips */}
            {section.evidence.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">
                  Evidence
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {section.evidence.map((ev) => (
                    
                    <a  key={`${section.heading}-${ev.article_id}`}
                      href={ev.url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-full border border-cyan-900 bg-cyan-950/60 px-2.5 py-0.5 text-[11px] text-cyan-400 transition-all hover:border-cyan-500 hover:bg-cyan-900/40 hover:text-cyan-200"
                    >
                      {ev.title}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Sources */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
          Sources
        </p>
        <div className="flex flex-col gap-2">
          {report.sources.map((source) => (
            <div
              key={source.id}
              className="group flex items-center justify-between rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2 transition-all duration-200 hover:border-cyan-500/40 hover:bg-slate-800 hover:shadow-[0_0_10px_rgba(56,189,248,0.06)]"
            >
              
              <a  href={source.url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-cyan-300 hover:text-cyan-200 transition-colors line-clamp-1 flex-1 min-w-0"
              >
                {source.title}
              </a>
              <div className="flex items-center gap-2 ml-3 shrink-0">
                <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-400">
                  {source.source}
                </span>
                <span className="text-[10px] text-slate-500">{source.date}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

    </section>
  )
}
