import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { SILENCE_MS } from '../recorder'
import { useStore } from '../store'
import LatencyChart from './LatencyChart'
import type { Row } from './LatencyChart'

type Stage = { n: number; p50: number | null; p95: number | null }
type Summary = {
  requests: number
  errors: number
  skipped_model: number
  fallback_used: number
  target_ms: number
  within_target_pct: number | null
  stages: Record<'preprocess' | 'rate_wait' | 'stt' | 'vlm' | 'total', Stage>
}

const STAGES: { key: keyof Summary['stages']; label: string }[] = [
  { key: 'preprocess', label: 'stagePreprocess' },
  { key: 'rate_wait', label: 'stageRateWait' },
  { key: 'stt', label: 'stageStt' },
  { key: 'vlm', label: 'stageVlm' },
  { key: 'total', label: 'stageTotal' },
]

const secs = (ms: number | null) => (ms === null ? '-' : (ms / 1000).toFixed(1))

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-2 p-3">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="text-2xl font-bold">{value}</dd>
    </div>
  )
}

export default function JuryPanel() {
  const { t } = useTranslation()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [rows, setRows] = useState<Row[]>([])
  const lastTimings = useStore((s) => s.lastTimings)
  const askMs = useStore((s) => s.lastAskMs)
  const ttsMs = useStore((s) => s.lastTtsMs)
  const voice = useStore((s) => s.lastVoice)

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const [s, r] = await Promise.all([
        fetch('/api/metrics/summary?window=200', { signal }).then((x) => x.json() as Promise<Summary>),
        fetch('/api/metrics/recent?limit=20', { signal }).then((x) => x.json() as Promise<{ items: Row[] }>),
      ])
      setSummary(s)
      setRows([...r.items].reverse())
    } catch {
      // keep showing the last data
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    const timer = window.setInterval(() => void refresh(controller.signal), 5000)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [refresh])

  useEffect(() => {
    if (lastTimings) void refresh()
  }, [lastTimings, refresh])

  const perceived = askMs === null ? null : (voice ? SILENCE_MS : 0) + askMs + (ttsMs ?? 0)
  const perceivedDetail =
    askMs === null
      ? ''
      : voice
        ? t('juryPerceivedVoice', { silence: secs(SILENCE_MS), server: secs(askMs), voice: secs(ttsMs ?? 0) })
        : t('juryPerceivedText', { server: secs(askMs), voice: secs(ttsMs ?? 0) })

  return (
    <section id="jury" aria-labelledby="jury-title" className="rounded-2xl border border-border bg-surface p-6">
      <h2 id="jury-title" className="text-lg font-semibold">
        {t('juryTitle')}
      </h2>

      {summary && summary.requests === 0 && <p className="mt-3 text-muted">{t('juryEmpty')}</p>}

      {summary && (
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Tile label={t('juryRequests')} value={String(summary.requests)} />
          <Tile
            label={t('juryWithin')}
            value={summary.within_target_pct === null ? '-' : `${summary.within_target_pct}%`}
          />
          <Tile label={t('juryErrors')} value={String(summary.errors)} />
          <Tile label={t('juryFallback')} value={String(summary.fallback_used)} />
        </dl>
      )}

      {perceived !== null && (
        <div className="mt-4 rounded-xl border border-border bg-surface-2 p-4">
          <p className="text-sm text-muted">{t('juryPerceived')}</p>
          <p className="text-3xl font-bold">{secs(perceived)} s</p>
          <p className="text-muted">{perceivedDetail}</p>
        </div>
      )}

      {summary && (
        <table className="mt-5 w-full">
          <caption className="sr-only">{t('juryStages')}</caption>
          <thead>
            <tr className="text-muted">
              <th scope="col" className="py-1 text-start font-normal">
                {t('colStage')}
              </th>
              <th scope="col" className="text-end font-normal">
                {t('colMedian')}
              </th>
              <th scope="col" className="text-end font-normal">
                {t('colP95')}
              </th>
              <th scope="col" className="text-end font-normal">
                {t('colSamples')}
              </th>
            </tr>
          </thead>
          <tbody>
            {STAGES.map((stage) => {
              const s = summary.stages[stage.key]
              return (
                <tr key={stage.key} className="border-t border-border">
                  <th scope="row" className="py-1 text-start font-normal">
                    {t(stage.label)}
                  </th>
                  <td className="text-end">{secs(s.p50)} s</td>
                  <td className="text-end">{secs(s.p95)} s</td>
                  <td className="text-end">{s.n}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <h3 className="mt-6 text-lg font-semibold">{t('juryChartTitle')}</h3>
      <LatencyChart rows={rows} />

      <details className="mt-4">
        <summary className="cursor-pointer text-lg">{t('juryTable')}</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted">
                <th scope="col" className="py-1 text-start font-normal">
                  #
                </th>
                <th scope="col" className="text-start font-normal">
                  {t('colTime')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('colStatus')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('stagePreprocess')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('stageRateWait')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('stageStt')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('stageVlm')}
                </th>
                <th scope="col" className="text-end font-normal">
                  {t('colTotal')}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="py-1">{i + 1}</td>
                  <td>{row.ts.slice(11, 19)}</td>
                  <td className="text-end">{row.status}</td>
                  <td className="text-end">{secs(row.ms_preprocess)}</td>
                  <td className="text-end">{secs(row.ms_rate_wait)}</td>
                  <td className="text-end">
                    {secs(row.ms_stt)}
                    {row.audio_s ? <span className="text-muted"> ({row.audio_s.toFixed(1)} s)</span> : null}
                  </td>
                  <td className="text-end">{secs(row.ms_vlm)}</td>
                  <td className="text-end">{secs(row.ms_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}
