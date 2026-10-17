import { fetchSpeech } from './api/client'
import type { Lang } from './api/types'

const BROWSER_LANG: Record<Lang, string> = { en: 'en-US', fr: 'fr-FR', ar: 'ar-SA' }
const MAX_TTS_CHARS = 1500

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

function speakWithBrowser(text: string, lang: Lang): 'browser' | 'none' {
  if (!('speechSynthesis' in window)) return 'none'
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = BROWSER_LANG[lang]
  window.speechSynthesis.speak(utterance)
  return 'browser'
}

export async function speak(text: string, lang: Lang): Promise<'server' | 'browser' | 'none'> {
  stopSpeaking()
  const mine = token
  try {
    const blob = await fetchSpeech(text.slice(0, MAX_TTS_CHARS), lang)
    if (mine !== token) return 'none'
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
    if (mine !== token) return 'none'
    return speakWithBrowser(text, lang)
  }
}
