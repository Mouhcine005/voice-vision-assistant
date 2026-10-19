# Demo plan

Demo machine: the author's laptop, Chrome, production build (cd frontend, npm run build, npm run preview, open http://localhost:4173), backend running (cd backend, activate .venv, uvicorn app.main:app).

## Day before
- Check the Gemini quota in AI Studio (500 requests per day for gemini-3.5-flash-lite; a voice turn costs 2). Do not run benchmarks or long tests on the demo day.
- Run python -m pytest -q in backend (expect 112 passed).
- backend/.env has GEMINI_API_KEY and GEMINI_MODEL=gemini-3.5-flash-lite. Restart the backend after any edit.
- Put 4 photos in a folder on the desktop: a room or street scene, a printed text (receipt or leaflet), a product box (medicine or food), a banknote.
- Make a blurry photo for the quality warning.
- Record a 2-minute screen video of a clean run (backup).
- Windows default microphone set, microphone allowed for localhost in Chrome, volume checked, other tabs and notifications closed, laptop charged and plugged in.

## Script (about 6 minutes)
1. Problem in one sentence: describing photos and reading labels for people who cannot see them.
2. Describe: choose the room photo, press Space, ask by voice what is in front of you, let the answer play.
3. Read text: press 2, send the printed text, ask to read it.
4. Product: press 3, send the medicine box. Point out that it says what it cannot see and to check with a pharmacist.
5. Quality check: send the blurry photo. The assistant asks for a retake instead of guessing.
6. Keyboard and accessibility: press H for help, L to switch to Arabic (layout flips), show Tab focus. Mention Lighthouse 100 and the checklist in docs/accessibility-checklist.md.
7. Jury mode: press J. Read the numbers live: text turns and voice turns, and the perceived wait. Say plainly that voice turns are slower because of speech to text.
8. Optional if time: install as an app, or show the offline shell with the server stopped.

## If something fails
- No internet: play the backup video; show the offline shell and the error banner.
- Quota or model errors: the app falls back to gemini-3.1-flash-lite automatically; if both fail, play the video.
- Microphone problem: press T and type the question instead.
- Backend not responding: restart uvicorn in the backend window (about 5 seconds), reload the page.
- Voice slow: point at the perceived wait tile in Jury mode and explain it.

## Questions the jury may ask
- How accurate is it? Answer only with what docs and the results files really contain. The benchmark harness exists; do not quote the web image pilot as accuracy.
- Why is voice slow? Gemini speech to text takes several seconds on the free tier; the numbers are in Jury mode; Whisper small is the fallback.
- Privacy? Photos go to Gemini on the free tier, which may use data to improve products; do not use private photos.
- Screen reader testing? One NVDA session with Chrome by the author; results in docs/accessibility-checklist.md; limitations listed there.
- Does it work offline? Only the app shell; recognition needs internet.
- Why not a mobile app? Out of scope for the project; the web app is installable as a PWA.
