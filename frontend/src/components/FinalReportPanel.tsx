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
    const html = `<html><body><pre>${report.markdown_export}</pre></body></html>`
    const win = window.open('', '_blank')
    if (win) {
      win.document.write(html)
      win.document.close()
      win.print()
    }
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Synthesis Agent Final Report</h3>
        <div className="space-x-2">
          <button onClick={downloadMarkdown} className="rounded bg-slate-700 px-3 py-1 text-sm">Export Markdown</button>
          <button onClick={openPrintable} className="rounded bg-cyan-600 px-3 py-1 text-sm">Printable View</button>
        </div>
      </div>
      <p className="mt-2 text-sm text-slate-300">{report.executive_summary}</p>
      <div className="mt-4 space-y-3">
        {report.sections.map((section) => (
          <div key={section.heading} className="rounded border border-slate-700 p-3">
            <h4 className="font-medium">{section.heading}</h4>
            <p className="text-sm mt-1">{section.content}</p>
            {section.evidence.length > 0 && (
              <div className="mt-2">
                <p className="text-xs uppercase tracking-wide text-slate-400">Evidence</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                  {section.evidence.map((evidence) => (
                    <li key={`${section.heading}-${evidence.article_id}`}>
                      <a className="text-cyan-300" href={evidence.url} target="_blank" rel="noreferrer">
                        {evidence.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
      <h4 className="mt-4 font-medium">Sources</h4>
      <ul className="list-disc pl-5 text-sm space-y-1">
        {report.sources.map((source) => (
          <li key={source.id}><a className="text-cyan-300" href={source.url} target="_blank" rel="noreferrer">{source.title}</a> ({source.source})</li>
        ))}
      </ul>
    </section>
  )
}
