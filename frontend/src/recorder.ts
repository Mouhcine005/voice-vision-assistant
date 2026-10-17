const SILENCE_MS = 1400 // quiet time after speech that ends the recording
const MIN_SPEECH_MS = 300 // speech shorter than this does not count
const NO_SPEECH_MS = 7000 // give up if nothing is said at all
const MAX_MS = 20000
const CALIBRATE_MS = 400
const MIN_THRESHOLD = 0.02
const MAX_THRESHOLD = 0.06

export type RecordingResult = { blob: Blob; durationMs: number; heardSpeech: boolean }

function pickMime(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((m) =>
    MediaRecorder.isTypeSupported(m),
  )
}

export class VoiceRecorder {
  private stream: MediaStream
  private ctx: AudioContext
  private analyser: AnalyserNode
  private samples = new Uint8Array(1024)
  private recorder: MediaRecorder | null = null
  private chunks: Blob[] = []
  private timer: number | null = null
  private startedAt = 0
  private speechAt = 0
  private lastLoudAt = 0
  private threshold = MIN_THRESHOLD
  private calibration: number[] = []
  private onAutoStop: () => void
  private closed = false

  private constructor(
    stream: MediaStream,
    ctx: AudioContext,
    analyser: AnalyserNode,
    onAutoStop: () => void,
  ) {
    this.stream = stream
    this.ctx = ctx
    this.analyser = analyser
    this.onAutoStop = onAutoStop
  }

  /** Ask for the microphone (this is where the permission prompt appears). Does not record yet. */
  static async open(onAutoStop: () => void): Promise<VoiceRecorder> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new DOMException('No media devices', 'NotSupportedError')
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
    })
    try {
      const ctx = new AudioContext()
      await ctx.resume()
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 1024
      ctx.createMediaStreamSource(stream).connect(analyser)
      return new VoiceRecorder(stream, ctx, analyser, onAutoStop)
    } catch (err) {
      stream.getTracks().forEach((track) => track.stop())
      throw err
    }
  }

  get isRecording(): boolean {
    return this.recorder?.state === 'recording'
  }

  /** Current loudness, 0 (silence) to about 1. */
  getLevel(): number {
    if (this.closed) return 0
    this.analyser.getByteTimeDomainData(this.samples)
    let sum = 0
    for (const v of this.samples) {
      const x = (v - 128) / 128
      sum += x * x
    }
    return Math.sqrt(sum / this.samples.length)
  }

  /** True once real speech (not just background noise) was heard in this recording. */
  get heardSpeech(): boolean {
    return this.speechAt !== 0 && this.lastLoudAt - this.speechAt >= MIN_SPEECH_MS
  }

  begin(): void {
    const mime = pickMime()
    this.recorder = new MediaRecorder(this.stream, mime ? { mimeType: mime } : undefined)
    this.recorder.ondataavailable = (event) => {
      if (event.data.size > 0) this.chunks.push(event.data)
    }
    this.recorder.start()
    this.startedAt = performance.now()
    this.lastLoudAt = this.startedAt
    this.timer = window.setInterval(() => this.tick(), 100)
  }

  private tick(): void {
    const now = performance.now()
    const elapsed = now - this.startedAt
    const level = this.getLevel()

    if (elapsed < CALIBRATE_MS) {
      this.calibration.push(level)
      return
    }
    if (this.calibration.length > 0) {
      const mean = this.calibration.reduce((a, b) => a + b, 0) / this.calibration.length
      this.threshold = Math.min(MAX_THRESHOLD, Math.max(MIN_THRESHOLD, mean * 2.5))
      this.calibration = []
    }

    if (level > this.threshold) {
      if (this.speechAt === 0) this.speechAt = now
      this.lastLoudAt = now
    }
    const spoke = this.speechAt !== 0 && this.lastLoudAt - this.speechAt >= MIN_SPEECH_MS
    if (
      (spoke && now - this.lastLoudAt > SILENCE_MS) ||
      (this.speechAt === 0 && elapsed > NO_SPEECH_MS) ||
      elapsed > MAX_MS
    ) {
      this.stopTimer()
      this.onAutoStop()
    }
  }

  private stopTimer(): void {
    if (this.timer !== null) {
      window.clearInterval(this.timer)
      this.timer = null
    }
  }

  stop(): Promise<RecordingResult> {
    this.stopTimer()
    const recorder = this.recorder
    const heardSpeech = this.heardSpeech
    return new Promise((resolve) => {
      const done = () => {
        const blob = new Blob(this.chunks, { type: recorder?.mimeType || 'audio/webm' })
        const durationMs = this.startedAt === 0 ? 0 : performance.now() - this.startedAt
        this.close()
        resolve({ blob, durationMs, heardSpeech })
      }
      if (!recorder || recorder.state === 'inactive') {
        done()
        return
      }
      recorder.onstop = done
      recorder.stop()
    })
  }

  /** Stop and throw the recording away. */
  cancel(): void {
    if (this.closed) return
    this.stopTimer()
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.onstop = null
      this.recorder.stop()
    }
    this.close()
  }

  private close(): void {
    if (this.closed) return
    this.closed = true
    this.stream.getTracks().forEach((track) => track.stop())
    void this.ctx.close()
  }
}
