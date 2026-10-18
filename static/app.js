const REFRESH_MS = 5 * 60 * 1000;
const TV_KEY = "aules:tv";

const tasksEl = document.getElementById("tasks");
const emptyEl = document.getElementById("empty");
const errorEl = document.getElementById("error-banner");
const updatedAtEl = document.getElementById("updated-at");
const statTotalEl = document.getElementById("stat-total");
const statUrgentEl = document.getElementById("stat-urgent");
const btnRefresh = document.getElementById("btn-refresh");
const btnTv = document.getElementById("btn-tv");

let countdownTimer = null;
let dueById = {};

function isTv() {
  const params = new URLSearchParams(location.search);
  if (params.has("tv")) return params.get("tv") !== "0";
  return localStorage.getItem(TV_KEY) === "1";
}

function setTv(on) {
  document.body.classList.toggle("tv", on);
  btnTv.classList.toggle("active", on);
  localStorage.setItem(TV_KEY, on ? "1" : "0");
}

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString("es-ES", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function urgencyOf(secondsLeft) {
  if (secondsLeft < 86400) return "urgent";
  if (secondsLeft < 3 * 86400) return "warning";
  return "ok";
}

function countdownHtml(task) {
  const urgency = urgencyOf(task.seconds_left);
  const div = document.createElement("div");
  div.className = `countdown urgency-${urgency}`;
  div.dataset.taskId = task.id;
  div.innerHTML = `
    <div class="unit"><div class="num" data-f="d">--</div><div class="lbl">días</div></div>
    <div class="unit"><div class="num" data-f="h">--</div><div class="lbl">horas</div></div>
    <div class="unit"><div class="num" data-f="m">--</div><div class="lbl">min</div></div>
    <div class="unit"><div class="num" data-f="s">--</div><div class="lbl">seg</div></div>`;
  return div;
}

function cardHtml(task) {
  const card = document.createElement("article");
  card.className = `card ${urgencyOf(task.seconds_left)}`;
  card.dataset.taskId = task.id;

  const meta = [];
  if (task.teacher) meta.push(`👤 ${task.teacher}`);
  meta.push(`📅 ${fmtDate(task.due)}`);

  card.innerHTML = `
    <div class="card-subject">${esc(task.subject)}</div>
    <h2 class="card-title">📌 ${esc(task.title)}</h2>
    <div class="card-meta">${meta.join(" · ")}</div>
    ${task.description ? `<p class="card-desc">${esc(task.description)}</p>` : ""}
  `;
  card.appendChild(countdownHtml(task));
  return card;
}

function esc(s) {
  const div = document.createElement("div");
  div.textContent = s || "";
  return div.innerHTML;
}

function render(data) {
  dueById = {};
  tasksEl.innerHTML = "";
  statTotalEl.textContent = data.total;
  statUrgentEl.textContent = data.urgent;

  const updated = new Date(data.updated_at);
  updatedAtEl.textContent = `Actualizado: ${updated.toLocaleTimeString("es-ES")}`;

  if (data.errors && data.errors.length) {
    errorEl.textContent = "⚠ " + data.errors.join(" | ");
    errorEl.classList.remove("hidden");
  } else {
    errorEl.classList.add("hidden");
  }

  for (const task of data.tasks) {
    dueById[task.id] = Date.parse(task.due);
    tasksEl.appendChild(cardHtml(task));
  }

  emptyEl.classList.toggle("hidden", data.tasks.length > 0);
  startCountdown();
}

function tickCountdowns() {
  const now = Date.now();
  for (const [id, due] of Object.entries(dueById)) {
    const el = tasksEl.querySelector(`.countdown[data-task-id="${id}"]`);
    if (!el) continue;

    let s = Math.max(0, Math.floor((due - now) / 1000));
    const card = el.closest(".card");
    if (card) {
      const urgency = urgencyOf(s);
      card.classList.remove("urgent", "warning", "ok");
      card.classList.add(urgency);
    }
    const d = Math.floor(s / 86400);
    s -= d * 86400;
    const h = Math.floor(s / 3600);
    s -= h * 3600;
    const m = Math.floor(s / 60);
    s -= m * 60;

    el.querySelector('[data-f="d"]').textContent = String(d);
    el.querySelector('[data-f="h"]').textContent = String(h).padStart(2, "0");
    el.querySelector('[data-f="m"]').textContent = String(m).padStart(2, "0");
    el.querySelector('[data-f="s"]').textContent = String(s).padStart(2, "0");
  }
}

function startCountdown() {
  if (countdownTimer) clearInterval(countdownTimer);
  tickCountdowns();
  countdownTimer = setInterval(tickCountdowns, 1000);
}

async function loadTasks(force = false) {
  const bust = Date.now();
  const urls = force
    ? [`/api/refresh?_=${bust}`, `/data.json?_=${bust}`]
    : [`/api/tasks?_=${bust}`, `/data.json?_=${bust}`];
  let lastErr = null;

  for (const url of urls) {
    try {
      const res = await fetch(url, {
        cache: "no-store",
        method: url.startsWith("/api/refresh") ? "POST" : "GET",
      });
      if (!res.ok) {
        lastErr = new Error(`HTTP ${res.status}`);
        continue;
      }
      render(await res.json());
      return;
    } catch (err) {
      lastErr = err;
    }
  }
  errorEl.textContent = `⚠ Error de conexión: ${lastErr.message}`;
  errorEl.classList.remove("hidden");
}

btnRefresh.addEventListener("click", () => loadTasks(true));
btnTv.addEventListener("click", () => setTv(!isTv()));

setTv(isTv());
loadTasks();
setInterval(() => loadTasks(), REFRESH_MS);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
