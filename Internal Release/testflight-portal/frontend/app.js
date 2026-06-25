const API = "";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const terminal = $("#terminal");
const btnReleaseIos = $("#btn-release-ios");
const btnReleaseAndroid = $("#btn-release-android");
const btnAnalyze = $("#btn-analyze");
const btnClearLogs = $("#btn-clear-logs");
const aiOutput = $("#ai-output");
const aiQuestion = $("#ai-question");

const IOS_STEPS = ["increment", "publish_ios", "upload_ios"];
const ANDROID_STEPS = ["publish_android"];

let ws = null;
let logBuffer = [];
let terminalCleared = false;
let activePlatform = null;

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${location.host}/ws/logs`);

  ws.onmessage = (event) => {
    if (event.data === "__ping__") return;
    appendLog(event.data);
  };

  ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

function appendLog(line) {
  logBuffer.push(line);

  if (terminalCleared) {
    terminal.textContent = "";
    terminalCleared = false;
  }

  if (terminal.querySelector(".placeholder")) {
    terminal.innerHTML = "";
  }

  const span = document.createElement("span");
  span.textContent = line + "\n";
  if (/ERROR|error|failed|FAILED/i.test(line)) {
    span.className = "line-error";
  }
  terminal.appendChild(span);
  terminal.scrollTop = terminal.scrollHeight;
}

function resetSteps(containerId, stepIds) {
  stepIds.forEach((id) => {
    const el = document.querySelector(`#${containerId} .step[data-step="${id}"]`);
    if (el) el.classList.remove("running", "success", "failed");
  });
}

function updateSteps(steps, platform) {
  if (!steps || !platform) return;
  const containerId = platform === "ios" ? "ios-steps" : "android-steps";
  for (const step of steps) {
    const el = document.querySelector(`#${containerId} .step[data-step="${step.id}"]`);
    if (!el) continue;
    el.classList.remove("running", "success", "failed");
    if (step.status === "running") el.classList.add("running");
    else if (step.status === "success") el.classList.add("success");
    else if (step.status === "failed") el.classList.add("failed");
  }
}

function setButtonsRunning(running, platform) {
  btnReleaseIos.disabled = running;
  btnReleaseAndroid.disabled = running;
  btnReleaseIos.classList.toggle("running", running && platform === "ios");
  btnReleaseAndroid.classList.toggle("running", running && platform === "android");

  if (running && platform === "ios") {
    btnReleaseIos.querySelector("span:last-child").textContent = "Releasing…";
  } else {
    btnReleaseIos.querySelector("span:last-child").textContent = "Release to TestFlight";
  }

  if (running && platform === "android") {
    btnReleaseAndroid.querySelector("span:last-child").textContent = "Building…";
  } else {
    btnReleaseAndroid.querySelector("span:last-child").textContent = "Build Android AAB";
  }
}

async function fetchPreview() {
  const res = await fetch(`${API}/api/preview`);
  const data = await res.json();
  $("#current-build").textContent = data.current ?? "—";
  $("#next-build").textContent = data.next ?? "—";
  $("#project-path").textContent = data.csproj_path ?? "";
}

async function fetchHealth() {
  const res = await fetch(`${API}/api/health`);
  const data = await res.json();
  const badges = $("#badges");
  badges.innerHTML = "";

  const appleBadge = document.createElement("span");
  appleBadge.className = `badge ${data.apple_configured ? "ok" : "warn"}`;
  appleBadge.textContent = data.apple_configured ? "Apple ID configured" : "Apple ID missing";
  badges.appendChild(appleBadge);

  const androidBadge = document.createElement("span");
  const androidOk = data.android_configured && data.android_keystore_exists;
  androidBadge.className = `badge ${androidOk ? "ok" : "warn"}`;
  androidBadge.textContent = androidOk
    ? "Android signing ready"
    : data.android_configured
      ? "Keystore file missing"
      : "Android signing missing";
  badges.appendChild(androidBadge);

  const groqBadge = document.createElement("span");
  groqBadge.className = `badge ${data.groq_configured ? "ok" : "warn"}`;
  groqBadge.textContent = data.groq_configured ? "Groq AI ready" : "Groq optional";
  badges.appendChild(groqBadge);
}

async function pollStatus() {
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    const running = data.status === "running";

    if (data.platform) {
      activePlatform = data.platform;
      updateSteps(data.steps, data.platform);
    }

    setButtonsRunning(running, data.platform);

    if (data.status === "success" || data.status === "failed") {
      if (data.platform === "ios") {
        const hint = $("#ios-hint");
        if (data.status === "failed") {
          hint.textContent = `Failed: ${data.error}`;
          hint.style.color = "var(--error)";
        } else {
          hint.textContent = `Build ${data.new_build} uploaded to TestFlight.`;
          hint.style.color = "var(--success)";
        }
      } else if (data.platform === "android") {
        const hint = $("#android-hint");
        if (data.status === "failed") {
          hint.textContent = `Failed: ${data.error}`;
          hint.style.color = "var(--error)";
        } else {
          const name = data.aab_path ? data.aab_path.split("/").pop() : "AAB";
          hint.textContent = `${name} ready for internal beta.`;
          hint.style.color = "var(--success)";
        }
      }

      if (data.platform === "ios") await fetchPreview();
      activePlatform = null;
    }
  } catch {
    /* server may be starting */
  }
}

async function startRelease(platform) {
  const hintEl = platform === "ios" ? $("#ios-hint") : $("#android-hint");
  hintEl.textContent = platform === "ios" ? "Release in progress…" : "Build in progress…";
  hintEl.style.color = "var(--text-muted)";

  resetSteps(platform === "ios" ? "ios-steps" : "android-steps",
    platform === "ios" ? IOS_STEPS : ANDROID_STEPS);

  try {
    const res = await fetch(`${API}/api/release`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Could not start release");
      return;
    }
    activePlatform = platform;
    setButtonsRunning(true, platform);
    logBuffer = [];
  } catch {
    alert("Could not reach server. Is it running?");
  }
}

btnReleaseIos.addEventListener("click", () => startRelease("ios"));
btnReleaseAndroid.addEventListener("click", () => startRelease("android"));

btnClearLogs.addEventListener("click", () => {
  terminal.innerHTML = '<span class="placeholder">Logs cleared (server buffer retained).</span>';
  terminalCleared = true;
});

btnAnalyze.addEventListener("click", async () => {
  btnAnalyze.disabled = true;
  aiOutput.innerHTML = '<span class="ai-loading">Analyzing logs…</span>';

  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: aiQuestion.value || null }),
    });

    const data = await res.json();
    if (!res.ok) {
      aiOutput.innerHTML = `<p class="placeholder">${data.detail || "Analysis failed"}</p>`;
      return;
    }

    const paragraphs = data.analysis.split("\n\n").filter(Boolean);
    aiOutput.innerHTML = paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("");
  } catch {
    aiOutput.innerHTML = '<p class="placeholder">Could not reach AI service.</p>';
  } finally {
    btnAnalyze.disabled = false;
  }
});

aiQuestion.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnAnalyze.click();
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

connectWebSocket();
fetchPreview();
fetchHealth();
setInterval(pollStatus, 2000);
