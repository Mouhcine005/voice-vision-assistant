import { useEffect, useRef } from 'react'
import type { Detail, Lang } from '../api/types'
import { speak } from '../speech'
import { useStore } from '../store'
import Select from './Select'
import type { Option } from './Select'

const DETAILS: Option<Detail>[] = [
  { value: 'brief', label: 'Brief' },
  { value: 'detailed', label: 'Detailed' },
]

const SAMPLE: Record<Lang, string> = {
  en: 'This is how I sound.',
  fr: 'Voici ma voix.',
  ar: '\u0647\u0630\u0627 \u0647\u0648 \u0635\u0648\u062a\u064a.',
}

export default function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const { lang, detail, autoSpeak, speed, soundCues, setSettings } = useStore()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="settings-title"
      className="m-auto w-full max-w-md rounded-2xl border border-border bg-surface p-6 text-fg backdrop:bg-black/70"
    >
      <h2 id="settings-title" className="text-xl font-bold">
        Settings
      </h2>

      <div className="mt-5 space-y-5">
        <Select
          id="detail"
          label="Answer length"
          value={detail}
          options={DETAILS}
          onChange={(v) => setSettings({ detail: v })}
        />

        <label className="flex items-center gap-3 text-lg">
          <input
            type="checkbox"
            checked={autoSpeak}
            onChange={(e) => setSettings({ autoSpeak: e.target.checked })}
            className="size-5 accent-accent"
          />
          Speak answers aloud
        </label>

        <label className="flex items-center gap-3 text-lg">
          <input
            type="checkbox"
            checked={soundCues}
            onChange={(e) => setSettings({ soundCues: e.target.checked })}
            className="size-5 accent-accent"
          />
          Sound cues (beeps and waiting tick)
        </label>

        <div className="flex flex-col gap-2">
          <label htmlFor="speed" className="text-lg">
            Speech speed: {speed.toFixed(2)}x
          </label>
          <input
            id="speed"
            type="range"
            min="0.75"
            max="1.5"
            step="0.05"
            value={speed}
            aria-valuetext={`${speed.toFixed(2)} times normal speed`}
            onChange={(e) => setSettings({ speed: Number(e.target.value) })}
            className="accent-accent"
          />
          <button
            type="button"
            onClick={() => void speak(SAMPLE[lang], lang, speed)}
            className="self-start rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            Test voice
          </button>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl bg-accent px-5 py-3 text-lg font-semibold text-accent-fg"
        >
          Close
        </button>
      </div>
    </dialog>
  )
}
