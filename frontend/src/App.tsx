import { useEffect, useState } from 'react'
import type { Detail, Lang, Mode } from './api/types'
import Conversation from './components/Conversation'
import PhotoPanel from './components/PhotoPanel'
import { useStore } from './store'

type Option<T extends string> = { value: T; label: string }

const LANGS: Option<Lang>[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'ar', label: '\u0627\u0644\u0639\u0631\u0628\u064a\u0629' },
]
const DETAILS: Option<Detail>[] = [
  { value: 'brief', label: 'Brief' },
  { value: 'detailed', label: 'Detailed' },
]
const MODES: Option<Mode>[] = [
  { value: 'describe', label: 'Describe' },
  { value: 'read', label: 'Read text' },
  { value: 'product', label: 'Product' },
  { value: 'currency', label: 'Currency (MAD)' },
  { value: 'find', label: 'Find object' },
]

function Select<T extends string>(props: {
  id: string
  label: string
  value: T
  options: Option<T>[]
  onChange: (value: T) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={props.id} className="text-sm text-muted">
        {props.label}
      </label>
      <select
        id={props.id}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value as T)}
        className="rounded-xl border border-border bg-surface-2 px-3 py-2 text-lg text-fg"
      >
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function ServerStatus() {
  const [text, setText] = useState('Connecting to the server...')
  const [ok, setOk] = useState<boolean | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<{ provider: string; model: string; provider_configured: boolean }>
      })
      .then((h) => {
        setOk(h.provider_configured)
        setText(
          h.provider_configured
            ? `Server connected (${h.provider} / ${h.model}).`
            : 'Server connected, but the vision provider is not configured.',
        )
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setOk(false)
        setText(`Cannot reach the server (${err instanceof Error ? err.message : 'error'}). Is the backend running?`)
      })
    return () => controller.abort()
  }, [])

  return (
    <p role="status" className={ok === false ? 'text-danger' : ok === true ? 'text-ok' : 'text-muted'}>
      {text}
    </p>
  )
}

export default function App() {
  const { lang, detail, mode, autoSpeak, setSettings } = useStore()

  return (
    <div className="min-h-screen bg-bg text-fg">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">Voice Vision Assistant</h1>
        <ServerStatus />
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <section aria-label="Settings" className="flex flex-wrap items-end gap-4">
          <Select id="lang" label="Language" value={lang} options={LANGS} onChange={(v) => setSettings({ lang: v })} />
          <Select id="mode" label="Mode" value={mode} options={MODES} onChange={(v) => setSettings({ mode: v })} />
          <Select id="detail" label="Detail" value={detail} options={DETAILS} onChange={(v) => setSettings({ detail: v })} />
          <label className="flex items-center gap-2 pb-2 text-lg">
            <input
              type="checkbox"
              checked={autoSpeak}
              onChange={(e) => setSettings({ autoSpeak: e.target.checked })}
              className="size-5 accent-accent"
            />
            Speak answers aloud
          </label>
        </section>

        <PhotoPanel />
        <Conversation />
      </main>
    </div>
  )
}
