import { useStore } from './store'

let ctx: AudioContext | null = null

function audio(): AudioContext {
  ctx ??= new AudioContext()
  void ctx.resume()
  return ctx
}

function beep(freq: number, length: number, peak: number): void {
  const c = audio()
  const t = c.currentTime
  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = 'sine'
  osc.frequency.value = freq
  gain.gain.setValueAtTime(0.0001, t)
  gain.gain.exponentialRampToValueAtTime(peak, t + 0.01)
  gain.gain.exponentialRampToValueAtTime(0.0001, t + length)
  osc.connect(gain).connect(c.destination)
  osc.start(t)
  osc.stop(t + length + 0.02)
}

export type Cue = 'start' | 'stop'

/** Short beep so the user can tell, without looking, that recording started or stopped. */
export function playCue(kind: Cue): void {
  if (!useStore.getState().soundCues) return
  try {
    beep(kind === 'start' ? 880 : 520, 0.14, 0.25)
  } catch {
    // cues are optional
  }
}

let thinkingTimer: number | null = null

/** Soft tick every 1.2 s while waiting for an answer (silent for quick answers). */
export function startThinking(): void {
  stopThinking()
  if (!useStore.getState().soundCues) return
  thinkingTimer = window.setInterval(() => {
    try {
      beep(330, 0.18, 0.06)
    } catch {
      // optional
    }
  }, 1200)
}

export function stopThinking(): void {
  if (thinkingTimer !== null) {
    window.clearInterval(thinkingTimer)
    thinkingTimer = null
  }
}
