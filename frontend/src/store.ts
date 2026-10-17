import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ApiError, ask, createSession, deleteSession } from './api/client'
import type { AskResponse, Detail, Lang, Mode, Timings } from './api/types'
import { speak, stopSpeaking } from './speech'

export type Message = { id: number; role: 'user' | 'assistant'; text: string }

type Settings = {
  lang: Lang
  detail: Detail
  mode: Mode
  autoSpeak: boolean
  speed: number
  soundCues: boolean
}

type Store = Settings & {
  sessionId: string | null
  photoUrl: string | null
  messages: Message[]
  busy: boolean
  error: string | null
  lastTimings: Timings | null
  setSettings: (patch: Partial<Settings>) => void
  sendPhoto: (file: File) => Promise<void>
  sendText: (text: string) => Promise<void>
  sendAudio: (audio: Blob) => Promise<void>
  notify: (message: string) => void
  reset: () => Promise<void>
}

let nextId = 1
const msg = (role: Message['role'], text: string): Message => ({ id: nextId++, role, text })

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return `Too many requests. Try again in ${err.retryAfter ?? 'a few'} seconds.`
    }
    if (err.status === 502) return 'The vision service is not answering right now. Please try again.'
    return err.message
  }
  return 'Could not reach the server. Is the backend running?'
}

const persistOptions = {
  name: 'vva-settings',
  partialize: (s: Store) => ({
    lang: s.lang,
    detail: s.detail,
    mode: s.mode,
    autoSpeak: s.autoSpeak,
    speed: s.speed,
    soundCues: s.soundCues,
  }),
}

export const useStore = create<Store>()(persist((set, get) => {
  const say = (text: string) => {
    if (!get().autoSpeak) return
    void speak(text, get().lang, get().speed).then((how) => {
      if (how === 'unavailable' && get().error === null) {
        set({
          error:
            'No voice is available for this language on this device. Please read the answer on screen.',
        })
      }
    })
  }

  const ensureSession = async (): Promise<string> => {
    const existing = get().sessionId
    if (existing) return existing
    const created = await createSession()
    set({ sessionId: created.session_id })
    return created.session_id
  }

  const callAsk = async (
    extra: { text?: string; image?: File; audio?: Blob },
    canRetry: boolean,
  ): Promise<AskResponse> => {
    const { lang, detail, mode } = get()
    try {
      const sessionId = await ensureSession()
      return await ask({ sessionId, lang, detail, mode, ...extra })
    } catch (err) {
      if (canRetry && err instanceof ApiError && err.status === 404) {
        set({ sessionId: null })
        return callAsk(extra, false)
      }
      throw err
    }
  }

  const fail = (err: unknown) => {
    const message = describeError(err)
    set({ error: message, busy: false })
    say(message)
  }

  return {
    lang: 'en',
    detail: 'brief',
    mode: 'describe',
    autoSpeak: true,
    speed: 1,
    soundCues: true,
    sessionId: null,
    photoUrl: null,
    messages: [],
    busy: false,
    error: null,
    lastTimings: null,

    setSettings: (patch) => set(patch),

    sendPhoto: async (file) => {
      if (get().busy) return
      stopSpeaking()
      const previousUrl = get().photoUrl
      const url = URL.createObjectURL(file)
      set({ busy: true, error: null, photoUrl: url })
      try {
        const res = await callAsk({ image: file }, true)
        const label = msg('user', `Photo: ${file.name || 'camera photo'}`)
        const answer = msg('assistant', res.text)
        if (!res.skipped_model) {
          if (previousUrl) URL.revokeObjectURL(previousUrl)
          set({ photoUrl: url, messages: [label, answer], lastTimings: res.timings_ms, busy: false })
        } else {
          // Bad photo: the server kept the previous one, so keep showing it too.
          URL.revokeObjectURL(url)
          set((s) => ({
            photoUrl: previousUrl,
            messages: [...s.messages, label, answer],
            lastTimings: res.timings_ms,
            busy: false,
          }))
        }
        say(res.text)
      } catch (err) {
        URL.revokeObjectURL(url)
        set({ photoUrl: previousUrl })
        fail(err)
      }
    },

    sendText: async (raw) => {
      const text = raw.trim()
      if (!text || get().busy) return
      if (!get().photoUrl) {
        const message = 'Send a photo first.'
        set({ error: message })
        say(message)
        return
      }
      stopSpeaking()
      set((s) => ({ busy: true, error: null, messages: [...s.messages, msg('user', text)] }))
      try {
        const res = await callAsk({ text }, false)
        set((s) => ({
          messages: [...s.messages, msg('assistant', res.text)],
          lastTimings: res.timings_ms,
          busy: false,
        }))
        say(res.text)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          const url = get().photoUrl
          if (url) URL.revokeObjectURL(url)
          set({ sessionId: null, photoUrl: null })
          fail(new ApiError('The session expired. Please send the photo again.', 404))
          return
        }
        fail(err)
      }
    },

    sendAudio: async (audio) => {
      if (get().busy) return
      if (!get().photoUrl) {
        get().notify('Send a photo first.')
        return
      }
      stopSpeaking()
      set({ busy: true, error: null })
      try {
        const res = await callAsk({ audio }, false)
        set((s) => ({
          messages: [
            ...s.messages,
            ...(res.transcript ? [msg('user', res.transcript)] : []),
            msg('assistant', res.text),
          ],
          lastTimings: res.timings_ms,
          busy: false,
        }))
        say(res.text)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          const url = get().photoUrl
          if (url) URL.revokeObjectURL(url)
          set({ sessionId: null, photoUrl: null })
          fail(new ApiError('The session expired. Please send the photo again.', 404))
          return
        }
        fail(err)
      }
    },

    notify: (message) => {
      set({ error: message })
      say(message)
    },

    reset: async () => {
      stopSpeaking()
      const { sessionId, photoUrl } = get()
      if (photoUrl) URL.revokeObjectURL(photoUrl)
      set({ sessionId: null, photoUrl: null, messages: [], error: null, lastTimings: null, busy: false })
      if (sessionId) await deleteSession(sessionId)
    },
  }
}, persistOptions))
