import type { Mode } from '../api/types'
import { useStore } from '../store'

const MODES: { value: Mode; title: string; hint: string }[] = [
  { value: 'describe', title: 'Describe', hint: 'What is in front of me' },
  { value: 'read', title: 'Read text', hint: 'Read printed or handwritten text' },
  { value: 'product', title: 'Product', hint: 'Identify a product or a medicine box' },
  { value: 'currency', title: 'Currency (MAD)', hint: 'Recognize Moroccan banknotes and coins' },
  { value: 'find', title: 'Find object', hint: 'Ask where an object is' },
]

export default function ModeCards() {
  const mode = useStore((s) => s.mode)
  const setSettings = useStore((s) => s.setSettings)

  return (
    <fieldset className="rounded-2xl border border-border bg-surface p-6">
      <legend className="px-2 text-lg font-semibold">What do you want to do?</legend>
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
            <span className="text-lg font-semibold">{m.title}</span>
            <span className="text-muted">{m.hint}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
