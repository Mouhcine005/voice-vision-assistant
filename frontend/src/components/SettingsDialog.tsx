import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { Detail } from '../api/types'
import { speak } from '../speech'
import { useStore } from '../store'
import Select from './Select'
import type { Option } from './Select'

export default function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const ref = useRef<HTMLDialogElement>(null)
  const { lang, detail, autoSpeak, speed, soundCues, setSettings } = useStore()

  const detailOptions: Option<Detail>[] = [
    { value: 'brief', label: t('brief') },
    { value: 'detailed', label: t('detailed') },
  ]

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
        {t('settings')}
      </h2>

      <div className="mt-5 space-y-5">
        <Select
          id="detail"
          label={t('answerLength')}
          value={detail}
          options={detailOptions}
          onChange={(v) => setSettings({ detail: v })}
        />

        <label className="flex items-center gap-3 text-lg">
          <input
            type="checkbox"
            checked={autoSpeak}
            onChange={(e) => setSettings({ autoSpeak: e.target.checked })}
            className="size-5 accent-accent"
          />
          {t('speakAloud')}
        </label>

        <label className="flex items-center gap-3 text-lg">
          <input
            type="checkbox"
            checked={soundCues}
            onChange={(e) => setSettings({ soundCues: e.target.checked })}
            className="size-5 accent-accent"
          />
          {t('soundCues')}
        </label>

        <div className="flex flex-col gap-2">
          <label htmlFor="speed" className="text-lg">
            {t('speed', { value: speed.toFixed(2) })}
          </label>
          <input
            id="speed"
            type="range"
            min="0.75"
            max="1.5"
            step="0.05"
            value={speed}
            aria-valuetext={t('speedValueText', { value: speed.toFixed(2) })}
            onChange={(e) => setSettings({ speed: Number(e.target.value) })}
            className="accent-accent"
          />
          <button
            type="button"
            onClick={() => void speak(t('voiceSample'), lang, speed)}
            className="self-start rounded-xl border border-border bg-surface-2 px-4 py-2 text-lg hover:border-accent"
          >
            {t('testVoice')}
          </button>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl bg-accent px-5 py-3 text-lg font-semibold text-accent-fg"
        >
          {t('close')}
        </button>
      </div>
    </dialog>
  )
}
