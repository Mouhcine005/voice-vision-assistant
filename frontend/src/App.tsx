import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Lang } from './api/types'
import { startThinking, stopThinking } from './audioCue'
import Announcer from './components/Announcer'
import Conversation from './components/Conversation'
import HelpDialog from './components/HelpDialog'
import JuryPanel from './components/JuryPanel'
import ModeCards from './components/ModeCards'
import PhotoPanel from './components/PhotoPanel'
import Select from './components/Select'
import type { Option } from './components/Select'
import SettingsDialog from './components/SettingsDialog'
import Shortcuts from './components/Shortcuts'
import VoicePanel from './components/VoicePanel'
import { hasSeenHelp, markHelpSeen } from './help'
import i18n, { applyDocumentLang } from './i18n'
import { useStore } from './store'

const LANGS: Option<Lang>[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'ar', label: '\u0627\u0644\u0639\u0631\u0628\u064a\u0629' },
]

type Server =
  | { kind: 'loading' }
  | { kind: 'ready'; provider: string; model: string; configured: boolean }
  | { kind: 'error'; error: string }

function ServerStatus() {
  const { t } = useTranslation()
  const [server, setServer] = useState<Server>({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<{ provider: string; model: string; provider_configured: boolean }>
      })
      .then((h) =>
        setServer({
          kind: 'ready',
          provider: h.provider,
          model: h.model,
          configured: h.provider_configured,
        }),
      )
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setServer({ kind: 'error', error: err instanceof Error ? err.message : 'error' })
      })
    return () => controller.abort()
  }, [])

  if (server.kind === 'loading') return <p role="status" className="text-muted">{t('serverConnecting')}</p>
  if (server.kind === 'error') {
    return (
      <p role="status" className="text-danger">
        {t('serverUnreachable', { error: server.error })}
      </p>
    )
  }
  return (
    <p role="status" className={server.configured ? 'text-ok' : 'text-danger'}>
      {server.configured
        ? t('serverConnected', { provider: server.provider, model: server.model })
        : t('serverNotConfigured')}
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
  const { t } = useTranslation()
  const lang = useStore((s) => s.lang)
  const setSettings = useStore((s) => s.setSettings)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(() => !hasSeenHelp())
  const [juryOpen, setJuryOpen] = useState(false)

  useEffect(() => {
    void i18n.changeLanguage(lang).then(() => applyDocumentLang(lang, i18n.t('appTitle')))
  }, [lang])

  return (
    <div className="min-h-screen bg-bg text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:start-2 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-fg"
      >
        {t('skipToMain')}
      </a>
      <Announcer />
      <Shortcuts onHelp={() => setHelpOpen(true)} onJury={() => setJuryOpen((open) => !open)} />
      <ThinkingSound />
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">{t('appTitle')}</h1>
        <ServerStatus />
      </header>

      <main id="main" tabIndex={-1} className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <section aria-label={t('settingsRegion')} className="flex flex-wrap items-end gap-4">
          <Select id="lang" label={t('language')} value={lang} options={LANGS} onChange={(v) => setSettings({ lang: v })} />
          <button
            type="button"
            aria-haspopup="dialog"
            onClick={() => setSettingsOpen(true)}
            className="rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            {t('settings')}
          </button>
          <button
            type="button"
            aria-haspopup="dialog"
            onClick={() => setHelpOpen(true)}
            className="rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            {t('helpButton')}
          </button>
          <button
            type="button"
            aria-expanded={juryOpen}
            aria-controls="jury"
            onClick={() => setJuryOpen((open) => !open)}
            className="rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            {t('juryButton')}
          </button>
        </section>

        <ModeCards />
        <PhotoPanel />
        <VoicePanel />
        <Conversation />
        {juryOpen && <JuryPanel />}
      </main>

      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <HelpDialog
        open={helpOpen}
        onClose={() => {
          markHelpSeen()
          setHelpOpen(false)
        }}
      />
    </div>
  )
}
