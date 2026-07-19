/* Connor's Deck — UI */
(() => {
  "use strict";

  const grid = document.getElementById("app-grid");
  const greetingEl = document.getElementById("greeting");
  const versionPill = document.getElementById("version-pill");
  const clockPill = document.getElementById("clock-pill");
  const refreshedEl = document.getElementById("refreshed");
  const toastHost = document.getElementById("toast-host");
  const btnRefresh = document.getElementById("btn-refresh");
  const btnUpdateAll = document.getElementById("btn-update-all");
  const helpDialog = document.getElementById("help-dialog");
  const livePill = document.getElementById("live-pill");

  /** @type {Array<any>} */
  let apps = [];
  let busyIds = new Set();

  function hourGreeting() {
    const h = new Date().getHours();
    if (h < 12) return "Good morning, Connor";
    if (h < 17) return "Hey Connor";
    if (h < 21) return "Good evening, Connor";
    return "Late session, Connor";
  }

  function tickClock() {
    const d = new Date();
    clockPill.textContent = d.toLocaleTimeString("en-ZA", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function toast(message, kind = "ok") {
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.textContent = message;
    toastHost.appendChild(el);
    setTimeout(() => {
      el.remove();
    }, 3800);
  }

  function statusLabel(status) {
    const map = {
      online: "Online",
      offline: "Offline",
      installed: "Ready",
      not_installed: "Not installed",
      coming_soon: "Coming soon",
      unknown: "Unknown",
    };
    return map[status] || status;
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      ...options,
    });
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = { ok: false, error: "Bad response from Deck server" };
    }
    if (!res.ok && data && !data.error) {
      data.error = `HTTP ${res.status}`;
    }
    return data;
  }

  function setCardBusy(id, on) {
    if (on) busyIds.add(id);
    else busyIds.delete(id);
    const card = grid.querySelector(`[data-app-id="${id}"]`);
    if (card) card.classList.toggle("busy", on);
  }

  function renderBerth(tease, index) {
    const card = document.createElement("article");
    card.className = "card berth";
    card.style.animationDelay = `${0.05 * (apps.length + index)}s`;
    card.innerHTML = `
      <div class="berth-icon" aria-hidden="true">◇</div>
      <div class="berth-title">Empty berth</div>
      <div class="berth-sub">${escapeHtml(tease || "Coming online")}</div>
    `;
    return card;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCard(app, index) {
    const card = document.createElement("article");
    const planned = app.state === "planned" || app.status === "coming_soon";
    card.className = `card${planned ? " planned" : ""}`;
    card.dataset.appId = app.id;
    card.style.setProperty("--card-accent", app.accent || "#a78bfa");
    card.style.animationDelay = `${0.05 * index}s`;
    if (busyIds.has(app.id)) card.classList.add("busy");

    const versionBits = [];
    if (app.version) versionBits.push(`v${app.version}`);
    if (app.gitSha) versionBits.push(app.gitSha);
    if (app.installPath) {
      const short = String(app.installPath).replace(/^\/Users\/[^/]+/, "~");
      versionBits.push(short);
    }
    const versionLine = versionBits.length
      ? versionBits.join(" · ")
      : planned
        ? "Reserved slot"
        : "—";

    const canLaunch = !!app.canLaunch;
    const canStop = !!app.canStop;
    const canUpdate = !!app.canUpdate;
    const launchLabel =
      app.status === "online" ? "Open" : app.state === "external" ? "Play" : "Launch";

    card.innerHTML = `
      <div class="card-top">
        <div class="icon-wrap" aria-hidden="true">${escapeHtml(app.emoji || "◆")}</div>
        <div class="meta">
          <span class="vibe">${escapeHtml(app.vibe || "")}</span>
          <span class="status ${escapeHtml(app.status || "")}">
            <span class="led" aria-hidden="true"></span>
            ${escapeHtml(statusLabel(app.status))}
          </span>
        </div>
      </div>
      <div class="card-body">
        <h2>${escapeHtml(app.name || app.id)}</h2>
        <p>${escapeHtml(app.tagline || "")}</p>
        ${
          planned && app.tease
            ? `<p class="tease">${escapeHtml(app.tease)}</p>`
            : ""
        }
        <div class="version-line">${escapeHtml(versionLine)}</div>
      </div>
      <div class="card-actions">
        <button type="button" class="btn primary small" data-action="launch" ${
          canLaunch ? "" : "disabled"
        }>${launchLabel}</button>
        <button type="button" class="btn ghost small" data-action="update" ${
          canUpdate ? "" : "disabled"
        }>Update</button>
        <button type="button" class="btn ghost small" data-action="stop" ${
          canStop ? "" : "disabled"
        }>Stop</button>
      </div>
    `;

    card.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.getAttribute("data-action");
        if (action === "launch") void runLaunch(app);
        if (action === "update") void runUpdate(app);
        if (action === "stop") void runStop(app);
      });
    });

    return card;
  }

  function paint(payload) {
    apps = (payload.apps || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0));
    const slots = payload.slots || 6;
    const teases = payload.emptySlotTeases || [];
    const deck = payload.deck || {};

    if (deck.version) {
      versionPill.textContent = `v${deck.version}${deck.gitSha ? " · " + deck.gitSha : ""}`;
    }

    grid.innerHTML = "";
    grid.setAttribute("aria-busy", "false");
    apps.forEach((app, i) => grid.appendChild(renderCard(app, i)));

    const emptyCount = Math.max(0, slots - apps.length);
    for (let i = 0; i < emptyCount; i++) {
      grid.appendChild(renderBerth(teases[i] || "Next build", i));
    }

    refreshedEl.textContent = `Refreshed ${new Date().toLocaleTimeString("en-ZA")}`;
    livePill.textContent = "DECK LIVE";
  }

  async function refresh() {
    try {
      const data = await api("/api/apps");
      if (!data.ok && data.error) throw new Error(data.error);
      paint(data);
    } catch (err) {
      grid.innerHTML = `
        <div class="loading-card">
          Could not reach the Deck control plane.<br/>
          <span style="opacity:.7">${escapeHtml(err.message || String(err))}</span><br/><br/>
          Open via <strong>Connor's Deck.command</strong> (not as a plain file) so the API is available.
        </div>`;
      livePill.textContent = "OFFLINE";
      toast("Deck API unavailable", "err");
    }
  }

  async function runLaunch(app) {
    setCardBusy(app.id, true);
    try {
      const data = await api(`/api/apps/${encodeURIComponent(app.id)}/launch`, {
        method: "POST",
        body: "{}",
      });
      if (!data.ok) throw new Error(data.error || "Launch failed");
      toast(data.message || `Launching ${app.name}`);
      // Give launch.sh a moment, then refresh status / soft-open URL
      if (data.url) {
        setTimeout(() => {
          window.open(data.url, "_blank", "noopener");
        }, 500);
      }
      setTimeout(() => void refresh(), 900);
    } catch (err) {
      toast(err.message || String(err), "err");
    } finally {
      setCardBusy(app.id, false);
    }
  }

  async function runStop(app) {
    setCardBusy(app.id, true);
    try {
      const data = await api(`/api/apps/${encodeURIComponent(app.id)}/stop`, {
        method: "POST",
        body: "{}",
      });
      if (!data.ok) throw new Error(data.error || "Stop failed");
      toast(data.message || `Stopped ${app.name}`);
      await refresh();
    } catch (err) {
      toast(err.message || String(err), "err");
    } finally {
      setCardBusy(app.id, false);
    }
  }

  async function runUpdate(app) {
    setCardBusy(app.id, true);
    toast(`Updating ${app.name}…`);
    try {
      const data = await api(`/api/apps/${encodeURIComponent(app.id)}/update`, {
        method: "POST",
        body: "{}",
      });
      if (!data.ok) throw new Error(data.error || "Update failed");
      toast(data.message || `Updated ${app.name}`);
      await refresh();
    } catch (err) {
      toast(err.message || String(err), "err");
    } finally {
      setCardBusy(app.id, false);
    }
  }

  async function runUpdateAll() {
    btnUpdateAll.disabled = true;
    toast("Updating all apps…");
    try {
      const data = await api("/api/update-all", { method: "POST", body: "{}" });
      if (!data.ok) throw new Error(data.error || "Update all failed");
      const results = data.results || [];
      const failed = results.filter((r) => r.ok === false);
      const updated = results.filter((r) => r.ok && !r.skipped);
      if (failed.length) {
        toast(`${failed.length} update(s) failed`, "err");
      } else if (updated.length) {
        toast(`Updated ${updated.length} app(s)`);
      } else {
        toast("Nothing to update");
      }
      await refresh();
    } catch (err) {
      toast(err.message || String(err), "err");
    } finally {
      btnUpdateAll.disabled = false;
    }
  }

  function launchableApps() {
    return apps.filter((a) => a.canLaunch);
  }

  function onKey(e) {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA") return;

    if (e.key === "?" || (e.shiftKey && e.key === "/")) {
      e.preventDefault();
      helpDialog.showModal();
      return;
    }
    if (e.key === "Escape" && helpDialog.open) {
      helpDialog.close();
      return;
    }
    if (e.key === "r" || e.key === "R") {
      e.preventDefault();
      void refresh();
      return;
    }
    if (e.key === "u" || e.key === "U") {
      e.preventDefault();
      void runUpdateAll();
      return;
    }
    if (/^[1-4]$/.test(e.key)) {
      const idx = Number(e.key) - 1;
      const list = launchableApps();
      // Prefer order of all apps: map number keys to first N apps that can launch
      // by grid order of apps array, not only launchable-only list length confusion
      const ordered = apps.filter((a) => a.canLaunch);
      const app = ordered[idx];
      if (app) {
        e.preventDefault();
        void runLaunch(app);
      }
    }
  }

  // init
  greetingEl.textContent = hourGreeting();
  tickClock();
  setInterval(tickClock, 30_000);
  btnRefresh.addEventListener("click", () => void refresh());
  btnUpdateAll.addEventListener("click", () => void runUpdateAll());
  document.addEventListener("keydown", onKey);
  void refresh();
  // No auto-poll: full refresh every N seconds rebuilt the whole grid and felt
  // like constant reloading. Status updates on open, after Launch/Stop/Update,
  // and when Connor hits Refresh / R.
})();
