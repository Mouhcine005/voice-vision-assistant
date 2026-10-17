import type { AskResponse, Detail, Lang, Mode } from './types'

export class ApiError extends Error {
  status: number
  retryAfter: number | null

  constructor(message: string, status: number, retryAfter: number | null = null) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let message = `HTTP ${res.status}`
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') message = data.detail
  } catch {
    // keep the default message
  }
  const retry = res.headers.get('Retry-After')
  return new ApiError(message, res.status, retry ? Number(retry) : null)
}

function audioFileName(blob: Blob): string {
  if (blob.type.includes('mp4')) return 'question.m4a'
  if (blob.type.includes('ogg')) return 'question.ogg'
  return 'question.webm'
}

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch('/api/session', { method: 'POST' })
  if (!res.ok) throw await toApiError(res)
  return res.json()
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`/api/session/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => undefined)
}

export type AskParams = {
  sessionId: string
  lang: Lang
  detail: Detail
  mode: Mode
  text?: string
  image?: File
  audio?: Blob
  force?: boolean
  signal?: AbortSignal
}

export async function ask(p: AskParams): Promise<AskResponse> {
  const form = new FormData()
  form.set('session_id', p.sessionId)
  form.set('lang', p.lang)
  form.set('detail', p.detail)
  form.set('mode', p.mode)
  if (p.force) form.set('force', 'true')
  if (p.text) form.set('text', p.text)
  if (p.image) form.set('image', p.image, p.image.name || 'photo.jpg')
  if (p.audio) form.set('audio', p.audio, audioFileName(p.audio))
  const res = await fetch('/api/ask', { method: 'POST', body: form, signal: p.signal })
  if (!res.ok) throw await toApiError(res)
  return (await res.json()) as AskResponse
}

export async function fetchSpeech(text: string, lang: Lang, speed = 1): Promise<Blob> {
  const res = await fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, lang, speed }),
  })
  if (!res.ok) throw await toApiError(res)
  return res.blob()
}
