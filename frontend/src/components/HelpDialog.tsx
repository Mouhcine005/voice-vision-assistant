import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { speak } from '../speech'
import { useStore } from '../store'

const ROWS: { keys: string; translateKey?: boolean; label: string }[] = [
  { keys: 'keySpace', translateKey: true, label: 'shortcutSpace' },
  { keys: 'Esc', label: 'shortcutEscape' },
  { keys: 'P', label: 'shortcutPhoto' },
  { keys: 'C', label: 'shortcutCamera' },
  { keys: 'R', label: 'shortcutRepeat' },
  { keys: 'T', label: 'shortcutType' },
  { keys: '1-5', label: 'shortcutModes' },
  { keys: 'L', label: 'shortcutLanguage' },
  { keys: 'N', label: 'shortcutNew' },
  { keys: 'H', label: 'shortcutHelp' },
]

export default function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const ref = useRef<HTMLDialogElement>(null)
  const lang = useStore((s) => s.lang)
  const speed = useStore((s) => s.speed)

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
      aria-labelledby="help-title"
      aria-describedby="help-intro"
      className="m-auto max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-surface p-6 text-fg backdrop:bg-black/70"
    >
      <h2 id="help-title" className="text-xl font-bold">
        {t('helpTitle')}
      </h2>
      <p id="help-intro" className="mt-3 text-lg text-muted">
        {t('helpIntro')}
      </p>

      <button
        type="button"
        onClick={() => void speak(t('helpSpoken'), lang, speed)}
        className="mt-4 rounded-xl bg-accent px-5 py-3 text-lg font-semibold text-accent-fg"
      >
        {t('readAloud')}
      </button>

      <dl className="mt-5 grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-3">
        {ROWS.map((row) => (
          <div key={row.label} className="contents">
            <dt>
              <kbd className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-lg">
                {row.translateKey ? t(row.keys) : row.keys}
              </kbd>
            </dt>
            <dd className="text-lg">{t(row.label)}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl border border-border bg-surface-2 px-5 py-3 text-lg hover:border-accent"
        >
          {t('close')}
        </button>
      </div>
    </dialog>
  )
}
