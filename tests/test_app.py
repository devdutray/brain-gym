"""Tests for Brain Gym backend logic and API endpoints.

Run with:
    pytest tests/
"""

import json
import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Import helpers from app.py
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as bgapp
from app import (
    rotation_order,
    problem_for_date,
    compute_streak,
    difficulty_tier,
    EPOCH,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PROBLEMS = [
    {"id": f"t-{i:02d}", "category": "logic", "difficulty": ((i % 3) + 1), "title": f"Problem {i}",
     "prompt": "p", "hints": [], "approach": "a", "reflection": "r"}
    for i in range(1, 13)
]
"""12 sample problems spread across difficulty 1, 2, 3."""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client with isolated data directory."""
    monkeypatch.setattr(bgapp, "DATA_DIR", tmp_path)
    monkeypatch.setattr(bgapp, "PROGRESS_FILE", tmp_path / "progress.json")
    monkeypatch.setattr(bgapp, "PROBLEMS_FILE", tmp_path / "problems.json")

    # Write sample problems to the temp dir
    (tmp_path / "problems.json").write_text(
        json.dumps(SAMPLE_PROBLEMS), encoding="utf-8"
    )

    bgapp.app.config["TESTING"] = True
    with bgapp.app.test_client() as c:
        yield c


def make_progress(tmp_path, completed: dict | None = None, answers: dict | None = None):
    """Write a progress.json to the tmp data dir and return the path."""
    progress = {"completed": completed or {}, "answers": answers or {}}
    p = tmp_path / "progress.json"
    p.write_text(json.dumps(progress), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# rotation_order — deterministic, full-cycle, no repeats
# ---------------------------------------------------------------------------

class TestRotationOrder:
    def test_deterministic(self):
        order1 = rotation_order(SAMPLE_PROBLEMS)
        order2 = rotation_order(SAMPLE_PROBLEMS)
        assert order1 == order2

    def test_contains_all_ids(self):
        order = rotation_order(SAMPLE_PROBLEMS)
        assert set(order) == {p["id"] for p in SAMPLE_PROBLEMS}

    def test_length_matches_bank(self):
        order = rotation_order(SAMPLE_PROBLEMS)
        assert len(order) == len(SAMPLE_PROBLEMS)

    def test_no_repeats_in_one_cycle(self):
        order = rotation_order(SAMPLE_PROBLEMS)
        assert len(order) == len(set(order)), "Duplicate IDs in rotation order"

    def test_full_cycle_visits_every_problem(self):
        """Iterating len(bank) days starting at EPOCH covers every problem exactly once."""
        seen = set()
        n = len(SAMPLE_PROBLEMS)
        for offset in range(n):
            day = EPOCH + timedelta(days=offset)
            p = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=99)
            seen.add(p["id"])
        assert len(seen) == n

    def test_cycle_wraps_and_repeats(self):
        """Day N and day 0 should return the same problem (modulo bank size)."""
        n = len(SAMPLE_PROBLEMS)
        p0 = problem_for_date(SAMPLE_PROBLEMS, EPOCH, total_solved=99)
        pN = problem_for_date(SAMPLE_PROBLEMS, EPOCH + timedelta(days=n), total_solved=99)
        assert p0["id"] == pN["id"]


# ---------------------------------------------------------------------------
# difficulty_tier — thresholds
# ---------------------------------------------------------------------------

class TestDifficultyTier:
    @pytest.mark.parametrize("solved,expected", [
        (0, 1), (1, 1), (6, 1),
        (7, 2), (10, 2), (20, 2),
        (21, 3), (50, 3), (999, 3),
    ])
    def test_tiers(self, solved, expected):
        assert difficulty_tier(solved) == expected


# ---------------------------------------------------------------------------
# problem_for_date — difficulty filtering
# ---------------------------------------------------------------------------

class TestProblemForDate:
    def test_tier1_only_difficulty1(self):
        """With total_solved < 7 only difficulty-1 problems should appear."""
        seen_difficulties = set()
        n = len([p for p in SAMPLE_PROBLEMS if p["difficulty"] == 1])
        for offset in range(n):
            day = EPOCH + timedelta(days=offset)
            p = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=0)
            seen_difficulties.add(p["difficulty"])
        assert seen_difficulties == {1}

    def test_tier2_max_difficulty2(self):
        """With 7 <= total_solved < 21 problems should have difficulty <= 2."""
        pool = [p for p in SAMPLE_PROBLEMS if p["difficulty"] <= 2]
        n = len(pool)
        for offset in range(n):
            day = EPOCH + timedelta(days=offset)
            p = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=7)
            assert p["difficulty"] <= 2

    def test_tier3_all_difficulties(self):
        """With total_solved >= 21 all difficulty levels appear over a full cycle."""
        seen = set()
        n = len(SAMPLE_PROBLEMS)
        for offset in range(n):
            day = EPOCH + timedelta(days=offset)
            p = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=21)
            seen.add(p["difficulty"])
        assert seen == {1, 2, 3}

    def test_deterministic_same_day_same_result(self):
        day = date(2025, 3, 15)
        p1 = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=5)
        p2 = problem_for_date(SAMPLE_PROBLEMS, day, total_solved=5)
        assert p1["id"] == p2["id"]


# ---------------------------------------------------------------------------
# compute_streak
# ---------------------------------------------------------------------------

class TestComputeStreak:
    def _today(self):
        return date.today()

    def test_empty_history_returns_zero(self):
        assert compute_streak([]) == 0

    def test_only_today_gives_streak_one(self):
        today = self._today().isoformat()
        assert compute_streak([today]) == 1

    def test_consecutive_days_ending_today(self):
        today = self._today()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(5)]
        assert compute_streak(dates) == 5

    def test_consecutive_days_ending_yesterday(self):
        """Streak should still be alive if yesterday was the last solve."""
        today = self._today()
        yesterday = today - timedelta(days=1)
        dates = [(yesterday - timedelta(days=i)).isoformat() for i in range(3)]
        assert compute_streak(dates) == 3

    def test_gap_breaks_streak(self):
        """A missing day between solves resets the streak to zero if the gap includes yesterday."""
        today = self._today()
        # Solved 5 days ago and 3 days ago — no solve yesterday or today
        dates = [
            (today - timedelta(days=5)).isoformat(),
            (today - timedelta(days=3)).isoformat(),
        ]
        assert compute_streak(dates) == 0

    def test_streak_does_not_count_future_dates(self):
        """Dates in the future should not affect the streak."""
        today = self._today()
        future = (today + timedelta(days=1)).isoformat()
        assert compute_streak([future]) == 0

    def test_non_consecutive_old_dates_give_zero(self):
        old = [(date(2020, 1, i)).isoformat() for i in range(1, 6)]
        assert compute_streak(old) == 0

    def test_long_streak_counted_correctly(self):
        today = self._today()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(30)]
        assert compute_streak(dates) == 30


# ---------------------------------------------------------------------------
# API: /api/today
# ---------------------------------------------------------------------------

class TestApiToday:
    def test_returns_200(self, client):
        res = client.get("/api/today")
        assert res.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/today").get_json()
        assert "problem" in data
        assert "date" in data
        assert "streak" in data
        assert "totalSolved" in data
        assert "bankSize" in data
        assert "difficultyTier" in data
        assert "completedToday" in data

    def test_completed_today_flag(self, client, tmp_path):
        today = date.today().isoformat()
        make_progress(tmp_path, completed={today: "t-01"})
        data = client.get("/api/today").get_json()
        assert data["completedToday"] is True

    def test_not_completed_today_flag(self, client, tmp_path):
        make_progress(tmp_path, completed={})
        data = client.get("/api/today").get_json()
        assert data["completedToday"] is False

    def test_difficulty_tier_in_response(self, client):
        data = client.get("/api/today").get_json()
        assert data["difficultyTier"] in (1, 2, 3)


# ---------------------------------------------------------------------------
# API: /api/practice
# ---------------------------------------------------------------------------

class TestApiPractice:
    def test_returns_problem(self, client):
        data = client.get("/api/practice").get_json()
        assert "problem" in data
        assert "id" in data["problem"]

    def test_category_filter_logic(self, client, tmp_path):
        # All sample problems have category "logic"
        data = client.get("/api/practice?category=logic").get_json()
        assert data["problem"]["category"] == "logic"

    def test_invalid_category_returns_400(self, client):
        res = client.get("/api/practice?category=bogus")
        assert res.status_code == 400

    def test_all_category_returns_problem(self, client):
        data = client.get("/api/practice?category=all").get_json()
        assert "problem" in data


# ---------------------------------------------------------------------------
# API: /api/answer
# ---------------------------------------------------------------------------

class TestApiAnswer:
    def test_saves_answer(self, client, tmp_path):
        res = client.post(
            "/api/answer",
            json={"problemId": "t-01", "answer": "my answer"},
        )
        assert res.status_code == 200
        assert res.get_json()["ok"] is True

        progress = json.loads((tmp_path / "progress.json").read_text())
        assert progress["answers"]["t-01"] == "my answer"

    def test_missing_problem_id_returns_400(self, client):
        res = client.post("/api/answer", json={"answer": "oops"})
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# API: /api/complete
# ---------------------------------------------------------------------------

class TestApiComplete:
    def test_marks_today_complete(self, client, tmp_path):
        res = client.post("/api/complete", json={"problemId": "t-01"})
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        assert body["totalSolved"] >= 1

        progress = json.loads((tmp_path / "progress.json").read_text())
        today = date.today().isoformat()
        assert today in progress["completed"]

    def test_streak_returned(self, client):
        res = client.post("/api/complete", json={"problemId": "t-01"})
        body = res.get_json()
        assert "streak" in body
        assert body["streak"] >= 1

    def test_difficulty_tier_returned(self, client):
        res = client.post("/api/complete", json={"problemId": "t-01"})
        body = res.get_json()
        assert "difficultyTier" in body


# ---------------------------------------------------------------------------
# API: /api/history
# ---------------------------------------------------------------------------

class TestApiHistory:
    def test_empty_history(self, client):
        data = client.get("/api/history").get_json()
        assert data["history"] == []

    def test_history_includes_completed_items(self, client, tmp_path):
        today = date.today().isoformat()
        make_progress(tmp_path, completed={today: "t-01"})
        data = client.get("/api/history").get_json()
        assert len(data["history"]) == 1
        item = data["history"][0]
        assert item["date"] == today
        assert "title" in item
        assert "category" in item
        assert "difficulty" in item


# ---------------------------------------------------------------------------
# API: /api/stats
# ---------------------------------------------------------------------------

class TestApiStats:
    def test_stats_shape(self, client):
        data = client.get("/api/stats").get_json()
        assert "streak" in data
        assert "totalSolved" in data
        assert "bankSize" in data
        assert "difficultyTier" in data
        assert "byCategory" in data
        assert "byDifficulty" in data
        assert "byWeek" in data
        assert "streakHistory" in data

    def test_by_week_has_12_entries(self, client):
        data = client.get("/api/stats").get_json()
        assert len(data["byWeek"]) == 12

    def test_streak_history_has_30_entries(self, client):
        data = client.get("/api/stats").get_json()
        assert len(data["streakHistory"]) == 30

    def test_stats_reflect_completed_problems(self, client, tmp_path):
        today = date.today().isoformat()
        make_progress(tmp_path, completed={today: "t-01"})
        data = client.get("/api/stats").get_json()
        assert data["totalSolved"] == 1
        assert data["streak"] == 1


# ---------------------------------------------------------------------------
# API: /api/bonus
# ---------------------------------------------------------------------------

class TestApiBonus:
    def test_returns_problem(self, client):
        data = client.get("/api/bonus").get_json()
        assert "problem" in data
        assert "id" in data["problem"]


# ---------------------------------------------------------------------------
# Index route
# ---------------------------------------------------------------------------

class TestIndex:
    def test_index_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
