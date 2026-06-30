# Brain Gym — Development Plan & Roadmap

> A personal daily problem-solving trainer. This document is the living plan for how the app is
> built, what's in progress, and where it's headed. Keep it updated as work lands.

- **Repository:** https://github.com/devdutray/brain-gym (public)
- **Stack:** Python 3 · Flask · vanilla HTML/CSS/JS
- **Run locally:** `run.bat` (Windows) or `python -m venv .venv` → activate → `pip install -r requirements.txt` → `python app.py` → http://127.0.0.1:5000

---

## 1. What the app is

Brain Gym serves **one rotating problem per day** to sharpen everyday problem-solving. Problems span five
styles — 🌍 everyday logistics, 🧩 logic/lateral puzzles, 🏗️ system design, 📊 estimation (Fermi), and
💡 creative brainstorming. Each problem ships with **progressive hints**, a **sample approach**, and a
**"thinking-skill" takeaway** so the user learns the technique, not just the answer. Streaks, history, and
saved answers keep the daily habit going.

## 2. Architecture

```
Browser (static/app.js + templates/index.html)
   │  fetch JSON
   ▼
Flask backend (app.py)  ──reads──►  data/problems.json  (the problem bank)
   │                    ──r/w────►  data/progress.json  (streak/answers, git-ignored)
   ▼
JSON responses → rendered UI
```

- **Daily rotation:** `index = days_since_epoch % bank_size` over a **fixed-seed shuffle** of all problem
  IDs. Deterministic, stateless, and guarantees **no repeats** until the full bank cycles.
- **Streak:** consecutive completed days counted backward from today/yesterday.
- **Persistence:** local JSON file (single user). Being migrated toward client-side storage for hosting.

## 3. Status snapshot

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Core app built, smoke-tested, pushed | ✅ Done |
| 1 | More problems · ramping difficulty · category filter · progress charts · backend tests | 🔄 PR #2 |
| 2 | Free-host deploy · mobile UI · persistent progress (localStorage) | 🔄 PR #4 |
| 3 | Review & merge PRs (#2 then #4), resolve conflicts | ⏭️ Planned |
| 4 | Render go-live (phone access) | ⏭️ Planned |
| 5 | PWA "add to home screen" | ⏸️ Deferred |
| 6 | Hardening: module split · atomic writes · input limits · a11y · CI | 🔮 Future |

## 4. Backlog / improvement ideas

**Reliability**
- Make progress writes atomic (temp file + `os.replace`) to avoid read-modify-write races.
- Cache the problem bank + rotation order at startup instead of reading on every request.

**Security**
- Cap saved-answer length and request body size so `progress.json` can't grow unbounded.
- Never run with `debug=True` in production; gate via environment.

**Maintainability**
- Split `app.py` into `storage`, `rotation`, and route modules (single responsibility).
- Add pytest coverage for rotation (no repeats across a cycle) and streak edge cases.

**UX / accessibility**
- Add ARIA labels, keyboard focus handling, and `Esc`-to-close on the history drawer.
- Friendly error toasts with retry instead of replacing the title text.

**Features (nice-to-have)**
- Daily reminder / notification.
- Tagging favorite problems; revisit-missed mode.
- Shareable "problem of the day" link.

## 5. Conventions

- **Adding a problem:** append an object to `data/problems.json` with a unique `id` and all required fields
  (see `.github/copilot-instructions.md` for the exact schema). No code change needed.
- **Don't break the rotation contract:** changes to seed/epoch logic must preserve determinism and the
  no-repeat-until-cycle guarantee.
- **Keep `data/progress.json` git-ignored** — it's personal state, not source.

## 6. Working with AI agents

Enhancements are delegated to the GitHub Copilot coding agent via GitHub issues assigned to Copilot, which
opens PRs for review. See `.github/copilot-instructions.md` for the repository guidance agents should follow.
