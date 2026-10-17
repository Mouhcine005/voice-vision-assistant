export type Lang = 'en' | 'fr' | 'ar'
export type Mode = 'describe' | 'read' | 'product' | 'currency' | 'find'
export type Detail = 'brief' | 'detailed'

export type Timings = {
  preprocess: number
  rate_wait: number
  stt: number
  vlm: number
  total: number
}

export type Quality = {
  ok: boolean
  severity: 'ok' | 'warn' | 'bad'
  issues: string[]
  advice: string
  metrics: { brightness: number; contrast: number; sharpness: number }
}

export type AskResponse = {
  text: string
  skipped_model: boolean
  no_speech: boolean
  transcript: string | null
  session_id: string
  turns: number
  mode: Mode
  lang: Lang
  detail: Detail
  provider: string | null
  model: string | null
  used_fallback: boolean
  attempts: number
  stt: { engine: string; audio_seconds: number } | null
  image: { width: number; height: number; sent_bytes: number; new: boolean } | null
  quality: Quality | null
  timings_ms: Timings
}
