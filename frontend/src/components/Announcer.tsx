import { useStore } from '../store'

/** Hidden live region: screen readers announce each new message, even if it repeats. */
export default function Announcer() {
  const text = useStore((s) => s.announcement)
  const id = useStore((s) => s.announcementId)
  return (
    <div role="status" aria-live="polite" className="sr-only">
      <span key={id}>{text}</span>
    </div>
  )
}
