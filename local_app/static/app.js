const $ = (id) => document.getElementById(id);
let chatHistory = [];
let currentContext = null;
let activeJob = null;

const fields = [
  "prefix",
  "event_number",
  "operation_name",
  "package_ids",
  "campaign_dir",
  "bms_root",
  "theater_folder",
  "object_dir",
  "map_source",
  "pyopencam_root",
  "planner_text",
];

function formData() {
  const data = {};
  for (const field of fields) {
    data[field] = $(field).value.trim();
  }
  data.cam_decoder = "pyopencam";
  data.render_maps = true;
  return data;
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("chatLog").appendChild(div);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text}`);
  }
  return response.json();
}

async function refreshStatus() {
  try {
    const prefix = $("prefix")?.value?.trim() || "";
    const status = await api(`/api/status?prefix=${encodeURIComponent(prefix)}`);
    const available = Object.entries(status.providers)
      .filter(([, ok]) => ok)
      .map(([name]) => name)
      .join(", ");
    const pyopencam = status.pyopencam?.available
      ? `pyopencam: ${status.pyopencam.path}`
      : "pyopencam: not found";
    $("providerStatus").textContent = available
      ? `Available providers: ${available}`
      : "No provider detected; offline template mode is available.";
    $("providerStatus").textContent += ` | ${pyopencam}`;
    if (status.pyopencam?.available && !$("pyopencam_root").value) {
      $("pyopencam_root").value = status.pyopencam.path;
    }
    if (status.bms?.bms_root && !$("bms_root").value) {
      $("bms_root").value = status.bms.bms_root;
    }
    if (status.bms?.campaign_dir && (!$("campaign_dir").value || $("campaign_dir").value === ".")) {
      $("campaign_dir").value = status.bms.campaign_dir;
    }
  } catch (error) {
    $("providerStatus").textContent = `Status unavailable: ${error.message}`;
  }
}

async function sendChat() {
  const message = $("chatInput").value.trim();
  if (!message) return;
  $("chatInput").value = "";
  addMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        form: formData(),
        history: chatHistory,
        provider: $("provider").value,
      }),
    });
    const answer = `[${result.provider}] ${result.message}`;
    addMessage("assistant", answer);
    chatHistory.push({ role: "assistant", content: result.message });
  } catch (error) {
    addMessage("system", `Chat failed: ${error.message}`);
  }
}

async function draftContext() {
  addMessage("system", "Drafting mission context JSON...");
  try {
    const result = await api("/api/context", {
      method: "POST",
      body: JSON.stringify({
        form: formData(),
        planner_text: $("planner_text").value,
        provider: $("provider").value,
      }),
    });
    currentContext = result.mission_context;
    $("contextJson").value = JSON.stringify(currentContext, null, 2);
    addMessage("assistant", `Mission context drafted with ${result.provider}. Review/edit it, then run the workflow.`);
  } catch (error) {
    addMessage("system", `Context draft failed: ${error.message}`);
  }
}

async function runWorkflow() {
  let missionContext = currentContext;
  const raw = $("contextJson").value.trim();
  if (raw) {
    try {
      missionContext = JSON.parse(raw);
    } catch (error) {
      addMessage("system", `Mission context JSON is invalid: ${error.message}`);
      return;
    }
  }
  addMessage("system", "Starting workflow job...");
  try {
    const result = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ form: formData(), mission_context: missionContext }),
    });
    activeJob = result.job_id;
    pollJob();
  } catch (error) {
    addMessage("system", `Workflow start failed: ${error.message}`);
  }
}

async function pollJob() {
  if (!activeJob) return;
  try {
    const job = await api(`/api/jobs/${activeJob}`);
    $("jobLogs").textContent = job.logs.join("\n");
    $("artifacts").innerHTML = "";
    for (const [name, path] of Object.entries(job.artifacts || {})) {
      const div = document.createElement("div");
      div.className = "artifact";
      div.textContent = `${name}: ${path}`;
      $("artifacts").appendChild(div);
    }
    if (job.status === "running" || job.status === "queued") {
      setTimeout(pollJob, 1500);
    } else {
      addMessage(job.status === "complete" ? "assistant" : "system", `Workflow ${job.status}.`);
    }
  } catch (error) {
    $("jobLogs").textContent += `\nPoll failed: ${error.message}`;
  }
}

$("sendChat").addEventListener("click", sendChat);
$("draftContext").addEventListener("click", draftContext);
$("runWorkflow").addEventListener("click", runWorkflow);
["prefix", "campaign_dir", "bms_root"].forEach((id) => {
  $(id).addEventListener("blur", refreshStatus);
});
$("chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) sendChat();
});

refreshStatus();
addMessage("assistant", "Fill the mission fields, paste planner intent, then draft context. I will use OpenAI first when configured, otherwise Ollama/LM Studio/local template.");
