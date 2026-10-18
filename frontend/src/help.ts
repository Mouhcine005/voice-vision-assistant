const KEY = 'vva-welcomed'

export function hasSeenHelp(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return true
  }
}

export function markHelpSeen(): void {
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    // ignore: the dialog just shows again next time
  }
}
