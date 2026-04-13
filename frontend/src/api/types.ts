export type ToolEvent = {
  name?: string
  args?: unknown
  cached?: boolean
  duration_seconds?: number
  output?: unknown
  saved_path?: string
}

export type ChatRequest = {
  message: string
  session_id?: string
  /** Optional; server uses current UTC if omitted. Shown as Executive Summary Analysis Date. */
  analysis_date?: string
}

export type ChatResponse = {
  session_id: string
  assistant_text: string
  tool_events?: ToolEvent[]
  error?: string
  report_saved_path?: string
}

export type HealthResponse = {
  status: string
  ready: boolean
}

export type ReportFileContent = {
  name: string
  content: string
  format: 'markdown' | 'json'
}
