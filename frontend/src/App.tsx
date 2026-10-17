import { useEffect, useState } from 'react'
import type { Lang } from './api/types'
import { startThinking, stopThinking } from './audioCue'
import Conversation from './components/Conversation'
import ModeCards from './components/ModeCards'
import PhotoPanel from './components/PhotoPanel'
import Select from './components/Select'
import type { Option } from './components/Select'
import SettingsDialog from './components/SettingsDialog'
import VoicePanel from './components/VoicePanel'
import { useStore } from './store'

const LANGS: Option<Lang>[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'ar', label: '\u0627\u0644\u0639\u0631\u0628\u064a\u0629' },
]

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

function ThinkingSound() {
  const busy = useStore((s) => s.busy)
  useEffect(() => {
    if (!busy) return
    startThinking()
    return () => stopThinking()
  }, [busy])
  return null
}

export default function App() {
  const lang = useStore((s) => s.lang)
  const setSettings = useStore((s) => s.setSettings)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="min-h-screen bg-bg text-fg">
      <ThinkingSound />
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">Voice Vision Assistant</h1>
        <ServerStatus />
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <section aria-label="Language and settings" className="flex flex-wrap items-end gap-4">
          <Select id="lang" label="Language" value={lang} options={LANGS} onChange={(v) => setSettings({ lang: v })} />
          <button
            type="button"
            aria-haspopup="dialog"
            onClick={() => setSettingsOpen(true)}
            className="rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            Settings
          </button>
        </section>

        <ModeCards />
        <PhotoPanel />
        <VoicePanel />
        <Conversation />
      </main>

      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
