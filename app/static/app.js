const state = {
  candidateId: "",
  candidateName: "",
  jobId: "",
  jobTitle: "",
  lastResults: {},
};

const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => Array.from(document.querySelectorAll(selector));

const api = async (path, options = {}) => {
  const headers = new Headers(options.headers || {});
  const key = qs("#api-key").value.trim();
  if (key) headers.set("X-API-Key", key);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(data.detail || `Request failed with status ${response.status}`);
  return data;
};

const notify = (message, isError = false) => {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.clearTimeout(notify.timer);
  notify.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
};

const setStep = (step) => {
  qsa(".step").forEach((button) => button.classList.toggle("active", button.dataset.step === step));
  qsa(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `step-${step}`));
  qs("#progress-fill").style.width = `${Number(step) * 33.333}%`;
};

const setOutputMode = (label) => {
  qs("#output-mode").textContent = label;
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const chips = (values = []) => {
  if (!values.length) return '<span class="subtle">None</span>';
  return values.map((value) => `<span class="chip">${escapeHtml(value)}</span>`).join("");
};

const summaryRows = (rows) =>
  `<div class="summary-grid">${rows
    .map(
      ([key, value]) =>
        `<div class="summary-row"><span class="summary-key">${escapeHtml(key)}</span><span>${value}</span></div>`,
    )
    .join("")}</div>`;

const setOutput = (payload, mode = "Result") => {
  const output = qs("#output");
  setOutputMode(mode);
  if (typeof payload === "string") {
    output.textContent = payload;
    return;
  }
  output.innerHTML = formatResult(payload, mode);
};

const formatResult = (payload, mode) => {
  if (mode === "Resume") {
    return summaryRows([
      ["Candidate", escapeHtml(payload.name)],
      ["Email", escapeHtml(payload.email || "Not provided")],
      ["Experience", `${escapeHtml(payload.experience)} years`],
      ["Education", escapeHtml(payload.education || "Not detected")],
      ["Skills", `<div class="chip-preview">${chips(payload.skills)}</div>`],
    ]);
  }
  if (mode === "Job") {
    return summaryRows([
      ["Role", escapeHtml(payload.title)],
      ["Experience", `${escapeHtml(payload.experience)}-${escapeHtml(payload.max_years_experience)} years`],
      ["Required", `<div class="chip-preview">${chips(payload.skills)}</div>`],
      ["Preferred", `<div class="chip-preview">${chips(payload.preferred_skills)}</div>`],
    ]);
  }
  if (mode === "Match") {
    return summaryRows([
      ["Candidate", escapeHtml(payload.candidate_id)],
      ["Job", escapeHtml(payload.job_id)],
      ["Semantic match", `<strong>${escapeHtml(payload.match_score)}%</strong>`],
    ]);
  }
  if (mode === "Rank") {
    const first = payload.rankings?.[0];
    if (!first) return '<span class="subtle">No rankings returned.</span>';
    return summaryRows([
      ["Rank", `<strong>#${escapeHtml(first.rank)}</strong>`],
      ["Candidate", escapeHtml(first.name)],
      ["Score", `<strong>${escapeHtml(first.score)}%</strong>`],
      ["Skill score", `${escapeHtml(first.feature_scores?.skill_match ?? "--")}%`],
      ["Explanation", `<div class="chip-preview">${chips(first.explanation || [])}</div>`],
    ]);
  }
  if (mode === "Gap") {
    return summaryRows([
      ["Experience gap", `<strong>${escapeHtml(payload.experience_gap_years)} years</strong>`],
      ["Required gaps", `<div class="chip-preview">${chips(payload.missing_required_skills)}</div>`],
      ["Preferred gaps", `<div class="chip-preview">${chips(payload.missing_preferred_skills)}</div>`],
      ["Priority", `<div class="chip-preview">${chips(payload.priority_gaps)}</div>`],
    ]);
  }
  if (mode === "Questions") {
    return `<ol class="question-list">${(payload.questions || [])
      .map((question) => `<li>${escapeHtml(question)}</li>`)
      .join("")}</ol>`;
  }
  if (mode === "Predict") {
    return summaryRows([
      ["Success probability", `<strong>${escapeHtml(payload.success_probability)}%</strong>`],
      ["Model", escapeHtml(payload.model)],
      ["Version", escapeHtml(payload.model_version)],
      ["Contributions", `<pre class="json-view">${escapeHtml(JSON.stringify(payload.feature_contributions, null, 2))}</pre>`],
    ]);
  }
  return `<pre class="json-view">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
};

const setStatus = (selector, message, ok = true) => {
  const node = qs(selector);
  node.textContent = message;
  node.classList.toggle("ok", ok);
  node.classList.toggle("toast", !ok);
};

const refreshSelection = () => {
  qs("#selected-candidate").textContent = state.candidateName || state.candidateId || "None";
  qs("#selected-job").textContent = state.jobTitle || state.jobId || "None";
};

const commaList = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);

const updateTextStats = () => {
  const resumeText = qs("#resume-text").value.trim();
  const skillHits = ["Python", "FastAPI", "Docker", "AWS", "SQL", "Machine Learning", "React", "Kubernetes"].filter((skill) =>
    resumeText.toLowerCase().includes(skill.toLowerCase()),
  );
  qs("#resume-count").textContent = `${resumeText.length.toLocaleString()} characters`;
  qs("#resume-skills").textContent = skillHits.length ? skillHits.join(", ") : "Skills pending";
  qs("#resume-quality").textContent = resumeText.length > 80 ? "Ready" : "Draft";
  qs("#resume-quality").classList.toggle("good", resumeText.length > 80);

  const preferred = commaList(qs("#preferred-skills").value);
  qs("#preferred-preview").innerHTML = chips(preferred);
  qs("#job-quality").textContent = qs("#job-description").value.trim().length > 80 ? "Ready" : "Draft";
  qs("#job-quality").classList.toggle("good", qs("#job-description").value.trim().length > 80);
};

const resetMetrics = () => {
  qs("#metric-match").textContent = "--";
  qs("#metric-success").textContent = "--";
  qs("#metric-gaps").textContent = "--";
  state.lastResults = {};
};

const selectCandidate = async (candidateId) => {
  const candidate = await api(`/api/v1/resume/${candidateId}`);
  state.candidateId = candidate.id;
  state.candidateName = candidate.name;
  qs("#candidate-name").value = candidate.name || "";
  qs("#candidate-email").value = candidate.email || "";
  qs("#resume-text").value = candidate.raw_text || "";
  setStatus("#resume-status", `Selected ${candidate.name}`);
  refreshSelection();
  updateTextStats();
  resetMetrics();
  setOutput(candidate, "Resume");
  await renderCandidates();
  notify("Candidate loaded");
};

const selectJob = async (jobId) => {
  const job = await api(`/api/v1/job/${jobId}`);
  state.jobId = job.id;
  state.jobTitle = job.title;
  qs("#job-title").value = job.title || "";
  qs("#preferred-skills").value = (job.preferred_skills || []).join(", ");
  qs("#job-description").value = job.description || "";
  setStatus("#job-status", `Selected ${job.title}`);
  refreshSelection();
  updateTextStats();
  resetMetrics();
  setOutput(job, "Job");
  await renderJobs();
  notify("Job loaded");
};

const withLoading = async (button, task) => {
  const original = button.innerHTML;
  button.classList.add("loading");
  button.disabled = true;
  button.innerHTML = '<span class="button-icon">...</span>Working';
  try {
    return await task();
  } finally {
    button.classList.remove("loading");
    button.disabled = false;
    button.innerHTML = original;
  }
};

const makeListItem = ({ title, meta, active, onClick }) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `list-item ${active ? "active" : ""}`;

  const titleNode = document.createElement("span");
  titleNode.className = "list-title";
  titleNode.textContent = title;

  const metaNode = document.createElement("span");
  metaNode.className = "list-meta";
  metaNode.textContent = meta;

  button.append(titleNode, metaNode);
  button.addEventListener("click", onClick);
  return button;
};

const renderCandidates = async () => {
  const list = qs("#candidate-list");
  const candidates = await api("/api/v1/candidates");
  qs("#candidate-total").textContent = candidates.length;
  list.classList.toggle("empty", candidates.length === 0);
  list.innerHTML = "";
  if (!candidates.length) {
    list.textContent = "No candidates yet";
    return;
  }
  candidates.forEach((candidate) => {
    list.appendChild(
      makeListItem({
        title: candidate.name,
        meta: candidate.skills.slice(0, 4).join(", ") || "No skills extracted",
        active: candidate.id === state.candidateId,
        onClick: async () => {
          try {
            await selectCandidate(candidate.id);
          } catch (error) {
            notify(error.message, true);
          }
        },
      }),
    );
  });
};

const renderJobs = async () => {
  const list = qs("#job-list");
  const jobs = await api("/api/v1/jobs");
  qs("#job-total").textContent = jobs.length;
  list.classList.toggle("empty", jobs.length === 0);
  list.innerHTML = "";
  if (!jobs.length) {
    list.textContent = "No jobs yet";
    return;
  }
  jobs.forEach((job) => {
    list.appendChild(
      makeListItem({
        title: job.title,
        meta: job.skills.slice(0, 4).join(", ") || "No skills extracted",
        active: job.id === state.jobId,
        onClick: async () => {
          try {
            await selectJob(job.id);
          } catch (error) {
            notify(error.message, true);
          }
        },
      }),
    );
  });
};

const refreshLists = async () => {
  await Promise.all([renderCandidates(), renderJobs()]);
  refreshSelection();
};

const requireSelection = () => {
  if (!state.candidateId || !state.jobId) {
    throw new Error("Select one candidate and one job first.");
  }
};

const runAction = async (action) => {
  requireSelection();
  setOutput("Running...", "Working");
  let result;
  let mode;
  if (action === "match") {
    result = await api("/api/v1/match", {
      method: "POST",
      body: JSON.stringify({ candidate_id: state.candidateId, job_id: state.jobId }),
    });
    qs("#metric-match").textContent = `${result.match_score}%`;
    mode = "Match";
  } else if (action === "rank") {
    result = await api("/api/v1/rank", {
      method: "POST",
      body: JSON.stringify({ job_id: state.jobId, candidate_ids: [state.candidateId] }),
    });
    mode = "Rank";
  } else if (action === "gap") {
    result = await api(`/api/v1/candidates/${state.candidateId}/gap?job_id=${encodeURIComponent(state.jobId)}`);
    qs("#metric-gaps").textContent = result.priority_gaps.length;
    mode = "Gap";
  } else if (action === "questions") {
    result = await api("/api/v1/questions", {
      method: "POST",
      body: JSON.stringify({ candidate_id: state.candidateId, job_id: state.jobId, count: 6 }),
    });
    mode = "Questions";
  } else {
    result = await api("/api/v1/predict-success", {
      method: "POST",
      body: JSON.stringify({ candidate_id: state.candidateId, job_id: state.jobId }),
    });
    qs("#metric-success").textContent = `${result.success_probability}%`;
    mode = "Predict";
  }
  state.lastResults[action] = result;
  setOutput(result, mode);
  return result;
};

qsa(".step").forEach((button) => {
  button.addEventListener("click", () => setStep(button.dataset.step));
});

qs("#resume-text").addEventListener("input", updateTextStats);
qs("#job-description").addEventListener("input", updateTextStats);
qs("#preferred-skills").addEventListener("input", updateTextStats);

qs("#resume-file").addEventListener("change", () => {
  const file = qs("#resume-file").files?.[0];
  qs("#resume-file-name").textContent = file ? file.name : "No file selected";
});

["dragenter", "dragover"].forEach((eventName) => {
  qs("#resume-dropzone").addEventListener(eventName, (event) => {
    event.preventDefault();
    qs("#resume-dropzone").classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  qs("#resume-dropzone").addEventListener(eventName, (event) => {
    event.preventDefault();
    qs("#resume-dropzone").classList.remove("dragging");
  });
});

qs("#resume-dropzone").addEventListener("drop", (event) => {
  const file = event.dataTransfer.files?.[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  qs("#resume-file").files = transfer.files;
  qs("#resume-file-name").textContent = file.name;
});

qs("#upload-resume").addEventListener("click", async (event) => {
  await withLoading(event.currentTarget, async () => {
    try {
      const file = qs("#resume-file").files?.[0];
      if (!file) throw new Error("Choose a resume file first.");
      const form = new FormData();
      form.append("file", file);
      const resume = await api("/api/v1/resume/upload", { method: "POST", body: form });
      state.candidateId = resume.id;
      state.candidateName = resume.name;
      setStatus("#resume-status", `Uploaded ${resume.name}`);
      setOutput(resume, "Resume");
      await refreshLists();
      notify("Resume uploaded");
      setStep("2");
    } catch (error) {
      setStatus("#resume-status", error.message, false);
      notify(error.message, true);
    }
  });
});

qs("#save-resume").addEventListener("click", async (event) => {
  await withLoading(event.currentTarget, async () => {
    try {
      const resume = await api("/api/v1/resumes", {
        method: "POST",
        body: JSON.stringify({
          name: qs("#candidate-name").value.trim(),
          email: qs("#candidate-email").value.trim(),
          resume_text: qs("#resume-text").value.trim(),
        }),
      });
      state.candidateId = resume.id;
      state.candidateName = resume.name;
      setStatus("#resume-status", `Saved ${resume.name}`);
      setOutput(resume, "Resume");
      await refreshLists();
      notify("Resume saved");
      setStep("2");
    } catch (error) {
      setStatus("#resume-status", error.message, false);
      notify(error.message, true);
    }
  });
});

qs("#clear-resume").addEventListener("click", () => {
  qs("#candidate-name").value = "";
  qs("#candidate-email").value = "";
  qs("#resume-text").value = "";
  updateTextStats();
});

qs("#sample-job").addEventListener("click", () => {
  qs("#job-title").value = "ML Platform Engineer";
  qs("#preferred-skills").value = "Communication, Leadership, AWS";
  qs("#job-description").value =
    "Need Python, FastAPI, SQL, Docker, Kubernetes and Generative AI experience for an ML platform team. 3-5 years experience preferred with strong communication.";
  updateTextStats();
});

qs("#save-job").addEventListener("click", async (event) => {
  await withLoading(event.currentTarget, async () => {
    try {
      const job = await api("/api/v1/job/create", {
        method: "POST",
        body: JSON.stringify({
          title: qs("#job-title").value.trim(),
          description: qs("#job-description").value.trim(),
          preferred_skills: commaList(qs("#preferred-skills").value),
        }),
      });
      state.jobId = job.id;
      state.jobTitle = job.title;
      setStatus("#job-status", `Saved ${job.title}`);
      setOutput(job, "Job");
      await refreshLists();
      notify("Job saved");
      setStep("3");
    } catch (error) {
      setStatus("#job-status", error.message, false);
      notify(error.message, true);
    }
  });
});

qsa("[data-run]").forEach((button) => {
  button.addEventListener("click", async () => {
    await withLoading(button, async () => {
      try {
        await runAction(button.dataset.run);
      } catch (error) {
        setOutput(error.message, "Error");
        notify(error.message, true);
      }
    });
  });
});

qs("#run-all").addEventListener("click", async (event) => {
  await withLoading(event.currentTarget, async () => {
    try {
      for (const action of ["match", "rank", "gap", "questions", "predict"]) {
        await runAction(action);
      }
      setOutput(
        {
          match: state.lastResults.match,
          rank: state.lastResults.rank,
          gap: state.lastResults.gap,
          questions: state.lastResults.questions,
          prediction: state.lastResults.predict,
        },
        "Summary",
      );
      notify("Analysis complete");
    } catch (error) {
      setOutput(error.message, "Error");
      notify(error.message, true);
    }
  });
});

updateTextStats();
refreshLists().catch((error) => setOutput(error.message, "Error"));
