/** Base URL of the Agentic Crawler FastAPI server (no trailing slash). */
export function getApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined
  const base = (raw ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
  return base
}

export const SESSION_STORAGE_KEY = 'agentic-crawler-session-id'
