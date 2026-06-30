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
- 100% local — your answers and progress stay in your browser (`localStorage`), so they work on any host.

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
├── Procfile             # Heroku / Railway / Fly.io process declaration
├── render.yaml          # Render one-click deploy config
├── Dockerfile           # Container image for any Docker host
├── run.bat              # One-click setup + launch (Windows)
├── data/
│   ├── problems.json    # The problem bank (editable)
│   └── progress.json    # Local server-side progress (auto-created, git-ignored)
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

## Deploy it (use from your phone)

Your streak and answers are saved in your **browser's `localStorage`**, so they survive on any
free host that resets the filesystem between deploys.

### Render (recommended — free, GitHub-integrated)

1. Fork or push this repo to your GitHub account.
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect your GitHub repo.
4. Render auto-detects `render.yaml` — just click **Create Web Service**.
5. Wait ~2 minutes for the first deploy; Render gives you a URL like
   `https://brain-gym-xxxx.onrender.com`.
6. Open that URL on your phone — bookmark it to your home screen for an
   app-like experience.

> **Note:** On Render's free plan the service sleeps after 15 min of inactivity
> and takes ~30 s to wake up. Your progress is safe because it lives in
> `localStorage`, not on the server.

### Railway / Fly.io / Heroku

These platforms use the included `Procfile` (`web: gunicorn app:app --bind 0.0.0.0:$PORT`):

1. Connect your GitHub repo in the platform dashboard.
2. The platform reads `Procfile` automatically.
3. No extra environment variables are required (defaults work).

### Docker (self-hosted / any VPS)

```bash
docker build -t brain-gym .
docker run -p 5000:5000 brain-gym
```

Then open `http://localhost:5000`.
