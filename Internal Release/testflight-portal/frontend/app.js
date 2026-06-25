const API = "";

const $ = (sel) => document.querySelector(sel);
const terminal = $("#terminal");
const btnReleaseIos = $("#btn-release-ios");
const btnReleaseAndroid = $("#btn-release-android");
const btnReleaseBoth = $("#btn-release-both");
const btnAnalyze = $("#btn-analyze");
const btnClearLogs = $("#btn-clear-logs");
const aiOutput = $("#ai-output");
const aiQuestion = $("#ai-question");

const IOS_STEPS = ["increment", "publish_ios", "upload_ios"];
const ANDROID_STEPS = ["publish_android"];

let ws = null;
let logBuffer = [];
let terminalCleared = false;

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
  } else if (/\[iOS\]/i.test(line)) {
    span.className = "line-ios";
  } else if (/\[Android\]/i.test(line)) {
    span.className = "line-android";
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

function updatePlatformUi(platform, data) {
  const running = data.status === "running";
  const btn = platform === "ios" ? btnReleaseIos : btnReleaseAndroid;
  const hint = platform === "ios" ? $("#ios-hint") : $("#android-hint");
  const label = platform === "ios"
    ? (running ? "Releasing…" : "Release to TestFlight")
    : (running ? "Building…" : "Build Android AAB");

  btn.disabled = running;
  btn.classList.toggle("running", running);
  btn.querySelector("span:last-child").textContent = label;

  updateSteps(data.steps, platform);

  if (data.status === "failed") {
    hint.textContent = `Failed: ${data.error}`;
    hint.style.color = "var(--error)";
  } else if (data.status === "success") {
    if (platform === "ios") {
      hint.textContent = `Build ${data.new_build} uploaded to TestFlight.`;
    } else {
      const name = data.aab_path ? data.aab_path.split("/").pop() : "AAB";
      hint.textContent = `${name} ready for internal beta.`;
    }
    hint.style.color = "var(--success)";
  } else if (data.status === "idle") {
    hint.textContent = platform === "ios"
      ? "Increment → build → upload"
      : "Signed AAB for internal beta testers";
    hint.style.color = "var(--text-muted)";
  }
}

function setBothButton(running) {
  btnReleaseBoth.disabled = running;
  btnReleaseBoth.classList.toggle("running", running);
  btnReleaseBoth.querySelector("span:last-child").textContent = running
    ? "Both builds running…"
    : "Release Both in Parallel";
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

    updatePlatformUi("ios", data.ios);
    updatePlatformUi("android", data.android);

    const anyRunning =
      data.ios.status === "running" || data.android.status === "running";
    setBothButton(anyRunning);

    if (data.ios.status === "success") await fetchPreview();
  } catch {
    /* server may be starting */
  }
}

async function startRelease(platform) {
  if (platform === "ios") {
    $("#ios-hint").textContent = "Release in progress…";
    $("#ios-hint").style.color = "var(--text-muted)";
    resetSteps("ios-steps", IOS_STEPS);
  } else if (platform === "android") {
    $("#android-hint").textContent = "Build in progress…";
    $("#android-hint").style.color = "var(--text-muted)";
    resetSteps("android-steps", ANDROID_STEPS);
  } else {
    $("#ios-hint").textContent = "Release in progress…";
    $("#android-hint").textContent = "Build in progress…";
    $("#ios-hint").style.color = "var(--text-muted)";
    $("#android-hint").style.color = "var(--text-muted)";
    resetSteps("ios-steps", IOS_STEPS);
    resetSteps("android-steps", ANDROID_STEPS);
  }

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
    logBuffer = [];
    pollStatus();
  } catch {
    alert("Could not reach server. Is it running?");
  }
}

btnReleaseIos.addEventListener("click", () => startRelease("ios"));
btnReleaseAndroid.addEventListener("click", () => startRelease("android"));
btnReleaseBoth.addEventListener("click", () => startRelease("both"));

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
