import { useTranslation } from 'react-i18next'

export type Row = {
  id: number
  ts: string
  status: number
  skipped_model: number
  ms_preprocess: number | null
  ms_rate_wait: number | null
  ms_stt: number | null
  ms_vlm: number | null
  ms_total: number | null
}

export const STAGE_COLORS = {
  preprocess: '#7cc4ff',
  rateWait: '#ff7b7b',
  stt: '#ffd60a',
  vlm: '#5df08a',
  other: '#c4ccd6',
} as const

export type StageKey = keyof typeof STAGE_COLORS

const LEGEND: { key: StageKey; label: string }[] = [
  { key: 'preprocess', label: 'stagePreprocess' },
  { key: 'rateWait', label: 'stageRateWait' },
  { key: 'stt', label: 'stageStt' },
  { key: 'vlm', label: 'stageVlm' },
  { key: 'other', label: 'stageOther' },
]

export function segmentsOf(row: Row): { key: StageKey; ms: number }[] {
  const pre = row.ms_preprocess ?? 0
  const wait = row.ms_rate_wait ?? 0
  const stt = row.ms_stt ?? 0
  const vlm = row.ms_vlm ?? 0
  const total = row.ms_total ?? pre + wait + stt + vlm
  const other = Math.max(0, total - pre - wait - stt - vlm)
  return [
    { key: 'preprocess', ms: pre },
    { key: 'rateWait', ms: wait },
    { key: 'stt', ms: stt },
    { key: 'vlm', ms: vlm },
    { key: 'other', ms: other },
  ]
}

const W = 720
const H = 260
const M = { top: 12, right: 14, bottom: 26, left: 44 }
const TARGET_MS = 4000

export default function LatencyChart({ rows }: { rows: Row[] }) {
  const { t } = useTranslation()
  const bars = rows.map((row) => ({ segments: segmentsOf(row), total: row.ms_total ?? 0 }))
  const maxTotal = Math.max(TARGET_MS, ...bars.map((b) => b.total))
  const yMax = Math.ceil((maxTotal * 1.05) / 1000) * 1000
  const step = yMax > 8000 ? 2000 : 1000
  const ticks: number[] = []
  for (let v = 0; v <= yMax; v += step) ticks.push(v)

  const innerWidth = W - M.left - M.right
  const innerHeight = H - M.top - M.bottom
  const y = (ms: number) => M.top + innerHeight - (ms / yMax) * innerHeight
  const slot = innerWidth / Math.max(bars.length, 1)
  const barWidth = Math.min(slot * 0.7, 36)

  return (
    <div dir="ltr">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('juryChartLabel')} className="w-full">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} stroke="#3a424d" strokeWidth="1" />
            <text x={M.left - 6} y={y(v) + 4} textAnchor="end" fontSize="12" fill="#c4ccd6">
              {v / 1000}s
            </text>
          </g>
        ))}

        {bars.map((bar, i) => {
          const x = M.left + slot * i + (slot - barWidth) / 2
          let acc = 0
          return (
            <g key={i}>
              {bar.segments.map((seg) => {
                const top = y(acc + seg.ms)
                const height = y(acc) - top
                acc += seg.ms
                return height > 0 ? (
                  <rect key={seg.key} x={x} y={top} width={barWidth} height={height} fill={STAGE_COLORS[seg.key]} />
                ) : null
              })}
              <text x={x + barWidth / 2} y={H - 8} textAnchor="middle" fontSize="11" fill="#c4ccd6">
                {i + 1}
              </text>
            </g>
          )
        })}

        <line
          x1={M.left}
          x2={W - M.right}
          y1={y(TARGET_MS)}
          y2={y(TARGET_MS)}
          stroke="#ffffff"
          strokeWidth="2"
          strokeDasharray="6 4"
        />
        <text x={W - M.right} y={y(TARGET_MS) - 5} textAnchor="end" fontSize="12" fontWeight="bold" fill="#ffffff">
          4 s
        </text>
      </svg>

      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm" dir="auto">
        {LEGEND.map((item) => (
          <li key={item.key} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block size-3 rounded-sm"
              style={{ background: STAGE_COLORS[item.key] }}
            />
            {t(item.label)}
          </li>
        ))}
      </ul>
    </div>
  )
}
