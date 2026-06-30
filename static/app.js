// Brain Gym front-end logic: fetch the daily problem, manage reveals,
// save answers, mark complete, and show history.
//
// Progress (streak, completed days, saved answers) is stored in browser
// localStorage so it survives on any host — including free tiers that reset
// the filesystem between deploys. The server APIs are still called for
// local-dev compatibility but are treated as best-effort.

const state = {
  problem: null,
  hintsRevealed: 0,
};

const el = (id) => document.getElementById(id);

const difficultyStars = (level) => "★".repeat(level) + "☆".repeat(3 - level);

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// localStorage-backed progress store
// ---------------------------------------------------------------------------
const STORAGE_KEY = "brainGymProgress";

function loadLocalProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) { /* ignore parse errors */ }
  return { completed: {}, answers: {}, history: [] };
}

function saveLocalProgress(progress) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (_) { /* storage quota exceeded — ignore */ }
}

function computeLocalStreak(completedDates) {
  if (!completedDates || !completedDates.length) return 0;
  const days = new Set(completedDates);
  const today = new Date();
  const todayKey = today.toISOString().slice(0, 10);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayKey = yesterday.toISOString().slice(0, 10);

  let cursor;
  if (days.has(todayKey)) cursor = new Date(todayKey + "T00:00:00");
  else if (days.has(yesterdayKey)) cursor = new Date(yesterdayKey + "T00:00:00");
  else return 0;

  let streak = 0;
  while (true) {
    const key = cursor.toISOString().slice(0, 10);
    if (!days.has(key)) break;
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

function renderProblem(problem, { savedAnswer = "", completedToday = false } = {}) {
  state.problem = problem;
  state.hintsRevealed = 0;

  const catBadge = el("categoryBadge");
  catBadge.textContent = problem.category.replace("-", " ");
  catBadge.dataset.cat = problem.category;

  el("difficultyBadge").textContent = difficultyStars(problem.difficulty);
  el("problemTitle").textContent = problem.title;
  el("problemPrompt").textContent = problem.prompt;
  el("answerBox").value = savedAnswer;

  // Reset reveal areas.
  el("hintsArea").classList.add("hidden");
  el("solutionArea").classList.add("hidden");
  el("hintsList").innerHTML = "";
  el("hintBtn").textContent = "💡 Reveal a hint";
  el("hintBtn").disabled = false;

  const completeBtn = el("completeBtn");
  if (completedToday) {
    completeBtn.textContent = "✅ Solved today";
    completeBtn.classList.add("completeBtn-done");
    completeBtn.disabled = true;
  } else {
    completeBtn.textContent = "✅ Mark solved";
    completeBtn.classList.remove("completeBtn-done");
    completeBtn.disabled = false;
  }
}

function revealNextHint() {
  const hints = state.problem.hints || [];
  if (state.hintsRevealed >= hints.length) return;

  el("hintsArea").classList.remove("hidden");
  const li = document.createElement("li");
  li.textContent = hints[state.hintsRevealed];
  el("hintsList").appendChild(li);
  state.hintsRevealed += 1;

  const btn = el("hintBtn");
  if (state.hintsRevealed >= hints.length) {
    btn.textContent = "💡 No more hints";
    btn.disabled = true;
  } else {
    btn.textContent = `💡 Reveal hint ${state.hintsRevealed + 1} of ${hints.length}`;
  }
}

function showSolution() {
  el("solutionText").textContent = state.problem.approach;
  el("reflectionText").textContent = state.problem.reflection;
  el("solutionArea").classList.remove("hidden");
}

async function saveAnswer() {
  if (!state.problem) return;
  const progress = loadLocalProgress();
  progress.answers[state.problem.id] = el("answerBox").value;
  saveLocalProgress(progress);

  // Best-effort server sync for local dev.
  api("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problemId: state.problem.id,
      answer: el("answerBox").value,
    }),
  }).catch(() => {});

  const note = el("savedNote");
  note.textContent = "Saved ✓";
  note.classList.add("show");
  setTimeout(() => note.classList.remove("show"), 1800);
}

