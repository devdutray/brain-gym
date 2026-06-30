"""Brain Gym - a daily problem-solving trainer.

A small Flask app that serves one rotating problem per day from a curated bank,
tracks streaks and your saved answers, and reveals hints/solutions on demand.
All state is local (data/progress.json).
"""

import json
import random
from collections import defaultdict
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

VALID_CATEGORIES = {"everyday", "logic", "system-design", "estimation", "creative"}

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


def difficulty_tier(total_solved):
    """Return the maximum difficulty level unlocked based on problems solved.

    Days 0–6  (first week)  → difficulty 1 only
    Days 7–20 (second+third week) → difficulty 1–2
    Day 21+   (beyond)      → all difficulties (1–3)
    """
    if total_solved < 7:
        return 1
    if total_solved < 21:
        return 2
    return 3


def problem_for_date(problems, the_day, total_solved=0):
    """Pick the problem for a given date.

    Difficulty scales with the user's total solved count so beginners start with
    easier problems and harder ones unlock gradually.  Within each tier the
    rotation is deterministic and visits every eligible problem before repeating.
    """
    max_diff = difficulty_tier(total_solved)
    pool = [p for p in problems if p["difficulty"] <= max_diff]
    if not pool:
        pool = problems
    order = rotation_order(pool)
    days = (the_day - EPOCH).days
    idx = days % len(order)
    target_id = order[idx]
    return next(p for p in pool if p["id"] == target_id)


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
    progress = load_progress()
    total_solved = len(progress["completed"])
    problem = problem_for_date(problems, today, total_solved)
    today_key = today.isoformat()

    return jsonify(
        {
            "problem": problem,
            "date": today_key,
            "completedToday": today_key in progress["completed"],
            "savedAnswer": progress["answers"].get(problem["id"], ""),
            "streak": compute_streak(list(progress["completed"].keys())),
            "totalSolved": total_solved,
            "bankSize": len(problems),
            "difficultyTier": difficulty_tier(total_solved),
        }
    )


@app.route("/api/bonus")
def api_bonus():
    """Return a random problem that is not today's (a bonus challenge)."""
    problems = load_problems()
    progress = load_progress()
    total_solved = len(progress["completed"])
    today_problem = problem_for_date(problems, date.today(), total_solved)
    pool = [p for p in problems if p["id"] != today_problem["id"]] or problems
    return jsonify({"problem": random.choice(pool)})


@app.route("/api/practice")
def api_practice():
    """Return a problem for ad-hoc practice, optionally filtered by category.

    Query params:
      category — one of everyday | logic | system-design | estimation | creative
                 (omit or pass 'all' to pick from the whole bank)

    The returned problem is chosen randomly from the filtered pool and will
    never be today's daily problem (unless the pool has only one entry).
    """
    problems = load_problems()
    category = request.args.get("category", "").strip().lower()

    if category and category != "all":
        if category not in VALID_CATEGORIES:
            return jsonify({"error": f"Unknown category '{category}'"}), 400
        pool = [p for p in problems if p["category"] == category]
    else:
        pool = list(problems)

    if not pool:
        return jsonify({"error": "No problems found for that category"}), 404

    # Try to exclude today's daily problem so it stays distinct.
    progress = load_progress()
    total_solved = len(progress["completed"])
    today_problem = problem_for_date(problems, date.today(), total_solved)
    filtered = [p for p in pool if p["id"] != today_problem["id"]]
    chosen_pool = filtered if filtered else pool

    return jsonify({"problem": random.choice(chosen_pool)})


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
    total_solved = len(progress["completed"])
    return jsonify(
        {
            "ok": True,
            "streak": compute_streak(list(progress["completed"].keys())),
            "totalSolved": total_solved,
            "difficultyTier": difficulty_tier(total_solved),
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
                "difficulty": problem["difficulty"] if problem else 0,
                "answer": progress["answers"].get(pid, ""),
            }
        )
    return jsonify({"history": items})


@app.route("/api/stats")
def api_stats():
    """Return aggregated progress statistics for the charts view.

    Response shape:
      streak          — current streak
      totalSolved     — total problems completed
      bankSize        — total problems in the bank
      difficultyTier  — current difficulty tier (1–3)
      byCategory      — {category: count}
      byDifficulty    — {1: count, 2: count, 3: count}
      byWeek          — [{week: "YYYY-Www", count: N}, …] (last 12 weeks)
      streakHistory   — [{date: "YYYY-MM-DD", streak: N}, …] (last 30 days)
    """
    problems = load_problems()
    by_id = {p["id"]: p for p in problems}
    progress = load_progress()
    completed = progress["completed"]  # {date_str: problem_id}

    total_solved = len(completed)
    streak = compute_streak(list(completed.keys()))
    tier = difficulty_tier(total_solved)

    by_category: dict = defaultdict(int)
    by_difficulty: dict = defaultdict(int)
    for pid in completed.values():
        prob = by_id.get(pid)
        if prob:
            by_category[prob["category"]] += 1
            by_difficulty[str(prob["difficulty"])] += 1

    # Problems solved per ISO week (last 12 weeks)
    today = date.today()
    week_counts: dict = defaultdict(int)
    for day_str in completed:
        d = datetime.strptime(day_str, "%Y-%m-%d").date()
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        week_counts[week_key] += 1

    # Build a sorted list covering the last 12 weeks (fill zeros for missing weeks)
    by_week = []
    for i in range(11, -1, -1):
        d = today - timedelta(weeks=i)
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        by_week.append({"week": week_key, "count": week_counts.get(week_key, 0)})

    # Streak length for each of the last 30 days (rolling streak up to that day)
    streak_history = []
    completed_set = {
        datetime.strptime(d, "%Y-%m-%d").date() for d in completed
    }
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.isoformat()
        # Compute streak ending on day d
        if d not in completed_set:
            s = 0
        else:
            cursor = d
            s = 0
            while cursor in completed_set:
                s += 1
                cursor -= timedelta(days=1)
        streak_history.append({"date": day_str, "streak": s})

    return jsonify(
        {
            "streak": streak,
            "totalSolved": total_solved,
            "bankSize": len(problems),
            "difficultyTier": tier,
            "byCategory": dict(by_category),
            "byDifficulty": dict(by_difficulty),
            "byWeek": by_week,
            "streakHistory": streak_history,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
