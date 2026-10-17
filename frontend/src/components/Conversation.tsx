import { useState } from 'react'
import type { FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { stopSpeaking } from '../speech'
import { useStore } from '../store'

const primary =
  'rounded-xl bg-accent px-5 py-3 text-lg font-semibold text-accent-fg disabled:cursor-not-allowed disabled:opacity-50'
const secondary =
  'rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg text-fg hover:border-accent'

const sec = (ms: number) => (ms / 1000).toFixed(1)

export default function Conversation() {
  const { t } = useTranslation()
  const messages = useStore((s) => s.messages)
  const busy = useStore((s) => s.busy)
  const error = useStore((s) => s.error)
  const hasPhoto = useStore((s) => s.photoUrl !== null)
  const lastTimings = useStore((s) => s.lastTimings)
  const sendText = useStore((s) => s.sendText)
  const reset = useStore((s) => s.reset)
  const [draft, setDraft] = useState('')

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (busy || draft.trim() === '') return
    const text = draft
    setDraft('')
    void sendText(text)
  }

  return (
    <section aria-labelledby="chat-heading" className="rounded-2xl border border-border bg-surface p-6">
      <h2 id="chat-heading" className="text-lg font-semibold">
        {t('conversation')}
      </h2>

      <ol aria-live="off" className="mt-4 space-y-3">
        {messages.map((m) => (
          <li key={m.id} className={m.role === 'user' ? 'text-muted' : 'text-lg text-fg'}>
            <span className="font-semibold">
              {t(m.role === 'user' ? 'you' : 'assistant')}:{' '}
            </span>
            <span dir="auto" lang={m.lang}>
              {m.text}
            </span>
          </li>
        ))}
      </ol>

      <p role="status" className="mt-4 min-h-7 text-muted">
        {busy ? t('thinking') : ''}
      </p>
      {error && (
        <p role="alert" className="mt-2 text-lg text-danger">
          {error}
        </p>
      )}

      <form onSubmit={onSubmit} className="mt-4 flex gap-3">
        <label htmlFor="question" className="sr-only">
          {t('questionLabel')}
        </label>
        <input
          id="question"
          dir="auto"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!hasPhoto}
          placeholder={hasPhoto ? t('askPlaceholder') : t('askPlaceholderNoPhoto')}
          className="min-w-0 flex-1 rounded-xl border border-border bg-surface-2 px-4 py-3 text-lg text-fg placeholder:text-muted disabled:opacity-50"
        />
        <button type="submit" disabled={!hasPhoto || busy || draft.trim() === ''} className={primary}>
          {t('ask')}
        </button>
      </form>

      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" onClick={stopSpeaking} className={secondary}>
          {t('stopSpeaking')}
        </button>
        <button type="button" onClick={() => void reset()} className={secondary}>
          {t('newConversation')}
        </button>
      </div>

      {lastTimings && (
        <p className="mt-4 text-sm text-muted">
          {t('lastAnswer', { total: sec(lastTimings.total), vlm: sec(lastTimings.vlm) })}
          {lastTimings.stt > 0 ? t('lastAnswerSpeech', { stt: sec(lastTimings.stt) }) : ''}
        </p>
      )}
    </section>
  )
}
