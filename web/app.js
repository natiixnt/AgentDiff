const STORAGE_PREFIX = "agentdiff.reviewState.v1";

const appState = {
  analysis: null,
  storageKey: null,
  persistTimer: null,
  ui: {
    collapsedGroups: {},
    visitedFiles: {},
    notes: {},
    activeFilePath: null,
  },
  nav: {
    groupEls: [],
    fileEls: [],
    activeFileIndex: -1,
  },
};

function makeCard(label, value) {
  const card = document.createElement("div");
  card.className = "card";

  const labelEl = document.createElement("div");
  labelEl.className = "card-label";
  labelEl.textContent = label;

  const valueEl = document.createElement("div");
  valueEl.className = "card-value";
  valueEl.textContent = String(value);

  card.append(labelEl, valueEl);
  return card;
}

function riskBadge(level) {
  const el = document.createElement("span");
  el.className = `badge ${level}`;
  el.textContent = level;
  return el;
}

function computeStorageKey(data) {
  const paths = (data.files || []).map((file) => file.path).join("|");
  return `${STORAGE_PREFIX}:${paths}`;
}

function loadUiState() {
  if (!appState.storageKey) return;
  try {
    const raw = window.localStorage.getItem(appState.storageKey);
    if (!raw) return;

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return;

    appState.ui.collapsedGroups = parsed.collapsedGroups && typeof parsed.collapsedGroups === "object"
      ? parsed.collapsedGroups
      : {};
    appState.ui.visitedFiles = parsed.visitedFiles && typeof parsed.visitedFiles === "object"
      ? parsed.visitedFiles
      : {};
    appState.ui.notes = parsed.notes && typeof parsed.notes === "object"
      ? parsed.notes
      : {};
    appState.ui.activeFilePath = typeof parsed.activeFilePath === "string" ? parsed.activeFilePath : null;
  } catch (_error) {
    // Ignore corrupt/inaccessible localStorage state and continue with defaults.
  }
}

function persistUiState() {
  if (!appState.storageKey) return;
  try {
    window.localStorage.setItem(
      appState.storageKey,
      JSON.stringify({
        collapsedGroups: appState.ui.collapsedGroups,
        visitedFiles: appState.ui.visitedFiles,
        notes: appState.ui.notes,
        activeFilePath: appState.ui.activeFilePath,
      })
    );
  } catch (_error) {
    // Ignore storage quota/access failures in local mode.
  }
}

function schedulePersist() {
  if (appState.persistTimer) {
    clearTimeout(appState.persistTimer);
  }
  appState.persistTimer = window.setTimeout(persistUiState, 140);
}

function resetUiState() {
  if (!appState.storageKey) return;
  try {
    window.localStorage.removeItem(appState.storageKey);
  } catch (_error) {
    // Ignore localStorage failures.
  }

  appState.ui = {
    collapsedGroups: {},
    visitedFiles: {},
    notes: {},
    activeFilePath: null,
  };

  if (appState.analysis) {
    renderSummary(appState.analysis);
    renderGroups(appState.analysis);
    renderRiskSidebar(appState.analysis);
    renderRelatedFiles(appState.analysis);
  }
}

function signalLabel(pattern, confidence) {
  return `${pattern} ${confidence.toFixed(2)}`;
}

function renderSummary(data) {
  const summary = data.summary || {};
  const cards = document.getElementById("summary-cards");
  cards.innerHTML = "";
  cards.append(
    makeCard("Files", summary.total_files || 0),
    makeCard("Groups", summary.total_groups || 0),
    makeCard("Additions", summary.total_additions || 0),
    makeCard("Deletions", summary.total_deletions || 0),
    makeCard("High Risk", (summary.risk_levels || {}).high || 0),
    makeCard("Behavior Changes", (summary.change_types || {}).behavior_change || 0)
  );

  const reviewList = document.getElementById("review-order");
  reviewList.innerHTML = "";
  for (const item of data.review_order || []) {
    const li = document.createElement("li");
    li.innerHTML = `<code>${item.path}</code> <small>(${item.reason}; risk: ${item.risk})</small>`;
    reviewList.appendChild(li);
  }

  const driftList = document.getElementById("plan-drift");
  driftList.innerHTML = "";

  const drift = data.plan_drift || {};
  if (!drift.has_plan) {
    const li = document.createElement("li");
    li.textContent = "No execution plan provided.";
    driftList.appendChild(li);
    return;
  }

  if (!drift.planned_but_unchanged_count && !drift.changed_but_unplanned_count) {
    const li = document.createElement("li");
    li.textContent = "No drift detected between plan and diff.";
    driftList.appendChild(li);
    return;
  }

  const counts = document.createElement("li");
  counts.innerHTML = `<strong>${drift.planned_but_unchanged_count}</strong> planned-but-unchanged · <strong>${drift.changed_but_unplanned_count}</strong> changed-but-unplanned`;
  driftList.appendChild(counts);

  for (const path of drift.planned_but_unchanged || []) {
    const li = document.createElement("li");
    li.innerHTML = `<code>${path}</code> planned but unchanged`;
    driftList.appendChild(li);
  }

  for (const path of drift.changed_but_unplanned || []) {
    const li = document.createElement("li");
    li.innerHTML = `<code>${path}</code> changed but not in plan`;
    driftList.appendChild(li);
  }
}

