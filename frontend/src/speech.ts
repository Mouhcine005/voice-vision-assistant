import { fetchSpeech } from './api/client'
import type { Lang } from './api/types'

const BROWSER_LANG: Record<Lang, string> = { en: 'en-US', fr: 'fr-FR', ar: 'ar-SA' }
const MAX_TTS_CHARS = 1500

export type SpeakResult = 'server' | 'browser' | 'stopped' | 'unavailable'

let current: { audio: HTMLAudioElement; url: string } | null = null
let token = 0

function releaseAudio() {
  if (current) {
    current.audio.pause()
    URL.revokeObjectURL(current.url)
    current = null
  }
}

export function stopSpeaking() {
  token += 1
  releaseAudio()
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

function hasBrowserVoice(lang: Lang): boolean {
  const voices = window.speechSynthesis.getVoices()
  // The voice list can still be empty right after page load: then we cannot tell, so try anyway.
  return voices.length === 0 || voices.some((v) => v.lang.toLowerCase().startsWith(lang))
}

function speakWithBrowser(text: string, lang: Lang): 'browser' | 'unavailable' {
  if (!('speechSynthesis' in window) || !hasBrowserVoice(lang)) return 'unavailable'
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = BROWSER_LANG[lang]
  window.speechSynthesis.speak(utterance)
  return 'browser'
}

export async function speak(text: string, lang: Lang): Promise<SpeakResult> {
  stopSpeaking()
  const mine = token
  try {
    const blob = await fetchSpeech(text.slice(0, MAX_TTS_CHARS), lang)
    if (mine !== token) return 'stopped'
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    current = { audio, url }
    audio.addEventListener('ended', () => {
      if (current?.audio === audio) releaseAudio()
    })
    await audio.play()
    return 'server'
  } catch {
    releaseAudio()
    if (mine !== token) return 'stopped'
    return speakWithBrowser(text, lang)
  }
}
