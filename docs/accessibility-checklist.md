# Accessibility checklist

Tested on: (date, browser, screen reader, OS)
Build tested: production build (npm run build, then npm run preview), because the service worker only exists there.

Result column: pass, fail or n/a. Put what you saw in Notes, especially for fails.

| # | Check | How | Result | Notes |
|---|---|---|---|---|
| 1 | Lighthouse accessibility score | Chrome DevTools, Lighthouse tab, Accessibility only, run for Desktop and Mobile | pass | 100/100 on Desktop and Mobile (Lighthouse, 2026-10-18, production preview) |
| 2 | Keyboard only: every control reachable | Put the mouse away. Tab and Shift+Tab through the whole page | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 3 | Visible focus on every control | Look for the yellow outline while tabbing | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 4 | Skip link | First Tab on page load shows a skip link; Enter jumps to the main content | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 5 | Shortcuts work | Space, Esc, P, C, R, T, 1 to 5, L, N, H, J as listed in the README | pass | tested 1 to 5, L, P, H, J, N, T, Space, Esc and R on desktop (author test, 2026-10-18); C opens the file picker there (capture input, so camera on phones, not tested on a phone) |
| 6 | Shortcuts ignored while typing | Type the letter P in the question field: it must not open the photo picker | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 7 | Dialogs | Open help and settings: focus moves inside, Tab stays inside, Esc closes, focus returns to the button | pass | keyboard test 2026-10-18; NVDA log 2026-10-19: Help is announced as a dialog with its description, focus lands inside, focus returns to the Help button on close; Settings dialog not yet checked with NVDA |
| 8 | Screen reader: page structure | NVDA: page title, headings list (H key), landmarks (D key) make sense | pass | NVDA Speech Viewer log, 2026-10-19, Chrome on the dev server (localhost:5173): title, skip link, banner, main landmark and h1/h2 structure announced correctly |
| 9 | Screen reader: controls | Mode cards announce name and selected state; mic button announces recording state | partial | NVDA 2026-10-19: names, roles and states read for language, Settings, Help, Jury, the 5 mode radios, photo buttons and mic button; Jury panel read as tables with headers and a chart text alternative. Photo buttons read 'No file chosen' after a pick because the input resets (minor). Mic recording state, mode change announcements and the Settings dialog were not itemized; NVDA was then removed, so not re-tested |
| 10 | Screen reader: answers | A new answer is announced once (live region), not twice, not silently | partial | Answer announced once after 'Thinking...' in the NVDA Speech Viewer log, 2026-10-19. Not determined: whether the app's own voice and a screen reader overlap (NVDA removed before this was tested) |
| 11 | Screen reader: errors | Turn the backend off and ask a question: the error is announced | pass | Backend stopped: error announced as an alert ('The vision service is not answering right now. Please try again.'); text appears twice in the Speech Viewer, to confirm by ear |
| 12 | Zoom 200 percent | Browser zoom 200 percent: nothing cut off, no sideways scrolling | pass | author test, 2026-10-18, production preview on desktop Chrome |
| 13 | Reflow 400 percent | Browser zoom 400 percent (narrow window): content stacks, still usable | pass | author test, 2026-10-18, production preview on desktop Chrome |
| 14 | Text contrast | Lighthouse contrast audit has no failures; check muted text and the disabled states | partial | Lighthouse contrast audit passed on the loaded page; muted text and disabled states not checked by hand yet |
| 15 | Reduced motion | Windows Settings, Accessibility, Visual effects, Animation effects off: mic animation and transitions calm down | pass | author test, 2026-10-18, Windows animation effects off |
| 16 | Arabic and RTL | Press L until Arabic: layout flips, order of buttons makes sense, text is not cut off | pass | author test, 2026-10-18, production preview on desktop Chrome; layout flips to right-to-left, nothing cut off |
| 17 | Arabic with screen reader | NVDA with Arabic UI: labels read in Arabic, not as letters | not tested | NVDA removed; its Arabic voice support was never verified. Arabic layout and right-to-left order were checked visually (#16) |
| 18 | No color-only meaning | Quality warnings and errors also have text, not only a red or yellow color | todo | |
| 19 | Touch targets on phone | Installed app on phone: buttons easy to hit, no tiny targets | not tested | demo is on a laptop; the app has not been tried on a phone |
| 20 | Offline start | Airplane mode, open the installed app: it loads and shows a clear message, not a blank page | todo | |
