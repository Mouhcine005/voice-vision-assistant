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
| 5 | Shortcuts work | Space, Esc, P, C, R, T, 1 to 5, L, N, H, J as listed in the README | partial | tested 1 to 5, L, P, H, J, N; Space, Esc, C, R and T not yet checked |
| 6 | Shortcuts ignored while typing | Type the letter P in the question field: it must not open the photo picker | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 7 | Dialogs | Open help and settings: focus moves inside, Tab stays inside, Esc closes, focus returns to the button | pass | keyboard-only test by the author, 2026-10-18, production preview |
| 8 | Screen reader: page structure | NVDA: page title, headings list (H key), landmarks (D key) make sense | todo | |
| 9 | Screen reader: controls | Mode cards announce name and selected state; mic button announces recording state | todo | |
| 10 | Screen reader: answers | A new answer is announced once (live region), not twice, not silently | todo | |
| 11 | Screen reader: errors | Turn the backend off and ask a question: the error is announced | todo | |
| 12 | Zoom 200 percent | Browser zoom 200 percent: nothing cut off, no sideways scrolling | todo | |
| 13 | Reflow 400 percent | Browser zoom 400 percent (narrow window): content stacks, still usable | todo | |
| 14 | Text contrast | Lighthouse contrast audit has no failures; check muted text and the disabled states | partial | Lighthouse contrast audit passed on the loaded page; muted text and disabled states not checked by hand yet |
| 15 | Reduced motion | Windows Settings, Accessibility, Visual effects, Animation effects off: mic animation and transitions calm down | todo | |
| 16 | Arabic and RTL | Press L until Arabic: layout flips, order of buttons makes sense, text is not cut off | todo | |
| 17 | Arabic with screen reader | NVDA with Arabic UI: labels read in Arabic, not as letters | todo | |
| 18 | No color-only meaning | Quality warnings and errors also have text, not only a red or yellow color | todo | |
| 19 | Touch targets on phone | Installed app on phone: buttons easy to hit, no tiny targets | todo | |
| 20 | Offline start | Airplane mode, open the installed app: it loads and shows a clear message, not a blank page | todo | |
