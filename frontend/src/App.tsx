import { useEffect, useState } from 'react'

type Health = {
  status: string
  env: string
  provider: string
  model: string
  provider_configured: boolean
  whisper_model: string
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

export default function App() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<Health>
      })
      .then((health) => setState({ kind: 'ok', health }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setState({
          kind: 'error',
          message: err instanceof Error ? err.message : 'Unknown error',
        })
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="min-h-screen bg-bg text-fg">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">Voice Vision Assistant</h1>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <section
          aria-labelledby="backend-heading"
          className="rounded-2xl border border-border bg-surface p-6"
        >
          <h2 id="backend-heading" className="text-lg font-semibold">
            Server
          </h2>

          <p role="status" className="mt-3 text-lg">
            {state.kind === 'loading' && 'Connecting to the server...'}
            {state.kind === 'ok' && (
              <span className="text-ok">Server connected.</span>
            )}
            {state.kind === 'error' && (
              <span className="text-danger">
                Cannot reach the server ({state.message}). Is the backend running?
              </span>
            )}
          </p>

          {state.kind === 'ok' && (
            <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-muted">
              <dt>Vision model</dt>
              <dd className="text-fg">
                {state.health.provider} / {state.health.model}
              </dd>
              <dt>Configured</dt>
              <dd className="text-fg">
                {state.health.provider_configured ? 'yes' : 'no'}
              </dd>
              <dt>Offline speech model</dt>
              <dd className="text-fg">{state.health.whisper_model}</dd>
              <dt>Environment</dt>
              <dd className="text-fg">{state.health.env}</dd>
            </dl>
          )}
        </section>
      </main>
    </div>
  )
}
