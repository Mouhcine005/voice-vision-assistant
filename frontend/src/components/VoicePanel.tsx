import { useCallback, useEffect, useRef, useState } from 'react'
import { playCue } from '../audioCue'
import { VoiceRecorder } from '../recorder'
import { stopSpeaking } from '../speech'
import { useStore } from '../store'

type Phase = 'idle' | 'starting' | 'recording'

const BARS = 48
const MIN_RECORDING_MS = 500
const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

function micErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Microphone access was blocked. Allow the microphone for this site in the browser, then try again.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'No microphone was found.'
  if (name === 'NotReadableError') return 'The microphone is busy in another application.'
  if (name === 'NotSupportedError') {
    return 'Recording is not supported here. Use a recent Chrome on localhost or HTTPS.'
  }
  return 'Could not start the microphone.'
}

export default function VoicePanel() {
  const busy = useStore((s) => s.busy)
  const sendAudio = useStore((s) => s.sendAudio)
  const notify = useStore((s) => s.notify)
  const [phase, setPhase] = useState<Phase>('idle')
  const recRef = useRef<VoiceRecorder | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const orbRef = useRef<HTMLSpanElement>(null)

  const finish = useCallback(async () => {
    const rec = recRef.current
    if (!rec || !rec.isRecording) return
    recRef.current = null
    setPhase('idle')
    const result = await rec.stop()
    playCue('stop')
    if (result.durationMs < MIN_RECORDING_MS) {
      notify('Recording was too short. Press the microphone button and ask your question.')
      return
    }
    void sendAudio(result.blob)
  }, [notify, sendAudio])

  const cancel = useCallback(() => {
    recRef.current?.cancel()
    recRef.current = null
    setPhase('idle')
  }, [])

  const start = useCallback(async () => {
    if (recRef.current) return
    const { busy: isBusy, photoUrl } = useStore.getState()
    if (isBusy) return
    if (!photoUrl) {
      notify('Send a photo first.')
      return
    }
    stopSpeaking()
    setPhase('starting')
    try {
      const rec = await VoiceRecorder.open(() => void finish())
      recRef.current = rec
      playCue('start')
      await sleep(220)
      if (recRef.current !== rec) {
        rec.cancel()
        return
      }
      rec.begin()
      setPhase('recording')
    } catch (err) {
      recRef.current = null
      setPhase('idle')
      notify(micErrorMessage(err))
    }
  }, [finish, notify])

  const toggle = useCallback(() => {
    if (phase === 'recording') void finish()
    else if (phase === 'idle') void start()
  }, [phase, finish, start])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (recRef.current) {
          cancel()
          playCue('stop')
        } else {
          stopSpeaking()
        }
        return
      }
      if (event.code !== 'Space' || event.repeat) return
      if (event.ctrlKey || event.altKey || event.metaKey) return
      const target = event.target
      if (
        target instanceof HTMLElement &&
        target.closest('input, textarea, select, button, a, [contenteditable="true"]')
      ) {
        return
      }
      event.preventDefault()
      toggle()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggle, cancel])

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const levels: number[] = new Array<number>(BARS).fill(0)
    let raf = 0
    const draw = () => {
      const level = recRef.current?.getLevel() ?? 0
      levels.push(level)
      levels.shift()
      const canvas = canvasRef.current
      const g = canvas?.getContext('2d')
      if (canvas && g) {
        g.clearRect(0, 0, canvas.width, canvas.height)
        g.fillStyle = '#ffd60a'
        const w = canvas.width / BARS
        for (let i = 0; i < BARS; i++) {
          const h = Math.max(3, Math.min(1, levels[i] * 4) * canvas.height)
          g.fillRect(i * w + 1, (canvas.height - h) / 2, w - 2, h)
        }
      }
      const orb = orbRef.current
      if (orb && !reduceMotion) orb.style.transform = `scale(${1 + Math.min(level * 2.5, 0.3)})`
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [])

  const recording = phase === 'recording'
  const label = busy
    ? 'Thinking...'
    : phase === 'starting'
      ? 'Getting the microphone...'
      : recording
        ? 'Listening... tap to stop'
        : 'Ask by voice'
  const status =
    phase === 'recording'
      ? 'Listening. Speak your question, then pause, or press Space to stop.'
      : phase === 'starting'
        ? 'Getting the microphone.'
        : ''

  return (
    <section aria-labelledby="voice-heading" className="rounded-2xl border border-border bg-surface p-6">
      <h2 id="voice-heading" className="text-lg font-semibold">
        Voice
      </h2>
      <div className="mt-4 flex flex-col items-center gap-4">
        <span ref={orbRef} className="inline-block will-change-transform">
          <button
            type="button"
            onClick={toggle}
            aria-disabled={busy || phase === 'starting'}
            className={`flex size-36 items-center justify-center rounded-full p-4 text-center text-xl font-bold aria-disabled:opacity-50 ${
              recording ? 'bg-danger text-black' : 'bg-accent text-accent-fg'
            }`}
          >
            {label}
          </button>
        </span>
        <canvas ref={canvasRef} width={480} height={64} aria-hidden="true" className="h-16 w-full max-w-md" />
        <p role="status" className="min-h-7 text-center text-lg">
          {status}
        </p>
        <p className="text-center text-muted">Press Space to start and stop. Escape cancels.</p>
      </div>
    </section>
  )
}
