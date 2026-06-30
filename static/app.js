// Brain Gym front-end logic: fetch the daily problem, manage reveals,
// save answers, mark complete, show history, practice by category, and stats.
// All state lives server-side in data/progress.json; this script just talks
// to the small JSON API.

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
  await api("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problemId: state.problem.id,
      answer: el("answerBox").value,
    }),
  });
  const note = el("savedNote");
  note.textContent = "Saved ✓";
  note.classList.add("show");
  setTimeout(() => note.classList.remove("show"), 1800);
}

async function markComplete() {
  if (!state.problem) return;
  const result = await api("/api/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problemId: state.problem.id }),
  });
  el("streak").textContent = result.streak;
  el("solved").textContent = result.totalSolved;

  const btn = el("completeBtn");
  btn.textContent = "✅ Solved today";
  btn.classList.add("completeBtn-done");
  btn.disabled = true;
}

async function loadToday() {
  const data = await api("/api/today");
  el("dateLabel").textContent = new Date(data.date + "T00:00:00").toLocaleDateString(
    undefined,
    { weekday: "long", month: "short", day: "numeric" }
  );
  el("streak").textContent = data.streak;
  el("solved").textContent = data.totalSolved;
  renderProblem(data.problem, {
    savedAnswer: data.savedAnswer,
    completedToday: data.completedToday,
  });
}

