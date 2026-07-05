import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Renders the final published report as nicely-styled markdown.
export default function ReportView({ text }) {
  return (
    <div className="report">
      <Markdown remarkPlugins={[remarkGfm]}>{text || ''}</Markdown>
    </div>
  )
}
