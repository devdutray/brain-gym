# 🧠 Brain Gym — Daily Problem Solving Trainer

A personal "brain gym" web app that serves you **one fresh real-world problem every day** to keep your
problem-solving, reasoning, estimation, and outside-the-box thinking skills sharp.

It mixes five challenge styles drawn from everyday life and engineering work:

| Style | What it trains |
|-------|----------------|
| 🌍 **Everyday** | Real-world logistics, planning, and trade-off decisions |
| 🧩 **Logic** | Deductive and lateral-thinking puzzles |
| 🏗️ **System Design** | Engineering / architecture mini-challenges |
| 📊 **Estimation** | Fermi "how many / how much" approximations |
| 💡 **Creative** | Brainstorming & innovative idea generation |

## Features

- **67-problem bank** across all five categories and three difficulty levels.
- **One problem per day**, deterministically rotated so you never repeat until the whole bank cycles.
- **Ramping difficulty** — early days serve difficulty-1 problems; harder problems unlock as you solve more.
- **Category practice** — pick any category (or "surprise me") for an on-demand practice problem, separate from your daily.
- **Streak tracking** — keep your daily-thinking habit alive.
- **Progressive hints** — reveal nudges one at a time only when you're stuck.
- **Write & save your own answer** before peeking at the sample approach.
- **Sample solution + a "thinking-skill" takeaway** for every problem.
- **Progress charts / stats view** — problems solved per week, streak sparkline, and breakdowns by category and difficulty (inline SVG, no build toolchain).
- **History** of everything you've solved.
- **Bonus problem** button for when one isn't enough.
- 100% local — your answers and progress stay on your machine (`data/progress.json`).

## Quick start (Windows)

```powershell
cd C:\Dev\brain-gym
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

Or just double-click **`run.bat`** — it sets up the virtual environment, installs Flask, and launches the app.

## How the daily rotation works

The full problem bank is shuffled once with a fixed seed, then today's problem is chosen by
`index = days_since_epoch % bank_size`. This guarantees a different problem every day with **no repeats**
until the entire bank has been seen.

### Ramping difficulty

Problems are tiered by the number you've already solved:

| Problems solved | Difficulty pool |
|-----------------|-----------------|
| 0 – 6 | Difficulty 1 only |
| 7 – 20 | Difficulty 1–2 |
| 21+ | All difficulties (1–3) |

Selection within each tier is still deterministic per day, visiting every eligible problem
before repeating. As you complete more problems the pool automatically expands.

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/today` | GET | Today's problem + progress state. Includes `difficultyTier`. |
| `/api/practice` | GET | Ad-hoc problem. Optional `?category=<cat>` query param (or `all`). |
| `/api/bonus` | GET | Random problem other than today's. |
| `/api/answer` | POST | Save answer `{problemId, answer}`. |
| `/api/complete` | POST | Mark today complete `{problemId}`. Returns updated streak + tier. |
| `/api/history` | GET | All solved problems with dates, categories, difficulties, and saved answers. |
| `/api/stats` | GET | Aggregated stats: streak, totals, by-category, by-difficulty, weekly counts, 30-day streak history. |

Valid `category` values: `everyday`, `logic`, `system-design`, `estimation`, `creative`.

## Running the tests

Install dependencies (includes pytest):

```powershell
pip install -r requirements.txt
```

Run all tests:

```powershell
pytest tests/
```

Or with verbose output:

```powershell
pytest tests/ -v
```

The test suite covers:

- **Rotation logic** — deterministic order, no duplicate IDs, full-cycle visits every problem, wraps correctly.
- **Difficulty tier** — all threshold boundaries.
- **`problem_for_date`** — difficulty filtering per tier, determinism across identical calls.
- **`compute_streak`** — empty history, single day, consecutive days, yesterday-alive, gaps, future dates, long streaks.
- **All API endpoints** — response shape, status codes, correct persistence behavior.

## Add your own problems

Open [data/problems.json](data/problems.json) and append an object following the same shape. The app
picks them up on restart. Growing the bank keeps the rotation fresh.

```json
{
  "id": "xx-NN",
  "category": "everyday",
  "difficulty": 2,
  "title": "Your problem title",
  "prompt": "The full problem statement…",
  "hints": ["First nudge", "Second nudge", "Third nudge"],
  "approach": "A thorough sample approach…",
  "reflection": "The thinking-skill takeaway."
}
```

## Project structure

```
brain-gym/
├── app.py               # Flask backend + daily rotation + progress API
├── requirements.txt     # Flask + pytest
├── run.bat              # One-click setup + launch (Windows)
├── data/
│   ├── problems.json    # The problem bank (67 problems, editable)
│   └── progress.json    # Your streak / answers (auto-created, git-ignored)
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
└── tests/
    └── test_app.py      # pytest suite (49 tests)
```

