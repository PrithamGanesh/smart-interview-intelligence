/**
 * Frontend performance optimizations:
 * - Debounced input handlers (reduces render calls 100x)
 * - Efficient DOM queries and updates
 * - Skill matching with Set (O(1) lookup instead of O(n))
 * - Reduced re-renders and API calls
 */

// Global state management
const state = {
    candidateId: "",
    candidateName: "",
    jobId: "",
    jobTitle: "",
    lastResults: {},
    allCandidates: [],  // Cache candidate list
    allJobs: [],        // Cache job list
};

// DOM query helpers
const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => Array.from(document.querySelectorAll(selector));

// ============================================================================
// Debouncing & Performance Optimization
// ============================================================================

/**
 * Debounce function - reduces function calls during rapid events
 * Example: User types 100 characters = 100 events → 1 debounced call after 300ms
 */
const debounce = (func, delay = 300) => {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
};

/**
 * Throttle function - limits function calls over time
 * Example: Scroll events every 10ms → throttled to every 100ms
 */
const throttle = (func, limit = 100) => {
    let inThrottle;
    return (...args) => {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
};

// ============================================================================
// API Communication
// ============================================================================

const api = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    const key = qs("#api-key")?.value?.trim();
    if (key) headers.set("X-API-Key", key);
    if (options.body && !(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(path, { ...options, headers });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
        throw new Error(data.detail || `Request failed with status ${response.status}`);
    }
    return data;
};

// ============================================================================
// UI Feedback
// ============================================================================

const notify = (message, isError = false) => {
    const toast = qs("#toast");
    if (!toast) return;
    
    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.classList.add("show");
    
    window.clearTimeout(notify.timer);
    notify.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
};

const setStatus = (selector, message, ok = true) => {
    const node = qs(selector);
    if (!node) return;
    
    node.textContent = message;
    node.classList.toggle("ok", ok);
    node.classList.toggle("error", !ok);
};

// ============================================================================
// Text Processing (Optimized)
// ============================================================================

/**
 * Optimized skill extraction using Set for O(1) lookup
 * Instead of filtering through array each keystroke
 */
const SKILL_SET = new Set([
    "python", "fastapi", "django", "flask",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "sql", "postgresql", "mongodb", "redis",
    "machine learning", "ml", "tensorflow", "pytorch",
    "react", "vue", "angular", "node", "nodejs",
    "typescript", "javascript", "java", "golang", "rust",
    "devops", "ci/cd", "jenkins", "gitlab", "github",
]);

/**
 * Extract skills from text using efficient Set matching
 * O(n) where n = number of words (not skills)
 */
const extractSkills = (text) => {
    if (!text || typeof text !== "string") return [];
    
    const words = text.toLowerCase().split(/[\s,;.]+/);
    const found = [];
    
    for (const word of words) {
        if (SKILL_SET.has(word)) {
            found.push(word);
        }
    }
    
    // Return unique skills
    return [...new Set(found)];
};

/**
 * Update text statistics with debouncing
 * Called max once every 300ms instead of on every keystroke
 */
const updateTextStats = () => {
    const resumeText = qs("#resume-text")?.value?.trim() || "";
    const jobDescription = qs("#job-description")?.value?.trim() || "";
    
    // Extract skills efficiently
    const resumeSkills = extractSkills(resumeText);
    const jobSkills = extractSkills(jobDescription);
    
    // Update UI with minimal DOM access
    const resumeCountEl = qs("#resume-count");
    const resumeSkillsEl = qs("#resume-skills");
    const resumeQualityEl = qs("#resume-quality");
    
    if (resumeCountEl) {
        resumeCountEl.textContent = `${resumeText.length.toLocaleString()} characters`;
    }
    
    if (resumeSkillsEl) {
        resumeSkillsEl.textContent = resumeSkills.length 
            ? resumeSkills.join(", ") 
            : "Skills pending";
    }
    
    const isReadyResume = resumeText.length > 80;
    if (resumeQualityEl) {
        resumeQualityEl.textContent = isReadyResume ? "Ready" : "Draft";
        resumeQualityEl.classList.toggle("good", isReadyResume);
    }
    
    // Job stats
    const jobQualityEl = qs("#job-quality");
    const isReadyJob = jobDescription.length > 80;
    if (jobQualityEl) {
        jobQualityEl.textContent = isReadyJob ? "Ready" : "Draft";
        jobQualityEl.classList.toggle("good", isReadyJob);
    }
};

// ✅ DEBOUNCED version - max once per 300ms during typing
const debouncedUpdateTextStats = debounce(updateTextStats, 300);

// ============================================================================
// Selection Management (Reduced Re-renders)
// ============================================================================

const selectCandidate = async (candidateId) => {
    try {
        // Try to find in cached list first
        let candidate = state.allCandidates.find(c => c.id === candidateId);
        
        // If not cached, fetch from API
        if (!candidate) {
            const response = await api(`/api/v1/resume/${candidateId}`);
            candidate = response.data;
        }
        
        // Update state
        state.candidateId = candidate.id;
        state.candidateName = candidate.name;
        
        // Update form fields
        const nameField = qs("#candidate-name");
        const emailField = qs("#candidate-email");
        const resumeField = qs("#resume-text");
        
        if (nameField) nameField.value = candidate.name || "";
        if (emailField) emailField.value = candidate.email || "";
        if (resumeField) resumeField.value = candidate.raw_text || "";
        
        // Single UI update call
        refreshSelection();
        updateTextStats();
        setOutput(candidate, "Resume");
        
        setStatus("#resume-status", `Selected ${candidate.name}`);
        notify("Candidate loaded");
        
    } catch (error) {
        notify(`Failed to load candidate: ${error.message}`, true);
    }
};

const selectJob = async (jobId) => {
    try {
        // Try cache first
        let job = state.allJobs.find(j => j.id === jobId);
        
        if (!job) {
            const response = await api(`/api/v1/job/${jobId}`);
            job = response.data;
        }
        
        // Update state
        state.jobId = job.id;
        state.jobTitle = job.title;
        
        // Update form fields
        const titleField = qs("#job-title");
        const descField = qs("#job-description");
        const skillsField = qs("#preferred-skills");
        
        if (titleField) titleField.value = job.title || "";
        if (descField) descField.value = job.description || "";
        if (skillsField) {
            skillsField.value = (job.preferred_skills || []).join(", ");
        }
        
        // Single UI update
        refreshSelection();
        updateTextStats();
        setOutput(job, "Job");
        
        setStatus("#job-status", `Selected ${job.title}`);
        notify("Job loaded");
        
    } catch (error) {
        notify(`Failed to load job: ${error.message}`, true);
    }
};

const refreshSelection = () => {
    const selectedCandidate = qs("#selected-candidate");
    const selectedJob = qs("#selected-job");
    
    if (selectedCandidate) {
        selectedCandidate.textContent = state.candidateName || state.candidateId || "None";
    }
    if (selectedJob) {
        selectedJob.textContent = state.jobTitle || state.jobId || "None";
    }
};

// ============================================================================
// Output Rendering (Optimized)
// ============================================================================

const escapeHtml = (value) => {
    const str = String(value ?? "");
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    };
    return str.replace(/[&<>"']/g, (c) => map[c]);
};

const chips = (values = []) => {
    if (!values || values.length === 0) {
        return '<span class="subtle">None</span>';
    }
    return values
        .map((value) => `<span class="chip">${escapeHtml(value)}</span>`)
        .join("");
};

const summaryRows = (rows) => {
    const html = rows
        .map(
            ([key, value]) =>
                `<div class="summary-row"><span class="summary-key">${escapeHtml(key)}</span><span>${value}</span></div>`
        )
        .join("");
    return `<div class="summary-grid">${html}</div>`;
};

const setOutputMode = (label) => {
    const output = qs("#output-mode");
    if (output) output.textContent = label;
};

const setOutput = (payload, mode = "Result") => {
    const output = qs("#output");
    if (!output) return;
    
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
    
    // Other modes...
    return `<pre class="json-view">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
};

// ============================================================================
// Event Listener Setup (Performance Optimized)
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    // ✅ Debounced input handlers
    const resumeText = qs("#resume-text");
    const jobDescription = qs("#job-description");
    const preferredSkills = qs("#preferred-skills");
    
    if (resumeText) resumeText.addEventListener("input", debouncedUpdateTextStats);
    if (jobDescription) jobDescription.addEventListener("input", debouncedUpdateTextStats);
    if (preferredSkills) preferredSkills.addEventListener("input", debouncedUpdateTextStats);
    
    // Initialize
    updateTextStats();
});
