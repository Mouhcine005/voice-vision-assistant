import { useTranslation } from 'react-i18next'
import type { Mode } from '../api/types'
import { useStore } from '../store'

const MODES: { value: Mode; title: string; hint: string }[] = [
  { value: 'describe', title: 'modeDescribe', hint: 'modeDescribeHint' },
  { value: 'read', title: 'modeRead', hint: 'modeReadHint' },
  { value: 'product', title: 'modeProduct', hint: 'modeProductHint' },
  { value: 'currency', title: 'modeCurrency', hint: 'modeCurrencyHint' },
  { value: 'find', title: 'modeFind', hint: 'modeFindHint' },
]

export default function ModeCards() {
  const { t } = useTranslation()
  const mode = useStore((s) => s.mode)
  const setSettings = useStore((s) => s.setSettings)

  return (
    <fieldset className="rounded-2xl border border-border bg-surface p-6">
      <legend className="px-2 text-lg font-semibold">{t('modeTitle')}</legend>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        {MODES.map((m) => (
          <label
            key={m.value}
            className="flex cursor-pointer flex-col gap-1 rounded-xl border-2 border-border bg-surface-2 p-4 has-[:checked]:border-accent has-[:checked]:bg-bg has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent"
          >
            <input
              type="radio"
              name="mode"
              value={m.value}
              checked={mode === m.value}
              onChange={() => setSettings({ mode: m.value })}
              className="sr-only"
            />
            <span className="text-lg font-semibold">{t(m.title)}</span>
            <span className="text-muted">{t(m.hint)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
