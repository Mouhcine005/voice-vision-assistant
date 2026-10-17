let ctx: AudioContext | null = null

export type Cue = 'start' | 'stop'

/** Short beep so the user can tell, without looking, that recording started or stopped. */
export function playCue(kind: Cue): void {
  try {
    ctx ??= new AudioContext()
    void ctx.resume()
    const t = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = kind === 'start' ? 880 : 520
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.25, t + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.14)
    osc.connect(gain).connect(ctx.destination)
    osc.start(t)
    osc.stop(t + 0.15)
  } catch {
    // cues are optional
  }
}
