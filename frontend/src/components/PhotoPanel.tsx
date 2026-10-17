import { useEffect, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { useStore } from '../store'

const button =
  'inline-flex cursor-pointer items-center rounded-xl bg-accent px-5 py-3 text-lg font-semibold ' +
  'text-accent-fg focus-within:outline-3 focus-within:outline-offset-4 focus-within:outline-accent ' +
  'has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50'

export default function PhotoPanel() {
  const photoUrl = useStore((s) => s.photoUrl)
  const busy = useStore((s) => s.busy)
  const sendPhoto = useStore((s) => s.sendPhoto)
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const file = Array.from(event.clipboardData?.files ?? []).find((f) =>
        f.type.startsWith('image/'),
      )
      if (file) {
        event.preventDefault()
        void sendPhoto(file)
      }
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [sendPhoto])

  const onPick = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (file) void sendPhoto(file)
  }

  const onDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragging(false)
    const file = Array.from(event.dataTransfer.files).find((f) => f.type.startsWith('image/'))
    if (file) void sendPhoto(file)
  }

  return (
    <section
      aria-labelledby="photo-heading"
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`rounded-2xl border-2 border-dashed p-6 ${
        dragging ? 'border-accent bg-surface-2' : 'border-border bg-surface'
      }`}
    >
      <h2 id="photo-heading" className="text-lg font-semibold">
        Photo
      </h2>

      {photoUrl ? (
        <img src={photoUrl} alt="The photo you sent" className="mt-4 max-h-80 rounded-xl" />
      ) : (
        <p className="mt-3 text-muted">Drop an image here, paste one with Ctrl+V, or choose a file.</p>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <label className={button}>
          Choose photo
          <input type="file" accept="image/*" className="sr-only" onChange={onPick} disabled={busy} />
        </label>
        <label className={button}>
          Take photo
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            onChange={onPick}
            disabled={busy}
          />
        </label>
      </div>
    </section>
  )
}
