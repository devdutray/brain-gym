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

- **One problem per day**, deterministically rotated so you never repeat until the whole bank cycles.
- **Streak tracking** — keep your daily-thinking habit alive.
- **Progressive hints** — reveal nudges one at a time only when you're stuck.
- **Write & save your own answer** before peeking at the sample approach.
- **Sample solution + a "thinking-skill" takeaway** for every problem.
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

## Add your own problems

Open [data/problems.json](data/problems.json) and append an object following the same shape. The app
picks them up on restart. Growing the bank keeps the rotation fresh.

## Project structure

```
brain-gym/
├── app.py               # Flask backend + daily rotation + progress API
├── requirements.txt
├── run.bat              # One-click setup + launch (Windows)
├── data/
│   ├── problems.json    # The problem bank (editable)
│   └── progress.json    # Your streak / answers (auto-created, git-ignored)
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```