function renderGroups(data) {
  const filesByPath = new Map((data.files || []).map((file) => [file.path, file]));
  const groupsRoot = document.getElementById("groups");
  groupsRoot.innerHTML = "";

  for (const group of data.groups || []) {
    const details = document.createElement("details");
    details.className = "group";
    details.dataset.groupId = group.id;

    const storedCollapsed = appState.ui.collapsedGroups[group.id];
    if (typeof storedCollapsed === "boolean") {
      details.open = !storedCollapsed;
    } else {
      details.open = (group.risk || "") === "high";
    }

    details.addEventListener("toggle", () => {
      appState.ui.collapsedGroups[group.id] = !details.open;
      schedulePersist();
    });

    const summary = document.createElement("summary");
    const title = document.createElement("span");
    title.className = "group-title";
    title.textContent = group.title;

    const meta = document.createElement("span");
    meta.className = "group-meta";
    meta.textContent = `${group.files.length} files · ${group.risk} risk`;

    summary.append(title, meta);
    details.appendChild(summary);

    for (const filePath of group.files) {
      const file = filesByPath.get(filePath);
      if (!file) continue;

      const fileCard = document.createElement("div");
      fileCard.className = "file-card";
      fileCard.dataset.filePath = file.path;
      fileCard.tabIndex = 0;
      if (appState.ui.visitedFiles[file.path]) {
        fileCard.classList.add("visited");
      }

      const header = document.createElement("div");
      header.className = "file-header";

      const path = document.createElement("span");
      path.className = "file-path";
      path.textContent = file.path;

      const status = document.createElement("span");
      status.className = "badge";
      status.textContent = file.status;

      const type = document.createElement("span");
      type.className = "badge";
      type.textContent = file.change_type;

      const facets = document.createElement("span");
      facets.className = "badge";
      facets.textContent = (file.change_facets || []).join(", ");

      const risk = riskBadge(file.risk_level);
      header.append(path, status, type, facets, risk);

      const signalRow = document.createElement("div");
      signalRow.className = "pattern-signals";
      const confidence = file.pattern_confidence || {};
      const patternNames = Object.keys(confidence).sort();
      if (patternNames.length) {
        for (const pattern of patternNames) {
          const value = Number(confidence[pattern]);
          const signal = document.createElement("span");
          signal.className = "signal";
          signal.textContent = signalLabel(pattern, Number.isFinite(value) ? value : 0);
          signalRow.appendChild(signal);
        }
      }

      const patch = document.createElement("pre");
      patch.className = "patch";
      patch.textContent = (file.patch || "").trim() || "No line-level patch available";

      const noteWrap = document.createElement("div");
      noteWrap.className = "note-wrap";

      const noteLabel = document.createElement("label");
      noteLabel.className = "note-label";
      noteLabel.textContent = "Reviewer note";

      const noteInput = document.createElement("textarea");
      noteInput.className = "note-input";
      noteInput.placeholder = "Optional note for this file";
      noteInput.value = appState.ui.notes[file.path] || "";
      noteInput.addEventListener("input", () => {
        const text = noteInput.value;
        if (text.trim()) {
          appState.ui.notes[file.path] = text;
        } else {
          delete appState.ui.notes[file.path];
        }
        schedulePersist();
      });

      noteWrap.append(noteLabel, noteInput);
      fileCard.append(header, signalRow, patch, noteWrap);
      details.appendChild(fileCard);
    }

    groupsRoot.appendChild(details);
  }

  refreshNavigationState();
}

function renderRiskSidebar(data) {
  const root = document.getElementById("risk-list");
  root.innerHTML = "";

  const sorted = [...(data.files || [])].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));
  for (const file of sorted) {
    const li = document.createElement("li");
    li.className = "risk-item";

    const title = document.createElement("div");
    title.className = "risk-title";
    title.textContent = file.path;

    const badge = riskBadge(file.risk_level || "low");

    const reasons = document.createElement("div");
    reasons.className = "risk-reasons";
    reasons.textContent = (file.risk_reasons || []).join("; ") || "No major risk signals.";

    li.append(title, badge, reasons);
    root.appendChild(li);
  }
}

function renderRelatedFiles(data) {
  const root = document.getElementById("related-files");
  root.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "related-grid";

  for (const file of data.files || []) {
    const wrap = document.createElement("div");
    wrap.className = "related-item";

    const path = document.createElement("p");
    path.className = "related-path";
    path.textContent = file.path;

    const list = document.createElement("ul");
    list.className = "related-links";

    const related = file.related_files || [];
    if (!related.length) {
      const li = document.createElement("li");
      li.textContent = "No related files detected";
      list.appendChild(li);
    } else {
      for (const rel of related) {
        const li = document.createElement("li");
        li.textContent = rel;
        list.appendChild(li);
      }
    }

    wrap.append(path, list);
    grid.appendChild(wrap);
  }

  root.appendChild(grid);
}

