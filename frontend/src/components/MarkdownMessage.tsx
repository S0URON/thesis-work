import {
  Children,
  type ComponentPropsWithoutRef,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { MermaidBlock } from './MermaidBlock'

function Pre({
  children,
  ...rest
}: ComponentPropsWithoutRef<'pre'>) {
  const child = Children.toArray(children).find(
    (c): c is ReactElement<{ className?: string; children?: ReactNode }> =>
      isValidElement(c) && c.type === 'code',
  )
  const cls = child?.props.className ?? ''
  if (cls.includes('language-mermaid')) {
    const text = String(child?.props.children ?? '').replace(/\n$/, '')
    return <MermaidBlock key={text} chart={text} />
  }
  return (
    <pre {...rest} className="md-pre">
      {children}
    </pre>
  )
}

type Props = {
  content: string
}

export function MarkdownMessage({ content }: Props) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ pre: Pre }}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