async function loadBonus() {
  const data = await api("/api/bonus");
  renderProblem(data.problem);
  el("dateLabel").textContent = "🎲 Bonus problem";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadPractice() {
  const category = el("categorySelect").value;
  const url = category === "all" ? "/api/practice" : `/api/practice?category=${encodeURIComponent(category)}`;
  const data = await api(url);
  renderProblem(data.problem);
  const catLabel = category === "all" ? "Practice problem" : `Practice: ${category.replace("-", " ")}`;
  el("dateLabel").textContent = `🎯 ${catLabel}`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function openHistory() {
  const data = await api("/api/history");
  const list = el("historyList");
  list.innerHTML = "";

  if (!data.history.length) {
    list.innerHTML = '<p class="history-empty">No solved problems yet. Solve today\'s to start your streak! 🔥</p>';
  } else {
    for (const item of data.history) {
      const div = document.createElement("div");
      div.className = "history-item";
      const dateText = new Date(item.date + "T00:00:00").toLocaleDateString();
      div.innerHTML = `
        <div class="hi-head">
          <span class="hi-title"></span>
          <span class="hi-date"></span>
        </div>
        <div class="hi-meta"></div>
        <div class="hi-answer"></div>`;
      div.querySelector(".hi-title").textContent = item.title;
      div.querySelector(".hi-date").textContent = dateText;
      div.querySelector(".hi-meta").innerHTML =
        `<span class="badge" data-cat="${item.category}">${item.category.replace("-", " ")}</span>` +
        `<span class="difficulty">${difficultyStars(item.difficulty || 0)}</span>`;
      div.querySelector(".hi-answer").textContent = item.answer
        ? item.answer
        : "(no answer saved)";
      list.appendChild(div);
    }
  }
  el("historyOverlay").classList.remove("hidden");
}

// ── Stats view ────────────────────────────────────────────────────────────

function svgBarChart(data, { width = 320, height = 100, barColor = "#6c8cff", labelColor = "#9aa0c4" } = {}) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const barW = Math.floor((width - (data.length - 1) * 4) / data.length);
  const bars = data
    .map((d, i) => {
      const bh = Math.round((d.value / maxVal) * (height - 20));
      const x = i * (barW + 4);
      const y = height - 20 - bh;
      return `
        <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="3" fill="${barColor}" opacity="0.8"/>
        <title>${d.label}: ${d.value}</title>`;
    })
    .join("");
  // X-axis labels (show every other label to avoid clutter)
  const labels = data
    .map((d, i) => {
      if (i % Math.ceil(data.length / 6) !== 0) return "";
      const x = i * (barW + 4) + barW / 2;
      const shortLabel = d.label.length > 6 ? d.label.slice(-5) : d.label;
      return `<text x="${x}" y="${height - 4}" text-anchor="middle" font-size="9" fill="${labelColor}">${shortLabel}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" style="display:block">${bars}${labels}</svg>`;
}

function svgDonut(slices, { size = 120, colors } = {}) {
  const total = slices.reduce((s, d) => s + d.value, 0) || 1;
  const defaultColors = ["#6c8cff", "#46d6b8", "#ffb454", "#ff6b8a", "#c484ff"];
  let angle = -Math.PI / 2;
  const cx = size / 2, cy = size / 2, r = size * 0.38, innerR = size * 0.22;
  const paths = slices.map((d, i) => {
    const sweep = (d.value / total) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(angle);
    const y1 = cy + r * Math.sin(angle);
    angle += sweep;
    const x2 = cx + r * Math.cos(angle);
    const y2 = cy + r * Math.sin(angle);
    const ix1 = cx + innerR * Math.cos(angle);
    const iy1 = cy + innerR * Math.sin(angle);
    const ix2 = cx + innerR * Math.cos(angle - sweep);
    const iy2 = cy + innerR * Math.sin(angle - sweep);
    const large = sweep > Math.PI ? 1 : 0;
    const col = (colors || defaultColors)[i % defaultColors.length];
    return `<path d="M${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} L${ix1},${iy1} A${innerR},${innerR} 0 ${large},0 ${ix2},${iy2} Z" fill="${col}"><title>${d.label}: ${d.value}</title></path>`;
  });
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">${paths.join("")}</svg>`;
}

async function openStats() {
  const data = await api("/api/stats");
  const content = el("statsContent");

  const tierLabel = ["", "Beginner (difficulty 1)", "Intermediate (1–2)", "Advanced (1–3)"][data.difficultyTier] || "";

  // Weekly bar chart
  const weekBars = data.byWeek.map((w) => ({ label: w.week, value: w.count }));
  const weekChart = svgBarChart(weekBars, { barColor: "#6c8cff" });

  // Streak sparkline (last 30 days)
  const streakBars = data.streakHistory.map((s) => ({ label: s.date, value: s.streak }));
  const streakChart = svgBarChart(streakBars, { barColor: "#46d6b8", width: 320, height: 80 });

  // Category donut
  const catOrder = ["everyday", "logic", "system-design", "estimation", "creative"];
  const catSlices = catOrder.map((c) => ({ label: c.replace("-", " "), value: data.byCategory[c] || 0 }));
  const catDonut = svgDonut(catSlices);

  // Difficulty donut
  const diffSlices = [
    { label: "Difficulty 1", value: data.byDifficulty["1"] || 0 },
    { label: "Difficulty 2", value: data.byDifficulty["2"] || 0 },
    { label: "Difficulty 3", value: data.byDifficulty["3"] || 0 },
  ];
  const diffDonut = svgDonut(diffSlices, { colors: ["#46d6b8", "#ffb454", "#ff6b8a"] });

  // Legend helper
  const catColors = ["#6c8cff", "#46d6b8", "#ffb454", "#ff6b8a", "#c484ff"];
  const catLegend = catOrder
    .map((c, i) => `<span class="legend-item"><span class="legend-dot" style="background:${catColors[i]}"></span>${c.replace("-", " ")} (${data.byCategory[c] || 0})</span>`)
    .join("");
  const diffColors = ["#46d6b8", "#ffb454", "#ff6b8a"];
  const diffLegend = diffSlices
    .map((d, i) => `<span class="legend-item"><span class="legend-dot" style="background:${diffColors[i]}"></span>${d.label} (${d.value})</span>`)
    .join("");

  content.innerHTML = `
    <div class="stats-summary">
      <div class="stats-kpi"><span class="kpi-val">${data.streak}</span><span class="kpi-label">🔥 Current streak</span></div>
      <div class="stats-kpi"><span class="kpi-val">${data.totalSolved}</span><span class="kpi-label">✅ Total solved</span></div>
      <div class="stats-kpi"><span class="kpi-val">${data.bankSize}</span><span class="kpi-label">📚 Problem bank</span></div>
      <div class="stats-kpi"><span class="kpi-val">${data.difficultyTier}</span><span class="kpi-label">⭐ Tier</span></div>
    </div>
    <p class="tier-label">${tierLabel}</p>

    <div class="chart-section">
      <h3>Problems solved per week (last 12 weeks)</h3>
      ${weekChart}
    </div>

    <div class="chart-section">
      <h3>Streak over last 30 days</h3>
      ${streakChart}
    </div>

    <div class="chart-row">
      <div class="chart-section chart-half">
        <h3>By category</h3>
        <div class="donut-wrap">${catDonut}</div>
        <div class="legend">${catLegend}</div>
      </div>
      <div class="chart-section chart-half">
        <h3>By difficulty</h3>
        <div class="donut-wrap">${diffDonut}</div>
        <div class="legend">${diffLegend}</div>
      </div>
    </div>
  `;

  el("statsOverlay").classList.remove("hidden");
}

function wireEvents() {
  el("hintBtn").addEventListener("click", revealNextHint);
  el("solutionBtn").addEventListener("click", showSolution);
  el("saveBtn").addEventListener("click", saveAnswer);
  el("completeBtn").addEventListener("click", markComplete);
  el("bonusBtn").addEventListener("click", loadBonus);
  el("practiceBtn").addEventListener("click", loadPractice);
  el("historyBtn").addEventListener("click", openHistory);
  el("statsBtn").addEventListener("click", openStats);

  el("closeHistory").addEventListener("click", () =>
    el("historyOverlay").classList.add("hidden")
  );
  el("historyOverlay").addEventListener("click", (e) => {
    if (e.target.id === "historyOverlay") el("historyOverlay").classList.add("hidden");
  });

  el("closeStats").addEventListener("click", () =>
    el("statsOverlay").classList.add("hidden")
  );
  el("statsOverlay").addEventListener("click", (e) => {
    if (e.target.id === "statsOverlay") el("statsOverlay").classList.add("hidden");
  });
}

wireEvents();
loadToday().catch((err) => {
  el("problemTitle").textContent = "Couldn't load today's problem 😕";
  el("problemPrompt").textContent = err.message;
});