function refreshNavigationState() {
  appState.nav.groupEls = Array.from(document.querySelectorAll("#groups details.group"));
  appState.nav.fileEls = Array.from(document.querySelectorAll("#groups .file-card"));

  const savedPath = appState.ui.activeFilePath;
  let nextIndex = appState.nav.fileEls.length ? 0 : -1;
  if (savedPath) {
    const foundIndex = appState.nav.fileEls.findIndex((el) => el.dataset.filePath === savedPath);
    if (foundIndex >= 0) {
      nextIndex = foundIndex;
    }
  }

  appState.nav.activeFileIndex = nextIndex;

  appState.nav.fileEls.forEach((el, index) => {
    el.addEventListener("click", () => setActiveFile(index));
    el.addEventListener("focus", () => setActiveFile(index, false));
  });

  if (appState.nav.activeFileIndex >= 0) {
    setActiveFile(appState.nav.activeFileIndex, false);
  }
}

function setActiveFile(index, scroll = true) {
  if (index < 0 || index >= appState.nav.fileEls.length) return;

  appState.nav.fileEls.forEach((el) => el.classList.remove("active"));
  const current = appState.nav.fileEls[index];
  current.classList.add("active");
  appState.nav.activeFileIndex = index;

  const path = current.dataset.filePath || null;
  if (path) {
    appState.ui.activeFilePath = path;
    appState.ui.visitedFiles[path] = true;
    current.classList.add("visited");
    schedulePersist();
  }

  const group = current.closest("details.group");
  if (group) {
    group.open = true;
  }

  if (scroll) {
    current.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function moveFile(step) {
  if (!appState.nav.fileEls.length) return;
  const next = Math.max(
    0,
    Math.min(appState.nav.fileEls.length - 1, appState.nav.activeFileIndex + step)
  );
  setActiveFile(next);
}

function groupForActiveFile() {
  if (appState.nav.activeFileIndex < 0 || !appState.nav.fileEls.length) return null;
  return appState.nav.fileEls[appState.nav.activeFileIndex].closest("details.group");
}

function moveGroup(step) {
  if (!appState.nav.groupEls.length) return;

  const activeGroup = groupForActiveFile();
  let currentIndex = 0;
  if (activeGroup) {
    currentIndex = appState.nav.groupEls.indexOf(activeGroup);
  }

  const nextGroupIndex = Math.max(0, Math.min(appState.nav.groupEls.length - 1, currentIndex + step));
  const nextGroup = appState.nav.groupEls[nextGroupIndex];
  nextGroup.open = true;

  const firstFile = nextGroup.querySelector(".file-card");
  if (!firstFile) return;

  const nextFileIndex = appState.nav.fileEls.indexOf(firstFile);
  if (nextFileIndex >= 0) {
    setActiveFile(nextFileIndex);
  }
}

function toggleActiveGroup() {
  const group = groupForActiveFile();
  if (!group) return;
  group.open = !group.open;
}

function toggleShortcutOverlay(forceVisible) {
  const overlay = document.getElementById("shortcut-overlay");
  const visible =
    typeof forceVisible === "boolean" ? forceVisible : overlay.classList.contains("hidden");

  overlay.classList.toggle("hidden", !visible);
  overlay.setAttribute("aria-hidden", visible ? "false" : "true");
}

function bindControls() {
  const helpButton = document.getElementById("shortcut-help-btn");
  const overlay = document.getElementById("shortcut-overlay");
  const resetButton = document.getElementById("reset-state-btn");

  helpButton.addEventListener("click", () => toggleShortcutOverlay());
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      toggleShortcutOverlay(false);
    }
  });

  resetButton.addEventListener("click", () => {
    const confirmed = window.confirm("Reset saved review state for this diff view?");
    if (!confirmed) return;
    resetUiState();
  });

  window.addEventListener("keydown", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      return;
    }

    if (event.key === "?") {
      event.preventDefault();
      toggleShortcutOverlay();
      return;
    }

    if (event.key === "Escape") {
      toggleShortcutOverlay(false);
      return;
    }

    if (event.key === "j") {
      event.preventDefault();
      moveFile(1);
      return;
    }

    if (event.key === "k") {
      event.preventDefault();
      moveFile(-1);
      return;
    }

    if (event.key === "]") {
      event.preventDefault();
      moveGroup(1);
      return;
    }

    if (event.key === "[") {
      event.preventDefault();
      moveGroup(-1);
      return;
    }

    if (event.key === "o") {
      event.preventDefault();
      toggleActiveGroup();
    }
  });
}

async function bootstrap() {
  const response = await fetch("/api/analysis");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data = await response.json();
  appState.analysis = data;
  appState.storageKey = computeStorageKey(data);
  loadUiState();

  renderSummary(data);
  renderGroups(data);
  renderRiskSidebar(data);
  renderRelatedFiles(data);
  bindControls();
}

bootstrap().catch((error) => {
  document.body.innerHTML = `<pre style="padding: 1rem; color: #8f1d21;">Failed to load AgentDiff data: ${error}</pre>`;
});
