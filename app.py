"""Brain Gym - a daily problem-solving trainer.

A small Flask app that serves one rotating problem per day from a curated bank,
tracks streaks and your saved answers, and reveals hints/solutions on demand.
All state is local (data/progress.json).
"""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROBLEMS_FILE = DATA_DIR / "problems.json"
PROGRESS_FILE = DATA_DIR / "progress.json"

# Fixed seed so the shuffled rotation order is stable across restarts.
ROTATION_SEED = 20240601
EPOCH = date(2024, 1, 1)

app = Flask(__name__)


def load_problems():
    """Load the problem bank from disk."""
    with PROBLEMS_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def rotation_order(problems):
    """Return problem ids shuffled once with a fixed seed.

    The deterministic shuffle gives a stable, repeatable daily sequence that
    visits every problem before any repeats.
    """
    ids = [p["id"] for p in problems]
    rng = random.Random(ROTATION_SEED)
    rng.shuffle(ids)
    return ids


def problem_for_date(problems, the_day):
    """Pick the problem for a given date via days-since-epoch modulo bank size."""
    order = rotation_order(problems)
    days = (the_day - EPOCH).days
    idx = days % len(order)
    target_id = order[idx]
    return next(p for p in problems if p["id"] == target_id)


def load_progress():
    """Load saved progress, returning a default structure if none exists."""
    if PROGRESS_FILE.exists():
        with PROGRESS_FILE.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"completed": {}, "answers": {}}


def save_progress(progress):
    """Persist progress to disk atomically enough for a local single-user app."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with PROGRESS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(progress, fh, indent=2)


def compute_streak(completed_dates):
    """Compute the current consecutive-day streak ending today or yesterday."""
    if not completed_dates:
        return 0
    days = {datetime.strptime(d, "%Y-%m-%d").date() for d in completed_dates}
    today = date.today()
    # A streak is "alive" if today or yesterday was completed.
    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/today")
def api_today():
    """Return today's problem plus the user's progress state."""
    problems = load_problems()
    today = date.today()
    problem = problem_for_date(problems, today)
    progress = load_progress()
    today_key = today.isoformat()

    return jsonify(
        {
            "problem": problem,
            "date": today_key,
            "completedToday": today_key in progress["completed"],
            "savedAnswer": progress["answers"].get(problem["id"], ""),
            "streak": compute_streak(list(progress["completed"].keys())),
            "totalSolved": len(progress["completed"]),
            "bankSize": len(problems),
        }
    )


@app.route("/api/bonus")
def api_bonus():
    """Return a random problem that is not today's (a bonus challenge)."""
    problems = load_problems()
    today_problem = problem_for_date(problems, date.today())
    pool = [p for p in problems if p["id"] != today_problem["id"]] or problems
    return jsonify({"problem": random.choice(pool)})


@app.route("/api/answer", methods=["POST"])
def api_answer():
    """Save the user's written answer for a problem."""
    payload = request.get_json(silent=True) or {}
    problem_id = payload.get("problemId")
    answer = payload.get("answer", "")
    if not problem_id:
        return jsonify({"error": "problemId is required"}), 400
    progress = load_progress()
    progress["answers"][problem_id] = answer
    save_progress(progress)
    return jsonify({"ok": True})


@app.route("/api/complete", methods=["POST"])
def api_complete():
    """Mark today's problem as completed and update the streak."""
    progress = load_progress()
    today_key = date.today().isoformat()
    payload = request.get_json(silent=True) or {}
    progress["completed"][today_key] = payload.get("problemId", "")
    save_progress(progress)
    return jsonify(
        {
            "ok": True,
            "streak": compute_streak(list(progress["completed"].keys())),
            "totalSolved": len(progress["completed"]),
        }
    )


@app.route("/api/history")
def api_history():
    """Return the list of solved problems with the dates and saved answers."""
    problems = load_problems()
    by_id = {p["id"]: p for p in problems}
    progress = load_progress()
    items = []
    for day, pid in sorted(progress["completed"].items(), reverse=True):
        problem = by_id.get(pid)
        items.append(
            {
                "date": day,
                "problemId": pid,
                "title": problem["title"] if problem else "(unknown)",
                "category": problem["category"] if problem else "",
                "answer": progress["answers"].get(pid, ""),
            }
        )
    return jsonify({"history": items})


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
