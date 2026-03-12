let navState = {
  groupEls: [],
  fileEls: [],
  activeFileIndex: -1,
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
  const filesByPath = new Map((data.files || []).map((f) => [f.path, f]));
  const groupsRoot = document.getElementById("groups");
  groupsRoot.innerHTML = "";

  for (const group of data.groups || []) {
    const details = document.createElement("details");
    details.className = "group";
    details.open = (group.risk || "") === "high";

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

      const patch = document.createElement("pre");
      patch.className = "patch";
      patch.textContent = (file.patch || "").trim() || "No line-level patch available";

      fileCard.append(header, patch);
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
  navState.groupEls = Array.from(document.querySelectorAll("#groups details.group"));
  navState.fileEls = Array.from(document.querySelectorAll("#groups .file-card"));
  navState.activeFileIndex = navState.fileEls.length ? 0 : -1;

  navState.fileEls.forEach((el, index) => {
    el.addEventListener("click", () => setActiveFile(index));
    el.addEventListener("focus", () => setActiveFile(index, false));
  });

  if (navState.activeFileIndex >= 0) {
    setActiveFile(navState.activeFileIndex, false);
  }
}

function setActiveFile(index, scroll = true) {
  if (index < 0 || index >= navState.fileEls.length) return;

  navState.fileEls.forEach((el) => el.classList.remove("active"));
  const current = navState.fileEls[index];
  current.classList.add("active");
  navState.activeFileIndex = index;

  const group = current.closest("details.group");
  if (group) group.open = true;

  if (scroll) {
    current.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function moveFile(step) {
  if (!navState.fileEls.length) return;
  const next = Math.max(0, Math.min(navState.fileEls.length - 1, navState.activeFileIndex + step));
  setActiveFile(next);
}

function groupForActiveFile() {
  if (navState.activeFileIndex < 0 || !navState.fileEls.length) return null;
  return navState.fileEls[navState.activeFileIndex].closest("details.group");
}

function moveGroup(step) {
  if (!navState.groupEls.length) return;

  const activeGroup = groupForActiveFile();
  let currentIndex = 0;
  if (activeGroup) {
    currentIndex = navState.groupEls.indexOf(activeGroup);
  }

  const nextGroupIndex = Math.max(0, Math.min(navState.groupEls.length - 1, currentIndex + step));
  const nextGroup = navState.groupEls[nextGroupIndex];
  nextGroup.open = true;

  const firstFile = nextGroup.querySelector(".file-card");
  if (!firstFile) return;

  const nextFileIndex = navState.fileEls.indexOf(firstFile);
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
  const visible = typeof forceVisible === "boolean" ? forceVisible : overlay.classList.contains("hidden");

  overlay.classList.toggle("hidden", !visible);
  overlay.setAttribute("aria-hidden", visible ? "false" : "true");
}

function bindShortcuts() {
  const helpButton = document.getElementById("shortcut-help-btn");
  const overlay = document.getElementById("shortcut-overlay");

  helpButton.addEventListener("click", () => toggleShortcutOverlay());
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      toggleShortcutOverlay(false);
    }
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
  renderSummary(data);
  renderGroups(data);
  renderRiskSidebar(data);
  renderRelatedFiles(data);
  bindShortcuts();
}

bootstrap().catch((error) => {
  document.body.innerHTML = `<pre style="padding: 1rem; color: #8f1d21;">Failed to load AgentDiff data: ${error}</pre>`;
});
