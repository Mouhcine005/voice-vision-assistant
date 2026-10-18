import { useEffect } from 'react'
import type { Lang, Mode } from '../api/types'
import i18n from '../i18n'
import { useStore } from '../store'

const MODE_KEYS: Record<string, { mode: Mode; label: string }> = {
  Digit1: { mode: 'describe', label: 'modeDescribe' },
  Digit2: { mode: 'read', label: 'modeRead' },
  Digit3: { mode: 'product', label: 'modeProduct' },
  Digit4: { mode: 'currency', label: 'modeCurrency' },
  Digit5: { mode: 'find', label: 'modeFind' },
}

const LANG_ORDER: Lang[] = ['en', 'fr', 'ar']
const LANG_NAMES: Record<Lang, string> = {
  en: 'English',
  fr: 'Fran\u00e7ais',
  ar: '\u0627\u0644\u0639\u0631\u0628\u064a\u0629',
}

function nextLang(current: Lang): Lang {
  const index = LANG_ORDER.indexOf(current)
  return LANG_ORDER[(index + 1) % LANG_ORDER.length] ?? 'en'
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  if (target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return true
  if (target instanceof HTMLInputElement) {
    return !['checkbox', 'radio', 'button', 'range', 'file', 'submit'].includes(target.type)
  }
  return false
}

function clickById(id: string): void {
  document.getElementById(id)?.click()
}

/** Global single-key shortcuts. Space and Escape are handled by the voice panel. */
export default function Shortcuts({ onHelp }: { onHelp: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) return
      if (isTyping(event.target) || document.querySelector('dialog[open]')) return

      const s = useStore.getState()
      const code = event.code

      const modeKey = MODE_KEYS[code]
      if (modeKey) {
        event.preventDefault()
        s.setSettings({ mode: modeKey.mode })
        s.announce(i18n.t('modeSelected', { mode: i18n.t(modeKey.label) }))
        return
      }

      switch (code) {
        case 'KeyP':
          event.preventDefault()
          clickById('photo-file')
          break
        case 'KeyC':
          event.preventDefault()
          clickById('camera-file')
          break
        case 'KeyR':
          event.preventDefault()
          s.repeatLast()
          break
        case 'KeyT': {
          event.preventDefault()
          const input = document.getElementById('question') as HTMLInputElement | null
          if (input && !input.disabled) input.focus()
          else s.announce(i18n.t('needPhoto'))
          break
        }
        case 'KeyN':
          event.preventDefault()
          void s.reset().then(() => useStore.getState().announce(i18n.t('newConversationStarted')))
          break
        case 'KeyL': {
          event.preventDefault()
          const next = nextLang(s.lang)
          s.setSettings({ lang: next })
          useStore.getState().announce(LANG_NAMES[next])
          break
        }
        case 'KeyH':
          event.preventDefault()
          onHelp()
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onHelp])

  return null
}
