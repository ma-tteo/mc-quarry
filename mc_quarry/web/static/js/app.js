/* ==========================================================================
   MC Quarry — Web UI client logic
   Handles: Socket.IO events, tabs, theme, config editor, log console,
            toasts, progress, stats. No external libs except socket.io.
   ========================================================================== */

(function () {
    "use strict";

    /* ---------- Constants ---------- */
    // Minecraft version pattern — mirrors main.py:MC_VERSION_PATTERN
    const MC_VERSION_RE = /^\d+\.\d+(\.\d+)?([+-][a-zA-Z0-9.]+)?$/;
    const MAX_LOG_ENTRIES = 500;
    const POLL_FALLBACK_MS = 10000;

    // Category key -> human label (must match backend CATEGORY_MAP keys)
    const CATEGORY_LABELS = {
        core_mods: "Core Mods",
        utility_mods: "Utility Mods",
        light_qol_mods: "Light QoL",
        curseforge_mods: "CurseForge Mods",
        texture_packs: "Texture Packs",
        curseforge_texture_packs: "CF Texture Packs",
    };

    // Editable config list keys (order matters for the config editor)
    const EDITABLE_LISTS = [
        "core_mods",
        "utility_mods",
        "light_qol_mods",
        "curseforge_mods",
        "texture_packs",
        "curseforge_texture_packs",
    ];

    /* ---------- State ---------- */
    const state = {
        socket: null,
        activeTab: "download",
        status: "idle",
        currentFilter: "all",
        searchQuery: "",
        autoScroll: true,
        logCount: 0,
        statsBefore: { installed: 0, updated: 0, skipped: 0, failed: 0, not_found: 0 },
        config: null,
        pollTimer: null,
    };

    /* ---------- DOM helpers ---------- */
    const $ = (id) => document.getElementById(id);
    const $$ = (sel) => document.querySelectorAll(sel);

    function el(tag, attrs = {}, ...children) {
        const node = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === "class") node.className = v;
            else if (k === "html") node.innerHTML = v;
            else if (k.startsWith("on") && typeof v === "function") {
                node.addEventListener(k.slice(2).toLowerCase(), v);
            } else if (v !== null && v !== undefined) node.setAttribute(k, v);
        }
        for (const c of children) {
            if (c == null) continue;
            node.append(c.nodeType ? c : document.createTextNode(String(c)));
        }
        return node;
    }

    /* ======================================================================
       THEME
       ====================================================================== */
    function initTheme() {
        const saved = localStorage.getItem("mcq-theme");
        const theme = saved || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
        applyTheme(theme);
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("mcq-theme", theme);
        const btn = $("themeToggle");
        if (btn) btn.innerHTML = theme === "dark" ? Icons.get("sun") : Icons.get("moon");
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        applyTheme(current === "dark" ? "light" : "dark");
    }

    /* ======================================================================
       NAVIGATION / TABS
       ====================================================================== */
    function switchTab(tab) {
        state.activeTab = tab;
        $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.tab === tab));
        $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${tab}`));
        if (tab === "config") loadConfig();
        if (tab === "system") loadHardware();
    }

    /* ======================================================================
       SOCKET.IO
       ====================================================================== */
    function initSocket() {
        state.socket = io();

        state.socket.on("connect", () => {
            setConnection(true);
            addLog("Connected to server", "success");
        });

        state.socket.on("disconnect", () => {
            setConnection(false);
            addLog("Disconnected from server", "error");
            // Fallback polling only when socket is down
            startFallbackPolling();
        });

        state.socket.on("log", (data) => addLog(data.message, data.level));
        state.socket.on("progress", (data) => updateProgress(data));
        state.socket.on("stats", (data) => updateStats(data));
        state.socket.on("complete", (data) => showSummary(data));
        state.socket.on("connected", () => setConnection(true));
    }

    function setConnection(online) {
        const ind = $("connectionIndicator");
        if (!ind) return;
        ind.classList.toggle("online", online);
        ind.classList.toggle("offline", !online);
        ind.querySelector(".connection-label").textContent = online ? "Online" : "Offline";
    }

    function startFallbackPolling() {
        if (state.pollTimer) return;
        state.pollTimer = setInterval(async () => {
            if (state.socket && state.socket.connected) {
                clearInterval(state.pollTimer);
                state.pollTimer = null;
                return;
            }
            try {
                const r = await fetch("/api/status");
                const data = await r.json();
                updateStatus(data.status);
            } catch { /* ignore */ }
        }, POLL_FALLBACK_MS);
    }

    /* ======================================================================
       LOG CONSOLE
       ====================================================================== */
    function addLog(message, level = "info") {
        const container = $("logContainer");
        if (!container) return;

        const time = new Date().toLocaleTimeString();
        const entry = el("div", { class: `log-entry log-${level}` },
            el("span", { class: "log-time" }, `[${time}]`),
            el("span", { class: "log-msg" }, message),
        );

        // Track level for filtering
        entry.dataset.level = level;
        entry.dataset.text = message.toLowerCase();

        // Apply current filter + search before inserting
        applyFiltersToEntry(entry);

        container.appendChild(entry);
        state.logCount++;

        // Cap entries (FIFO)
        while (state.logCount > MAX_LOG_ENTRIES) {
            const first = container.querySelector(".log-entry");
            if (!first) break;
            first.remove();
            state.logCount--;
        }

        if (state.autoScroll) container.scrollTop = container.scrollHeight;
    }

    function applyFiltersToEntry(entry) {
        const levelOk = state.currentFilter === "all" || entry.dataset.level === state.currentFilter;
        const searchOk = !state.searchQuery || entry.dataset.text.includes(state.searchQuery);
        entry.classList.toggle("hidden", !(levelOk && searchOk));
    }

    function reapplyFilters() {
        $$("#logContainer .log-entry").forEach(applyFiltersToEntry);
    }

    function setFilter(level) {
        state.currentFilter = level;
        $$(".filter-btn").forEach((b) => b.classList.toggle("active", b.dataset.filter === level));
        reapplyFilters();
    }

    function onSearch(e) {
        state.searchQuery = e.target.value.trim().toLowerCase();
        reapplyFilters();
    }

    function exportLog() {
        const entries = $$("#logContainer .log-entry:not(.hidden)");
        if (entries.length === 0) {
            showToast("warning", "Nothing to export", "The log is empty.");
            return;
        }
        const lines = Array.from(entries).map((e) => e.textContent.replace(/\s+/g, " ").trim());
        const blob = new Blob([lines.join("\n")], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = el("a", { href: url, download: `mc-quarry-log-${Date.now()}.txt` });
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function onLogScroll(e) {
        const c = e.target;
        const atBottom = c.scrollHeight - c.scrollTop - c.clientHeight < 30;
        // Only auto-flip the toggle when user scrolls; don't fight programmatic scroll
        if (state.autoScroll && !atBottom) {
            state.autoScroll = false;
            updateAutoScrollBtn();
        } else if (!state.autoScroll && atBottom) {
            state.autoScroll = true;
            updateAutoScrollBtn();
        }
    }

    function toggleAutoScroll() {
        state.autoScroll = !state.autoScroll;
        updateAutoScrollBtn();
        if (state.autoScroll) {
            const c = $("logContainer");
            c.scrollTop = c.scrollHeight;
        }
    }

    function updateAutoScrollBtn() {
        const btn = $("autoScrollBtn");
        if (!btn) return;
        btn.classList.toggle("active", state.autoScroll);
        btn.title = state.autoScroll ? "Auto-scroll: ON" : "Auto-scroll: OFF";
    }

    /* ======================================================================
       PROGRESS + STATS
       ====================================================================== */
    function updateProgress(data) {
        const { current, total, percentage, current_mod } = data;
        const fill = $("progressFill");
        const pct = Math.round(percentage || 0);
        fill.style.width = `${pct}%`;
        fill.textContent = pct > 0 ? `${pct}%` : "";

        $("progressBar").classList.toggle("running", state.status === "running" && pct < 100);
        $("progressText").textContent = `${current} / ${total} mods`;
        $("progressPct").textContent = `${pct}%`;
        $("processedBadge").textContent = `${current} processed / ${total} total`;

        const modEl = $("currentMod");
        if (current_mod) {
            $("currentModName").textContent = current_mod;
            modEl.style.display = "flex";
        } else if (pct >= 100) {
            modEl.style.display = "none";
        }
    }

    function updateStats(stats) {
        animateNumber("statInstalled", state.statsBefore.installed, stats.installed || 0);
        animateNumber("statUpdated", state.statsBefore.updated, stats.updated || 0);
        animateNumber("statSkipped", state.statsBefore.skipped, stats.skipped || 0);
        animateNumber("statFailed", state.statsBefore.failed, stats.failed || 0);
        animateNumber("statNotFound", state.statsBefore.not_found, stats.not_found || 0);
        state.statsBefore = { ...stats };
    }

    function animateNumber(id, from, to) {
        const node = $(id);
        if (!node || from === to) {
            if (node) node.textContent = to;
            return;
        }
        const duration = 400;
        const start = performance.now();
        const step = (now) => {
            const t = Math.min((now - start) / duration, 1);
            const val = Math.round(from + (to - from) * t);
            node.textContent = val;
            if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    function updateStatus(status) {
        state.status = status;
        const badge = $("statusBadge");
        // Map "connected" to a supported visual class
        const cls = status === "connected" ? "connected" : status;
        badge.className = `status-badge status-${cls}`;
        const labels = { idle: "Idle", running: "Running", complete: "Complete", error: "Error", connected: "Connected" };
        badge.innerHTML = `<span class="dot"></span> ${labels[status] || status}`;

        const running = status === "running";
        $("startBtn").disabled = running;
        $("stopBtn").disabled = !running;
    }

    /* ======================================================================
       DOWNLOAD CONTROL
       ====================================================================== */
    function getSelectedCategories() {
        const cats = [];
        $$("#categoryGroup input[type=checkbox]:checked").forEach((cb) => cats.push(cb.value));
        return cats;
    }

    async function startDownload() {
        const version = $("mcVersion").value.trim();
        const versionError = $("versionError");

        if (!MC_VERSION_RE.test(version)) {
            versionError.textContent = "Invalid format. Examples: 1.21, 1.21.1, 1.20.1-beta.3";
            $("mcVersion").classList.add("invalid");
            showToast("error", "Invalid version", "Please enter a valid Minecraft version.");
            return;
        }
        versionError.textContent = "";
        $("mcVersion").classList.remove("invalid");

        const categories = getSelectedCategories();
        if (categories.length === 0) {
            showToast("warning", "No categories", "Please select at least one mod category.");
            return;
        }

        addLog(`Starting download for MC ${version}…`, "info");
        updateStatus("running");

        try {
            const r = await fetch("/api/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ version, categories }),
            });
            const data = await r.json();
            if (!data.success) {
                addLog(`Error: ${data.error}`, "error");
                showToast("error", "Could not start", data.error || "Unknown error");
                updateStatus("idle");
            }
        } catch (err) {
            addLog(`Error: ${err.message}`, "error");
            showToast("error", "Request failed", err.message);
            updateStatus("idle");
        }
    }

    async function stopDownload() {
        addLog("Stopping download…", "warning");
        try {
            await fetch("/api/stop", { method: "POST" });
        } catch (err) {
            addLog(`Error: ${err.message}`, "error");
        }
    }

    /* ======================================================================
       SUMMARY MODAL (final report with per-mod failures)
       ====================================================================== */
    async function showSummary(summary) {
        const data = summary || await fetchJSON("/api/summary");
        if (!data) return;

        const { stats, failed = [], not_found = [], skipped_incompatible = 0 } = data;
        const totalFailed = (failed.length || 0) + (not_found.length || 0);

        // Refresh stats + status
        if (stats) updateStats(stats);
        updateStatus(totalFailed > 0 ? "complete" : "complete");

        const body = $("summaryBody");
        body.innerHTML = "";

        if (totalFailed === 0 && skipped_incompatible === 0) {
            body.appendChild(emptySummarySuccess(stats));
        } else {
            const ul = el("ul");
            failed.forEach(([name, reason]) => ul.appendChild(
                el("li", { class: "failed" },
                    el("div", { class: "mod-name" }, name),
                    el("div", { class: "mod-reason" }, reason || "download failed"),
                ),
            ));
            not_found.forEach((name) => ul.appendChild(
                el("li", { class: "not-found" },
                    el("div", { class: "mod-name" }, name),
                    el("div", { class: "mod-reason" }, "not found on the provider"),
                ),
            ));
            if (skipped_incompatible > 0) {
                ul.appendChild(el("li", { class: "not-found" },
                    el("div", { class: "mod-reason" }, `${skipped_incompatible} mod(s) skipped (incompatible/hardware)`),
                ));
            }
            body.appendChild(ul);
        }

        $("summaryModal").classList.add("active");
        showToast(
            totalFailed === 0 ? "success" : "warning",
            "Download finished",
            totalFailed === 0
                ? "All mods processed successfully."
                : `${totalFailed} issue(s) — see details.`,
        );
    }

    function emptySummarySuccess(stats) {
        const txt = stats
            ? `Installed ${stats.installed || 0} · Updated ${stats.updated || 0} · Up-to-date ${stats.skipped || 0}`
            : "All mods processed.";
        return el("div", { class: "empty-state", html: Icons.get("checkCircle") },
            el("p", {}, txt),
        );
    }

    function closeModal() {
        $("summaryModal").classList.remove("active");
    }

    /* ======================================================================
       CONFIG EDITOR
       ====================================================================== */
    async function loadConfig() {
        if (state.config) return; // cached
        try {
            const cfg = await fetchJSON("/api/config");
            if (!cfg) return;
            state.config = cfg;
            renderConfig(cfg);
        } catch (err) {
            showToast("error", "Config load failed", err.message);
        }
    }

    function renderConfig(cfg) {
        // Scalars
        $("cfgApiKey").value = cfg.curseforge_api_key === "***" ? "" : (cfg.curseforge_api_key || "");
        $("cfgLanguage").value = cfg.language || "en";
        $("cfgLightQol").checked = cfg.install_light_qol !== false;
        $("cfgModsFolder").value = cfg.mods_folder || "";
        $("cfgResourcepacksFolder").value = cfg.resourcepacks_folder || "";

        // Mod lists
        const host = $("modLists");
        host.innerHTML = "";
        for (const key of EDITABLE_LISTS) {
            host.appendChild(renderModList(key, cfg[key] || []));
        }

        // Read-only rules
        $("cfgIncompatible").textContent = JSON.stringify(cfg.incompatible_mods || {}, null, 2);
        $("cfgRequirements").textContent = JSON.stringify(cfg.requirements || {}, null, 2);
        $("cfgConflicts").textContent = JSON.stringify(cfg.conflicts || {}, null, 2);
    }

    function renderModList(key, items) {
        const section = el("div", { class: "config-section" });
        section.appendChild(el("h4", {}, CATEGORY_LABELS[key] || key));

        const list = el("div", { class: "mod-list-editor", id: `list-${key}` });
        items.forEach((m) => list.appendChild(modRow(key, m)));
        section.appendChild(list);

        const addRow = el("div", { class: "mod-list-add" });
        const input = el("input", { type: "text", placeholder: "Add mod name or slug…" });
        const addBtn = el("button", { class: "btn btn-sm btn-ghost", html: Icons.get("plus") + " Add", onclick: () => {
            const val = input.value.trim();
            if (!val) return;
            $(`list-${key}`).appendChild(modRow(key, val));
            input.value = "";
        } });
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addBtn.click(); } });
        addRow.append(input, addBtn);
        section.appendChild(addRow);

        return section;
    }

    function modRow(key, value) {
        const inp = el("input", { type: "text", value });
        return el("div", { class: "mod-list-item" },
            inp,
            el("button", {
                class: "btn btn-icon btn-ghost",
                html: Icons.get("trash"),
                title: "Remove",
                onclick: (e) => e.target.closest(".mod-list-item").remove(),
            }),
        );
    }

    function collectConfig() {
        const cfg = {
            curseforge_api_key: $("cfgApiKey").value,
            language: $("cfgLanguage").value,
            install_light_qol: $("cfgLightQol").checked,
            mods_folder: $("cfgModsFolder").value,
            resourcepacks_folder: $("cfgResourcepacksFolder").value,
        };
        for (const key of EDITABLE_LISTS) {
            cfg[key] = Array.from($$(`#list-${key} input[type=text]`))
                .map((i) => i.value.trim())
                .filter(Boolean);
        }
        return cfg;
    }

    async function saveConfig() {
        const btn = $("saveConfigBtn");
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner"></span> Saving…`;
        try {
            const r = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(collectConfig()),
            });
            const data = await r.json();
            if (data.success) {
                state.config = null; // invalidate cache
                showToast("success", "Saved", "Configuration updated.");
            } else {
                showToast("error", "Save failed", data.error || "Unknown error");
            }
        } catch (err) {
            showToast("error", "Save failed", err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    }

    /* ======================================================================
       SYSTEM / HARDWARE VIEW
       ====================================================================== */
    async function loadHardware() {
        const host = $("hwGrid");
        if (host.dataset.loaded === "1") return;
        host.innerHTML = `<div class="empty-state"><div class="spinner" style="margin:0 auto"></div><p style="margin-top:10px">Detecting hardware…</p></div>`;
        try {
            const hw = await fetchJSON("/api/hardware");
            if (!hw) return;
            host.innerHTML = "";
            host.appendChild(hwCard("cpu", "CPU Cores", `${hw.cpu_cores} cores`));
            host.appendChild(hwCard("monitor", "GPU", capitalize(hw.gpu || "generic")));
            host.dataset.loaded = "1";
        } catch (err) {
            host.innerHTML = `<div class="empty-state" html="${Icons.get("alertTriangle")}"><p>Could not detect hardware.</p></div>`;
        }
    }

    function hwCard(icon, label, value) {
        return el("div", { class: "hw-card", html: Icons.get(icon) },
            el("div", {},
                el("div", { class: "hw-label" }, label),
                el("div", { class: "hw-value" }, value),
            ),
        );
    }

    /* ======================================================================
       TOASTS
       ====================================================================== */
    function showToast(type, title, message, timeout = 5000) {
        const host = $("toastContainer");
        const icon = { success: "checkCircle", error: "xCircle", warning: "alertTriangle", info: "info" }[type] || "info";
        const toast = el("div", { class: `toast ${type}`, role: "alert" },
            el("span", { html: Icons.get(icon) }),
            el("div", { class: "toast-content" },
                el("div", { class: "toast-title" }, title),
                el("div", { class: "toast-message" }, message),
            ),
            el("button", { class: "toast-close", "aria-label": "Close", onclick: () => removeToast(toast) }, "×"),
        );
        host.appendChild(toast);
        if (timeout) setTimeout(() => removeToast(toast), timeout);
    }

    function removeToast(toast) {
        if (!toast.parentNode) return;
        toast.classList.add("removing");
        setTimeout(() => toast.remove(), 300);
    }

    /* ======================================================================
       UTILITIES
       ====================================================================== */
    async function fetchJSON(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    }

    function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

    /* ======================================================================
       WIRE UP THE DOM
       ====================================================================== */
    function init() {
        initTheme();

        // Inject icons into static elements
        $("logoIcon").innerHTML = Icons.get("logo", "logo");
        $$(".nav-item").forEach((n) => {
            n.insertAdjacentHTML("afterbegin", Icons.get(n.dataset.icon || "download"));
        });
        $("startBtn").insertAdjacentHTML("afterbegin", Icons.get("play"));
        $("stopBtn").insertAdjacentHTML("afterbegin", Icons.get("stop"));
        $("themeToggle").innerHTML = Icons.get("sun");
        $("filterIcon").innerHTML = Icons.get("filter");
        $("searchIcon").innerHTML = Icons.get("search");
        $("exportLogBtn").insertAdjacentHTML("afterbegin", Icons.get("download"));
        $("autoScrollBtn").insertAdjacentHTML("afterbegin", Icons.get("arrowDown"));
        $("saveConfigBtn").insertAdjacentHTML("afterbegin", Icons.get("save"));
        $("summaryIcon").innerHTML = Icons.get("package");

        // Stat card icons
        const statIcons = { statInstalled: "check", statUpdated: "refreshCw", statSkipped: "package", statFailed: "alertTriangle", statNotFound: "xCircle" };
        for (const [id, icon] of Object.entries(statIcons)) {
            const card = $(id).closest(".stat-card");
            if (card) card.insertAdjacentHTML("afterbegin", `<span class="stat-icon" style="color:var(--${ {statInstalled:"success",statUpdated:"accent",statSkipped:"text-secondary",statFailed:"warning",statNotFound:"error"}[id]})">${Icons.get(icon)}</span>`);
        }

        // Wire buttons
        $("themeToggle").addEventListener("click", toggleTheme);
        $("startBtn").addEventListener("click", startDownload);
        $("stopBtn").addEventListener("click", stopDownload);
        $("saveConfigBtn").addEventListener("click", saveConfig);
        $("exportLogBtn").addEventListener("click", exportLog);
        $("autoScrollBtn").addEventListener("click", toggleAutoScroll);
        $("summaryCloseBtn").addEventListener("click", closeModal);
        $("summaryModal").addEventListener("click", (e) => { if (e.target.id === "summaryModal") closeModal(); });
        $("logContainer").addEventListener("scroll", onLogScroll);
        $("logSearch").addEventListener("input", onSearch);
        $("mcVersion").addEventListener("input", (e) => {
            const ok = MC_VERSION_RE.test(e.target.value.trim());
            e.target.classList.toggle("invalid", e.target.value.length > 0 && !ok);
            $("versionError").textContent = ok || e.target.value.length === 0 ? "" : "Format: 1.21, 1.21.1, 1.20.1-beta.3";
        });

        // Filter buttons
        $$(".filter-btn").forEach((b) => b.addEventListener("click", () => setFilter(b.dataset.filter)));

        // Tabs
        $$(".nav-item").forEach((n) => n.addEventListener("click", () => switchTab(n.dataset.tab)));

        // Checkbox tile visual sync
        document.addEventListener("change", (e) => {
            if (e.target.matches('#categoryGroup input[type=checkbox]')) {
                e.target.closest(".checkbox-item").classList.toggle("checked", e.target.checked);
            }
        });
        // Initial checked styling
        $$("#categoryGroup input[type=checkbox]:checked").forEach((cb) =>
            cb.closest(".checkbox-item").classList.add("checked"),
        );

        updateAutoScrollBtn();

        // Socket + initial status
        initSocket();
        fetchJSON("/api/status").then((s) => updateStatus(s.status)).catch(() => {});

        // Welcome log
        addLog("Ready. Select categories and version, then press Start.", "info");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