async function markComplete() {
  if (!state.problem) return;
  const todayKey = new Date().toISOString().slice(0, 10);
  const progress = loadLocalProgress();
  progress.completed[todayKey] = state.problem.id;
  progress.answers[state.problem.id] = el("answerBox").value;

  // Upsert into history (avoid duplicates for the same date).
  const existingIdx = (progress.history || []).findIndex((h) => h.date === todayKey);
  const entry = {
    date: todayKey,
    problemId: state.problem.id,
    title: state.problem.title,
    category: state.problem.category,
    answer: el("answerBox").value,
  };
  if (existingIdx >= 0) {
    progress.history[existingIdx] = entry;
  } else {
    progress.history = [entry, ...(progress.history || [])];
  }
  saveLocalProgress(progress);

  const streak = computeLocalStreak(Object.keys(progress.completed));
  el("streak").textContent = streak;
  el("solved").textContent = Object.keys(progress.completed).length;

  const btn = el("completeBtn");
  btn.textContent = "✅ Solved today";
  btn.classList.add("completeBtn-done");
  btn.disabled = true;

  // Best-effort server sync for local dev.
  api("/api/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problemId: state.problem.id }),
  }).catch(() => {});
}

async function loadToday() {
  const data = await api("/api/today");
  const progress = loadLocalProgress();
  const todayKey = data.date;

  const completedToday = todayKey in progress.completed;
  const savedAnswer = progress.answers[data.problem.id] || "";
  const streak = computeLocalStreak(Object.keys(progress.completed));
  const totalSolved = Object.keys(progress.completed).length;

  el("dateLabel").textContent = new Date(data.date + "T00:00:00").toLocaleDateString(
    undefined,
    { weekday: "long", month: "short", day: "numeric" }
  );
  el("streak").textContent = streak;
  el("solved").textContent = totalSolved;
  renderProblem(data.problem, {
    savedAnswer,
    completedToday,
  });
}

async function loadBonus() {
  const data = await api("/api/bonus");
  renderProblem(data.problem);
  el("dateLabel").textContent = "🎲 Bonus problem";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function openHistory() {
  const progress = loadLocalProgress();
  const list = el("historyList");
  list.innerHTML = "";

  const history = (progress.history || []).slice().sort((a, b) => b.date.localeCompare(a.date));

  if (!history.length) {
    list.innerHTML = '<p class="history-empty">No solved problems yet. Solve today\'s to start your streak! 🔥</p>';
  } else {
    for (const item of history) {
      const div = document.createElement("div");
      div.className = "history-item";
      const dateText = new Date(item.date + "T00:00:00").toLocaleDateString();
      div.innerHTML = `
        <div class="hi-head">
          <span class="hi-title"></span>
          <span class="hi-date"></span>
        </div>
        <div class="hi-answer"></div>`;
      div.querySelector(".hi-title").textContent = item.title;
      div.querySelector(".hi-date").textContent = dateText;
      div.querySelector(".hi-answer").textContent = item.answer
        ? item.answer
        : "(no answer saved)";
      list.appendChild(div);
    }
  }
  el("historyOverlay").classList.remove("hidden");
}

function wireEvents() {
  el("hintBtn").addEventListener("click", revealNextHint);
  el("solutionBtn").addEventListener("click", showSolution);
  el("saveBtn").addEventListener("click", saveAnswer);
  el("completeBtn").addEventListener("click", markComplete);
  el("bonusBtn").addEventListener("click", loadBonus);
  el("historyBtn").addEventListener("click", openHistory);
  el("closeHistory").addEventListener("click", () =>
    el("historyOverlay").classList.add("hidden")
  );
  el("historyOverlay").addEventListener("click", (e) => {
    if (e.target.id === "historyOverlay") {
      el("historyOverlay").classList.add("hidden");
    }
  });
}

wireEvents();
loadToday().catch((err) => {
  el("problemTitle").textContent = "Couldn't load today's problem 😕";
  el("problemPrompt").textContent = err.message;
});
