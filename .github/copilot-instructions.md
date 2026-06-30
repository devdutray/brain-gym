# Brain Gym — Repository Instructions for AI Agents

These instructions tell GitHub Copilot (and any AI coding agent) how this project is built and the
conventions to follow when making changes. Read this before editing.

## What this project is

Brain Gym is a small, self-contained **daily problem-solving trainer**. It serves one rotating problem per
day from a curated bank, with progressive hints, a sample approach, a "thinking-skill" takeaway, plus streak
tracking, saved answers, and history. The goal is to keep the user's reasoning, estimation, and creative
problem-solving sharp.

## Tech stack

- **Backend:** Python 3 + **Flask** (single file: `app.py`).
- **Frontend:** plain **HTML/CSS/JavaScript** (no framework, no build step).
- **Data:** JSON files on disk. No database.
- **Run locally:** `python app.py` (or `run.bat` on Windows) → http://127.0.0.1:5000.

Keep the stack lightweight. Do **not** introduce a frontend framework, a build toolchain, or heavy
dependencies unless a task explicitly requires it and justifies it.

## Project structure

```
brain-gym/
├── app.py                 # Flask backend: rotation logic, streak, JSON API
├── requirements.txt       # Pinned Python deps
├── run.bat                # One-click setup + launch (Windows)
├── docs/PLAN.md           # Development plan / roadmap
├── data/
│   ├── problems.json      # The problem bank (source of truth, editable)
│   └── progress.json      # User streak/answers — GIT-IGNORED, never commit
├── templates/index.html   # Page markup
└── static/
    ├── style.css          # Dark theme, CSS variables, responsive @media rules
    └── app.js             # Fetches the API, manages reveals + UI state
```

## How the core logic works (do not break these contracts)

- **Daily rotation:** the day's problem is `rotation_order(problems)[days_since_epoch % bank_size]`, where
  `rotation_order` shuffles all problem IDs **once with a fixed seed** (`ROTATION_SEED`). This is
  **deterministic** and guarantees **no repeats until the entire bank has cycled**. Any change to rotation
  must preserve determinism and the no-repeat guarantee.
- **Streak:** `compute_streak` counts consecutive completed days backward from today (or yesterday, so the
  streak stays "alive" until a full day is missed).
- **Persistence:** `load_progress` / `save_progress` read/write `data/progress.json` as
  `{ "completed": {date: problemId}, "answers": {problemId: text} }`.

## JSON API (keep these stable; migrate gracefully if you must change them)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/today` | Today's problem + `{ streak, totalSolved, savedAnswer, completedToday, bankSize }` |
| GET | `/api/bonus` | A random non-today problem |
| POST | `/api/answer` | Body `{ problemId, answer }` — save the user's written answer |
| POST | `/api/complete` | Body `{ problemId }` — mark today solved, recompute streak |
| GET | `/api/history` | List of solved problems with dates + saved answers |

## Problem bank schema (`data/problems.json`)

A JSON array of objects. Every problem **must** include all fields:

```json
{
  "id": "ev-01",                       // unique, short, lowercase; <cat-prefix>-<n>
  "category": "everyday",              // one of: everyday | logic | system-design | estimation | creative
  "difficulty": 1,                     // integer 1 (easy) .. 3 (hard)
  "title": "The Overlapping Errands",
  "prompt": "A clear, real-world problem statement the user solves.",
  "hints": ["nudge 1", "nudge 2", "nudge 3"],   // 2-3 progressive hints, least to most revealing
  "approach": "A sample way to reason through it (not the only answer).",
  "reflection": "The transferable thinking-skill takeaway."
}
```

Rules when adding problems:
- `id` must be **unique** across the whole bank.
- Spread additions **evenly across the five categories**.
- Match the existing **tone and quality**: real, relatable prompts; hints that teach a method; an `approach`
  that explains the reasoning; a `reflection` that names the underlying thinking skill.
- Adding problems requires **no code change** — the bank is data-driven.

## Coding conventions

- Keep functions small and single-purpose; add a short docstring to backend functions.
- Backend: prefer standard library + Flask. Pin any new dependency in `requirements.txt`.
- Frontend: keep the thin `api()` fetch helper + a small `state` object pattern in `app.js`; separate API
  calls from DOM rendering. Use `textContent` (not `innerHTML`) for user/data-derived strings.
- Preserve the existing dark theme and the responsive `@media` rules in `style.css`.

## Guardrails (important)

- **Never commit `data/progress.json`** — it's personal state and is git-ignored.
- **Never run `debug=True` in production** — gate Flask debug/host/port via environment
  (`PORT`, default 5000; bind `0.0.0.0` only for hosted deployments).
- **Validate/limit input:** cap saved-answer length and request body size so `progress.json` can't grow
  unbounded.
- **Don't break existing endpoints or the `progress.json` shape** — migrate gracefully if a change is needed.
- Free-tier hosting has an **ephemeral filesystem**; for deployed builds, persist user progress on the client
  (localStorage) or a persistent store, not a server-side file.

## Testing

- Use **pytest**. Prioritize tests for the **rotation logic** (deterministic; no repeats across a full cycle)
  and **streak computation** (gaps, today-vs-yesterday edges), plus the API endpoints via Flask's test client.
- Document how to run tests in the README when tests are added.

## Quality bar for changes

Keep changes well-scoped and reviewable. Update `README.md` and `docs/PLAN.md` when you add features,
endpoints, or developer workflows. Don't over-engineer — this is a focused personal app.
