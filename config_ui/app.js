  const token = new URLSearchParams(location.search).get("token") || "";
  const authHeaders = token ? { Authorization: "Bearer " + token } : {};

  function blockSideNav(e) {
    if (e.button === 3 || e.button === 4) {
      e.preventDefault();
      e.stopPropagation();
    }
  }
  ["mousedown", "mouseup", "auxclick"].forEach((type) => {
    window.addEventListener(type, blockSideNav, true);
  });
  try {
    history.pushState(null, "", location.href);
    window.addEventListener("popstate", () => {
      history.pushState(null, "", location.href);
    });
  } catch (_) {}

  const ASPECTS = {
    "16:9": 16 / 9,
    "1:1": 1,
    "4:3": 4 / 3,
    "21:9": 21 / 9,
  };

  let cfg = {};
  let presetInfo = { builtin: [], user: [], active: "", active_kind: "builtin" };
  let selectedPreset = { name: "", kind: "builtin" };
  let applyTimer = null;
  let suppress = false;
  let previewMode = "lite";
  let currentSection = "presets";
  let presetBaseline = null;
  let presetDirty = false;

  // Populated from /api/presets (single source: velo.defaults.PRESET_EXCLUDE)
  let presetExclude = new Set();

  const FEEL_HINTS = {
    tight: "Faster / larger on the pad",
    normal: "Default balance",
    soft: "Slower, smoother look",
    custom: "Custom values",
  };

  const $ = (id) => document.getElementById(id);
  const frame = $("frame");
  const stage = $("stage");
  const previewViewport = $("preview-viewport");
  const previewOff = $("preview-off");
  const previewModeEl = $("preview-mode");
  const toastEl = $("toast");
  const obsUrl = $("obs-url");
  const statusEl = $("status");
  const sizeLabel = $("size-label");
  const sizeLabel2 = $("size-label-2");
  const presetList = $("preset-list");
  const presetNameInput = $("preset-name");
  const dirtyBanner = $("preset-dirty");
  const dirtyLabel = $("preset-dirty-label");
  const btnDirtyUpdate = $("btn-dirty-update");
  const btnDirtySave = $("btn-dirty-save");
  const btnPresetUpdate = $("btn-preset-update");

  function toast(msg) {
    toastEl.hidden = false;
    toastEl.textContent = msg;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (toastEl.hidden = true), 2000);
  }

  const modalRoot = $("modal-root");
  const modalTitle = $("modal-title");
  const modalMessage = $("modal-message");
  const modalInputWrap = $("modal-input-wrap");
  const modalInput = $("modal-input");
  const modalCancel = $("modal-cancel");
  const modalSecondary = $("modal-secondary");
  const modalConfirm = $("modal-confirm");
  const modalBackdrop = $("modal-backdrop");
  let modalResolver = null;

  function closeModal(result) {
    if (!modalRoot) return;
    modalRoot.hidden = true;
    const resolve = modalResolver;
    modalResolver = null;
    if (resolve) resolve(result);
  }

  function showModal(opts) {
    const options = opts || {};
    return new Promise((resolve) => {
      if (!modalRoot) {
        resolve({ ok: false, action: "cancel" });
        return;
      }
      if (modalResolver) closeModal({ ok: false, action: "cancel" });
      modalResolver = resolve;
      if (modalTitle) modalTitle.textContent = options.title || "Confirm";
      if (modalMessage) modalMessage.textContent = options.message || "";
      const hasInput = options.input !== undefined && options.input !== null;
      if (modalInputWrap) {
        if (hasInput) modalInputWrap.removeAttribute("hidden");
        else modalInputWrap.setAttribute("hidden", "");
      }
      if (modalInput) {
        modalInput.value = hasInput ? String(options.input) : "";
        modalInput.placeholder = options.placeholder || "";
      }
      if (modalCancel) {
        modalCancel.textContent = options.cancelText || "Cancel";
        if (options.hideCancel) modalCancel.setAttribute("hidden", "");
        else modalCancel.removeAttribute("hidden");
      }
      if (modalSecondary) {
        const hasSecondary = !!options.secondaryText;
        if (hasSecondary) {
          modalSecondary.removeAttribute("hidden");
          modalSecondary.textContent = options.secondaryText;
        } else {
          modalSecondary.setAttribute("hidden", "");
        }
      }
      if (modalConfirm) {
        modalConfirm.textContent = options.confirmText || "OK";
        modalConfirm.classList.toggle("danger", !!options.danger);
      }
      modalRoot.hidden = false;
      setTimeout(() => {
        if (hasInput && modalInput) {
          modalInput.focus();
          modalInput.select();
        } else if (modalConfirm) {
          modalConfirm.focus();
        }
      }, 0);
    });
  }

  function confirmDialog(message, opts) {
    const o = opts || {};
    return showModal({
      title: o.title || "Confirm",
      message,
      confirmText: o.confirmText || "OK",
      cancelText: o.cancelText || "Cancel",
      danger: !!o.danger,
    }).then((r) => !!r.ok && r.action === "confirm");
  }

  function promptDialog(message, opts) {
    const o = opts || {};
    return showModal({
      title: o.title || "Input",
      message,
      input: o.value != null ? o.value : "",
      placeholder: o.placeholder || "",
      confirmText: o.confirmText || "OK",
      cancelText: o.cancelText || "Cancel",
      hideCancel: !!o.hideCancel,
    }).then((r) => (r.ok && r.action === "confirm" ? String(r.value || "").trim() : null));
  }

  if (modalConfirm) {
    modalConfirm.addEventListener("click", () => {
      const value = modalInput && !modalInputWrap.hidden ? modalInput.value : undefined;
      closeModal({ ok: true, action: "confirm", value });
    });
  }
  if (modalSecondary) {
    modalSecondary.addEventListener("click", () => {
      closeModal({ ok: true, action: "secondary" });
    });
  }
  if (modalCancel) {
    modalCancel.addEventListener("click", () => closeModal({ ok: false, action: "cancel" }));
  }
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", () => closeModal({ ok: false, action: "cancel" }));
  }
  document.addEventListener("keydown", (e) => {
    if (!modalRoot || modalRoot.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeModal({ ok: false, action: "cancel" });
    } else if (e.key === "Enter" && modalInput && !modalInputWrap.hidden && document.activeElement === modalInput) {
      e.preventDefault();
      closeModal({ ok: true, action: "confirm", value: modalInput.value });
    }
  });

  function api(path, opts = {}) {
    const q = token ? (path.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token) : "";
    return fetch(path + q, {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        ...authHeaders,
      },
    });
  }

  function overlayUrl() {
    const host =
      cfg.host === "0.0.0.0" || cfg.host === "::" ? "127.0.0.1" : cfg.host || "127.0.0.1";
    const port = cfg.port || 27180;
    if (cfg.auth_enabled !== false && cfg.auth_token) {
      return `http://${host}:${port}/overlay?token=${cfg.auth_token}`;
    }
    return `http://${host}:${port}/overlay`;
  }

  function updateSizeLabels() {
    const w = Math.round(Number(cfg.canvas_width) || 640);
    const h = Math.round(Number(cfg.canvas_height) || 360);
    const t = `${w} × ${h}`;
    sizeLabel.textContent = t;
    if (sizeLabel2) sizeLabel2.textContent = t;
    if (obsUrl) obsUrl.textContent = overlayUrl();
    const sizeLine = $("obs-size-line");
    if (sizeLine) sizeLine.textContent = "Browser size: " + w + " x " + h;
    layoutPreviewCanvas();
  }

  function layoutPreviewCanvas() {
    if (!stage || !previewViewport) return;
    const w = Math.max(1, Math.round(Number(cfg.canvas_width) || 640));
    const h = Math.max(1, Math.round(Number(cfg.canvas_height) || 360));
    const sr = stage.getBoundingClientRect();
    const pad = 20;
    const availW = Math.max(1, sr.width - pad * 2);
    const availH = Math.max(1, sr.height - pad * 2);
    const scale = Math.min(availW / w, availH / h);
    previewViewport.style.width = w + "px";
    previewViewport.style.height = h + "px";
    previewViewport.style.transform = "scale(" + scale + ")";
  }

  function presetRelevantSnapshot(src) {
    const out = {};
    Object.keys(src || {})
      .filter((k) => !presetExclude.has(k))
      .sort()
      .forEach((k) => {
        out[k] = src[k];
      });
    return out;
  }

  function stableStringify(obj) {
    return JSON.stringify(obj);
  }

  function capturePresetBaseline() {
    presetBaseline = presetRelevantSnapshot(cfg);
    presetDirty = false;
    updateDirtyUi();
  }

  function recomputePresetDirty() {
    if (!presetBaseline) {
      presetDirty = false;
      updateDirtyUi();
      return;
    }
    const now = presetRelevantSnapshot(cfg);
    presetDirty = stableStringify(now) !== stableStringify(presetBaseline);
    updateDirtyUi();
  }

  function updateDirtyUi() {
    const name = selectedPreset.name || cfg.active_preset || "";
    const isUser = selectedPreset.kind === "user";
    const hasSelection = !!selectedPreset.name;
    if (dirtyBanner) dirtyBanner.hidden = !presetDirty;
    if (dirtyLabel) {
      dirtyLabel.textContent = presetDirty
        ? isUser
          ? `"${name}" was changed.`
          : `"${name}" is a default. Save as new to keep your changes.`
        : "";
    }
    if (btnDirtyUpdate) {
      btnDirtyUpdate.hidden = !(presetDirty && isUser);
    }
    const selName = $("preset-selected-name");
    if (selName) {
      const dirtyMark = hasSelection && presetDirty ? " *" : "";
      selName.textContent = (name || "None") + dirtyMark;
    }
    const setBtn = (id, enabled) => {
      const el = $(id);
      if (el) el.disabled = !enabled;
    };
    if (btnPresetUpdate) {
      btnPresetUpdate.disabled = !(isUser && presetDirty);
    }
    setBtn("btn-preset-rename", isUser && hasSelection);
    setBtn("btn-preset-delete", isUser && hasSelection);
    setBtn("btn-preset-export", hasSelection);
    setBtn("btn-preset-copy", hasSelection);
  }

  function getPresetGroupCollapsed(key, fallback) {
    try {
      const v = localStorage.getItem("velo.presetGroup." + key);
      if (v === "1") return true;
      if (v === "0") return false;
    } catch (_) {}
    if (key === "user") return false;
    return !!fallback;
  }

  function setPresetGroupCollapsed(key, collapsed) {
    try {
      localStorage.setItem("velo.presetGroup." + key, collapsed ? "1" : "0");
    } catch (_) {}
  }

  function updateFeelUi() {
    const feel = cfg.motion_feel || "normal";
    document.querySelectorAll(".feel-pill").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.feel === feel);
    });
    const hint = $("feel-hint");
    if (hint) hint.textContent = FEEL_HINTS[feel] || FEEL_HINTS.custom;
  }

  function updateObsSetupUi() {
    const done = !!cfg.ui_obs_setup_done;
    const card = $("obs-setup-card");
    const badge = $("obs-setup-badge");
    const title = $("obs-setup-title");
    const doneBtn = $("btn-setup-done");
    if (card) card.classList.toggle("first-run", !done);
    if (badge) {
      badge.textContent = done ? "OK" : "Setup";
      badge.classList.toggle("done", done);
      badge.hidden = false;
    }
    if (title) title.textContent = "Browser source";
    if (doneBtn) doneBtn.hidden = done;
  }

  function loadPreview() {
    const mode = previewMode || "lite";
    if (mode === "off") {
      try {
        frame.removeAttribute("src");
        frame.src = "about:blank";
      } catch (_) {}
      frame.hidden = true;
      if (previewViewport) previewViewport.classList.add("is-off");
      if (previewOff) {
        previewOff.hidden = true;
        previewOff.classList.add("is-visible");
      }
      return;
    }
    if (previewOff) {
      previewOff.classList.remove("is-visible");
      previewOff.hidden = true;
    }
    if (previewViewport) previewViewport.classList.remove("is-off");
    frame.hidden = false;
    layoutPreviewCanvas();
    const u = overlayUrl();
    if (!u || !cfg.port) return;
    const sep = u.includes("?") ? "&" : "?";
    const extra = mode === "lite" ? "preview=lite&" : "";
    frame.src = u + sep + extra + "_=" + Date.now();
  }

  function setPreviewMode(mode, persist) {
    previewMode = mode === "off" || mode === "live" || mode === "lite" ? mode : "lite";
    if (previewModeEl) previewModeEl.value = previewMode;
    loadPreview();
    if (persist) queuePatch({ ui_preview_mode: previewMode });
  }

  function showSection(id, persist) {
    currentSection = id || "presets";
    document.querySelectorAll(".sec-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.section === currentSection);
    });
    document.querySelectorAll(".block.sec").forEach((el) => {
      el.hidden = el.dataset.section !== currentSection;
    });
    if (persist) queuePatch({ ui_section: currentSection });
  }

  function bindForm() {
    suppress = true;
    document.querySelectorAll("[data-key]").forEach((el) => {
      const key = el.getAttribute("data-key");
      let val = cfg[key];
      if (el.type === "checkbox") {
        el.checked = !!val;
      } else if (el.hasAttribute("data-color")) {
        let c = String(val || "#ffffff");
        if (c.length > 7) c = c.slice(0, 7);
        el.value = c;
      } else if (el.type === "range") {
        el.value = val;
      } else {
        el.value = val == null ? "" : val;
      }
    });
    document.querySelectorAll(".val-input[data-link]").forEach((inp) => {
      const key = inp.getAttribute("data-link");
      const v = cfg[key];
      inp.value = v == null ? "" : v;
    });
    const colors = cfg.click_colors || {};
    const setColor = (id, hex) => {
      const el = $(id);
      if (!el) return;
      let c = String(hex || "#ffffff");
      if (c.length > 7) c = c.slice(0, 7);
      el.value = c;
    };
    setColor("click-color-left", colors.left);
    setColor("click-color-right", colors.right);
    setColor("click-color-middle", colors.middle);
    setColor("click-color-side", colors.x1 || colors.x2 || "#aaaaaa");

    const clickShow = cfg.click_show || {};
    const setClickShow = (id, on) => {
      const el = $(id);
      if (el) el.checked = on !== false;
    };
    setClickShow("click-show-left", clickShow.left);
    setClickShow("click-show-right", clickShow.right);
    setClickShow("click-show-middle", clickShow.middle);
    setClickShow("click-show-side", clickShow.side);

    const stops = normalizeSpeedStops(cfg.speed_stops);
    for (let i = 0; i < 4; i++) {
      setColor("speed-stop-" + i, stops[i].color);
    }
    updateTrailColorUi();
    updateHotkeyUi();
    updateStartupUi();

    suppress = false;
    updateSizeLabels();
    updateFeelUi();
    updateObsSetupUi();
    renderPresetList();
    recomputePresetDirty();
  }

  function updateStartupUi() {
    const auto = !!cfg.start_with_windows;
    const minLabel = $("label-minimized");
    const minChk = $("chk-minimized");
    if (minLabel) minLabel.classList.toggle("is-disabled", !auto);
    if (minChk) {
      minChk.disabled = !auto;
      if (!auto) minChk.checked = false;
    }
  }

  let hotkeyListening = false;
  let hotkeyKeyHandler = null;

  function updateHotkeyUi() {
    const btn = $("btn-hotkey-bind");
    if (!btn || hotkeyListening) return;
    const spec = String(cfg.stats_reset_hotkey || "").trim();
    btn.textContent = spec || "Click to bind";
    btn.classList.remove("listening");
  }

  function formatHotkeyFromEvent(e) {
    const parts = [];
    if (e.ctrlKey) parts.push("Ctrl");
    if (e.shiftKey) parts.push("Shift");
    if (e.altKey) parts.push("Alt");
    if (e.metaKey) parts.push("Win");
    const code = e.code || "";
    const key = e.key || "";
    let name = "";
    if (/^F\d{1,2}$/i.test(key)) name = key.toUpperCase();
    else if (/^Digit[0-9]$/.test(code)) name = code.slice(5);
    else if (/^Key[A-Z]$/.test(code)) name = code.slice(3);
    else if (key === " ") name = "Space";
    else if (key === "Escape") name = "Esc";
    else if (key === "Enter") name = "Enter";
    else if (key === "Tab") name = "Tab";
    else if (key === "Backspace") name = "Backspace";
    else if (key === "Delete") name = "Delete";
    else if (key === "Insert") name = "Insert";
    else if (key === "Home") name = "Home";
    else if (key === "End") name = "End";
    else if (key === "PageUp") name = "PageUp";
    else if (key === "PageDown") name = "PageDown";
    else if (key === "ArrowUp") name = "Up";
    else if (key === "ArrowDown") name = "Down";
    else if (key === "ArrowLeft") name = "Left";
    else if (key === "ArrowRight") name = "Right";
    else if (key === "+" || code === "Equal") name = "Plus";
    else if (key === "-" || code === "Minus") name = "Minus";
    else if (key.length === 1 && /[a-zA-Z0-9]/.test(key)) name = key.toUpperCase();
    else return null;
    if (!name) return null;
    parts.push(name);
    return parts.join("+");
  }

  function stopHotkeyListen() {
    hotkeyListening = false;
    if (hotkeyKeyHandler) {
      window.removeEventListener("keydown", hotkeyKeyHandler, true);
      hotkeyKeyHandler = null;
    }
    updateHotkeyUi();
  }

  function startHotkeyListen() {
    const btn = $("btn-hotkey-bind");
    if (!btn) return;
    if (hotkeyListening) {
      stopHotkeyListen();
      return;
    }
    hotkeyListening = true;
    btn.textContent = "Press keys… (Esc cancel)";
    btn.classList.add("listening");
    hotkeyKeyHandler = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") {
        stopHotkeyListen();
        return;
      }
      if (["Control", "Shift", "Alt", "Meta"].includes(e.key)) return;
      const spec = formatHotkeyFromEvent(e);
      if (!spec) return;
      stopHotkeyListen();
      queuePatch({ stats_reset_hotkey: spec });
      cfg.stats_reset_hotkey = spec;
      updateHotkeyUi();
      toast("Hotkey " + spec);
    };
    window.addEventListener("keydown", hotkeyKeyHandler, true);
  }

  const DEFAULT_SPEED_STOPS = [
    { t: 0.0, color: "#ffffff" },
    { t: 0.45, color: "#a0a0a0" },
    { t: 0.75, color: "#ffcc66" },
    { t: 1.0, color: "#ff4444" },
  ];

  function normalizeSpeedStops(raw) {
    const out = DEFAULT_SPEED_STOPS.map((s) => ({ t: s.t, color: s.color }));
    if (!Array.isArray(raw)) return out;
    for (let i = 0; i < 4; i++) {
      const src = raw[i];
      if (!src || typeof src !== "object") continue;
      if (typeof src.t === "number") out[i].t = src.t;
      if (src.color) {
        let c = String(src.color);
        if (c.length > 7) c = c.slice(0, 7);
        out[i].color = c;
      }
    }
    return out;
  }

  function updateTrailColorUi() {
    const speedOn = !!cfg.speed_colorize;
    const solid = $("trail-solid-color");
    const grad = $("trail-speed-colors");
    if (solid) solid.hidden = speedOn;
    if (grad) grad.hidden = !speedOn;
  }

  function coerce(el) {
    if (el.type === "checkbox") return el.checked;
    if (el.type === "range" || el.type === "number" || el.hasAttribute("data-num")) {
      const n = parseFloat(el.value);
      return Number.isFinite(n) ? n : el.value;
    }
    return el.value;
  }

  function collect(el) {
    const key = el.getAttribute("data-key") || el.getAttribute("data-link");
    if (!key) return null;
    let val = coerce(el);
    const intKeys = new Set([
      "port",
      "canvas_width",
      "canvas_height",
      "trail_lifetime_ms",
      "trail_max_points",
      "trail_samples",
      "target_fps",
      "ws_send_hz",
      "pad_radius",
      "pad_grid_size",
      "speed_min",
      "speed_max",
      "click_lifetime_ms",
      "click_radius",
      "stats_dpi",
    ]);
    if (intKeys.has(key) && typeof val === "number") val = Math.round(val);
    return { [key]: val };
  }

  function queuePatch(patch) {
    Object.assign(cfg, patch);
    if ("canvas_width" in patch || "canvas_height" in patch || "canvas_aspect" in patch) {
      maybeLockAspect(patch);
      updateSizeLabels();
    }
    if ("host" in patch || "port" in patch || "auth_token" in patch) updateSizeLabels();
    suppress = true;
    Object.keys(patch).forEach((key) => {
      document.querySelectorAll(`[data-key="${key}"]`).forEach((el) => {
        if (el.type === "checkbox") el.checked = !!patch[key];
        else if (el.type === "range") {
          el.value = patch[key];
        } else if (el.type !== "color" || typeof patch[key] === "string") {
          if (el.hasAttribute("data-color") && String(patch[key]).length > 7) {
            el.value = String(patch[key]).slice(0, 7);
          } else {
            el.value = patch[key];
          }
        }
      });
      document.querySelectorAll(`[data-link="${key}"]`).forEach((el) => {
        el.value = patch[key];
      });
    });
    suppress = false;

    if ("motion_feel" in patch || "motion_scale" in patch || "motion_ease" in patch || "camera_lag" in patch) {
      updateFeelUi();
    }
    if ("speed_colorize" in patch) updateTrailColorUi();
    if ("start_with_windows" in patch || "start_minimized" in patch) {
      if ("start_with_windows" in patch && !patch.start_with_windows) {
        cfg.start_minimized = false;
        patch.start_minimized = false;
      }
      updateStartupUi();
    }
    const dirtyKeys = Object.keys(patch).filter((k) => !presetExclude.has(k));
    if (dirtyKeys.length) recomputePresetDirty();

    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => persist(patch), 80);
  }

  function maybeLockAspect(patch) {
    const aspect = cfg.canvas_aspect || "16:9";
    if (aspect === "custom" || !ASPECTS[aspect]) return;
    const r = ASPECTS[aspect];
    if ("canvas_width" in patch && !("canvas_height" in patch)) {
      cfg.canvas_height = Math.round(cfg.canvas_width / r);
      patch.canvas_height = cfg.canvas_height;
    } else if ("canvas_height" in patch && !("canvas_width" in patch)) {
      cfg.canvas_width = Math.round(cfg.canvas_height * r);
      patch.canvas_width = cfg.canvas_width;
    } else if ("canvas_aspect" in patch) {
      cfg.canvas_height = Math.round((cfg.canvas_width || 640) / r);
      patch.canvas_height = cfg.canvas_height;
    }
  }

  async function persist(patch) {
    try {
      const res = await api("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error("save");
      const data = await res.json();
      if (data.data) {
        cfg = data.data;
        if ("render_quality" in patch || "motion_feel" in patch) bindForm();
        else {
          updateFeelUi();
          recomputePresetDirty();
        }
      }
      updateSizeLabels();
      updateObsSetupUi();
    } catch (_) {
      statusEl.textContent = "Save failed";
    }
  }

  function onInput(ev) {
    if (suppress) return;
    const t = ev.target;
    if (t.classList.contains("val-input") && t.hasAttribute("data-link")) {
      const patch = collect(t);
      if (patch) queuePatch(patch);
      return;
    }
    const el = t.closest("[data-key]");
    if (!el) return;
    const patch = collect(el);
    if (patch) queuePatch(patch);
  }

  function renderPresetList() {
    if (!presetList) return;
    presetList.innerHTML = "";
    const activeName = cfg.active_preset || presetInfo.active || "";
    const activeKind = cfg.active_preset_kind || presetInfo.active_kind || "builtin";
    const users = presetInfo.user || [];
    const builtins = presetInfo.builtin || [];

    function addGroup(key, label, items, defaultCollapsed) {
      const group = document.createElement("div");
      group.className = "preset-group";
      const collapsed = getPresetGroupCollapsed(key, defaultCollapsed);
      if (collapsed) group.classList.add("collapsed");

      const head = document.createElement("button");
      head.type = "button";
      head.className = "preset-group-head";
      head.setAttribute("aria-expanded", collapsed ? "false" : "true");
      head.innerHTML =
        '<span class="preset-group-chevron" aria-hidden="true"></span>' +
        '<span class="preset-group-title"></span>' +
        '<span class="preset-group-count"></span>';
      head.querySelector(".preset-group-title").textContent = label;
      head.querySelector(".preset-group-count").textContent = String(items.length);
      head.addEventListener("click", () => {
        const next = !group.classList.contains("collapsed");
        group.classList.toggle("collapsed", next);
        head.setAttribute("aria-expanded", next ? "false" : "true");
        setPresetGroupCollapsed(key, next);
      });
      group.appendChild(head);

      const body = document.createElement("div");
      body.className = "preset-group-body";

      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "preset-empty";
        empty.textContent =
          key === "user" ? "No saved presets yet." : "No default presets.";
        body.appendChild(empty);
      } else {
        items.forEach((p) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "preset-item";
          const isActive =
            p.name === activeName &&
            (p.kind === activeKind ||
              (selectedPreset.name === p.name && selectedPreset.kind === p.kind));
          const isSelected =
            selectedPreset.name === p.name && selectedPreset.kind === p.kind;
          if (isActive || isSelected) btn.classList.add("active");
          btn.innerHTML =
            '<span class="p-name"></span>' +
            '<span class="p-badge"></span>';
          const dirtyMark = isActive && presetDirty ? " *" : "";
          btn.querySelector(".p-name").textContent = p.name + dirtyMark;
          btn.querySelector(".p-badge").textContent = isActive ? "active" : "";
          btn.addEventListener("click", () => applyPreset(p.name, p.kind));
          body.appendChild(btn);
        });
      }

      group.appendChild(body);
      presetList.appendChild(group);
    }

    addGroup("user", "Saved", users, false);
    addGroup("defaults", "Defaults", builtins, users.length > 0);

    if (!users.length && !builtins.length) {
      const empty = document.createElement("div");
      empty.className = "preset-empty";
      empty.textContent = "No presets.";
      presetList.appendChild(empty);
    }
    updateDirtyUi();
  }

  function applyExcludeKeys(keys) {
    if (Array.isArray(keys) && keys.length) {
      presetExclude = new Set(keys);
    }
  }

  async function refreshPresets() {
    try {
      const res = await api("/api/presets");
      const data = await res.json();
      applyExcludeKeys(data.exclude_keys);
      presetInfo = {
        builtin: data.builtin || [],
        user: data.user || [],
        active: data.active || "",
        active_kind: data.active_kind || "builtin",
      };
      if (!selectedPreset.name && presetInfo.active) {
        selectedPreset = { name: presetInfo.active, kind: presetInfo.active_kind || "builtin" };
      }
    } catch (err) {
      console.warn("presets load failed", err);
      presetInfo = {
        builtin: (presetInfo.builtin || []).length
          ? presetInfo.builtin
          : ["16:9 pad", "16:9 grid", "Square HUD", "Border only", "Transparent trails", "Corner mini"].map(
              (name) => ({ name, kind: "builtin" })
            ),
        user: [],
        active: cfg.active_preset || "",
        active_kind: cfg.active_preset_kind || "builtin",
      };
    }
    renderPresetList();
  }

  async function applyPreset(name, kind) {
    selectedPreset = { name, kind };
    try {
      const res = await api("/api/config/preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, kind }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "apply");
      if (data.data) cfg = data.data;
      bindForm();
      capturePresetBaseline();
      loadPreview();
      toast(name);
      await refreshPresets();
    } catch (e) {
      toast("Couldn't load preset");
    }
  }

  async function savePresetAs() {
    let name = (presetNameInput.value || "").trim();
    if (!name && presetDirty && selectedPreset.name) {
      name = selectedPreset.name + " copy";
      if (presetNameInput) presetNameInput.value = name;
    }
    if (!name) {
      toast("Enter a name");
      presetNameInput.focus();
      return;
    }
    try {
      const res = await api("/api/presets/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "save");
      if (data.data) cfg = data.data;
      if (data.presets) {
        presetInfo = {
          builtin: data.presets.builtin || [],
          user: data.presets.user || [],
          active: data.presets.active || name,
          active_kind: data.presets.active_kind || "user",
        };
      }
      selectedPreset = { name, kind: "user" };
      presetNameInput.value = "";
      bindForm();
      capturePresetBaseline();
      toast("Saved " + name);
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Save failed");
    }
  }

  async function updateSelectedPreset() {
    if (!selectedPreset.name || selectedPreset.kind !== "user") {
      toast("Pick a saved preset first");
      return;
    }
    try {
      const res = await api("/api/presets/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPreset.name }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "update");
      if (data.data) cfg = data.data;
      capturePresetBaseline();
      updateDirtyUi();
      toast("Updated " + selectedPreset.name);
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Update failed");
    }
  }

  async function deleteSelectedPreset() {
    if (!selectedPreset.name || selectedPreset.kind !== "user") {
      toast("Pick a saved preset first");
      return;
    }
    const ok = await confirmDialog("Delete \"" + selectedPreset.name + "\"?", {
      title: "Delete preset",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      const res = await api("/api/presets/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPreset.name }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "delete");
      if (data.data) cfg = data.data;
      toast("Deleted " + selectedPreset.name);
      selectedPreset = { name: cfg.active_preset || "", kind: cfg.active_preset_kind || "builtin" };
      await refreshPresets();
      bindForm();
    } catch (e) {
      toast(String(e.message || e) || "Delete failed");
    }
  }

  async function renameSelectedPreset() {
    if (!selectedPreset.name || selectedPreset.kind !== "user") {
      toast("Pick a saved preset first");
      return;
    }
    const newName = await promptDialog("New name for this preset:", {
      title: "Rename preset",
      value: selectedPreset.name,
      confirmText: "Rename",
    });
    if (newName == null) return;
    if (!newName) {
      toast("Enter a name");
      return;
    }
    if (newName === selectedPreset.name) return;
    try {
      const res = await api("/api/presets/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_name: selectedPreset.name, new_name: newName }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "rename");
      if (data.data) cfg = data.data;
      selectedPreset = { name: newName, kind: "user" };
      if (data.presets) {
        presetInfo = {
          builtin: data.presets.builtin || [],
          user: data.presets.user || [],
          active: data.presets.active || newName,
          active_kind: data.presets.active_kind || "user",
        };
      }
      bindForm();
      capturePresetBaseline();
      toast("Renamed to " + newName);
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Rename failed");
    }
  }

  async function exportSelectedPresetFile() {
    if (!selectedPreset.name) {
      toast("Select a preset first");
      return;
    }
    try {
      const res = await api("/api/presets/export-dialog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPreset.name, kind: selectedPreset.kind }),
      });
      const data = await readJson(res);
      if (data.cancelled) return;
      if (!res.ok || !data.ok) throw new Error(data.error || "export");
      toast("Preset exported");
    } catch (e) {
      toast(String(e.message || e) || "Export failed");
    }
  }

  async function readJson(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error("Bad server response");
    }
  }

  async function copySelectedPreset() {
    if (!selectedPreset.name) {
      toast("Select a preset first");
      return;
    }
    try {
      const res = await api("/api/presets/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPreset.name, kind: selectedPreset.kind }),
      });
      const data = await readJson(res);
      if (!res.ok || !data.ok) throw new Error(data.error || "share");
      const code = String(data.code || "").trim();
      if (!code) throw new Error("empty code");
      const ok = await copyText(code);
      if (!ok) {
        await promptDialog("Copy this code manually (Ctrl+C):", {
          title: "Preset code",
          value: code,
          confirmText: "Done",
          hideCancel: true,
        });
      }
      toast(ok ? "Preset code copied" : "Code ready to copy");
    } catch (e) {
      toast(String(e.message || e) || "Copy failed");
    }
  }

  async function importPresetFile() {
    try {
      const res = await api("/api/presets/import-dialog", { method: "POST" });
      const data = await readJson(res);
      if (data.cancelled) return;
      if (!res.ok || !data.ok) throw new Error(data.error || "import");
      if (data.data) cfg = data.data;
      if (data.presets) {
        presetInfo = {
          builtin: data.presets.builtin || [],
          user: data.presets.user || [],
          active: data.presets.active || "",
          active_kind: data.presets.active_kind || "user",
        };
      }
      selectedPreset = {
        name: cfg.active_preset || "",
        kind: cfg.active_preset_kind || "user",
      };
      bindForm();
      capturePresetBaseline();
      loadPreview();
      await refreshPresets();
      toast("Preset imported");
    } catch (e) {
      toast(String(e.message || e) || "Import failed");
    }
  }

  async function importPresetFromCodeInput() {
    const input = $("preset-code-input");
    const text = input ? String(input.value || "").trim() : "";
    if (!text) {
      toast("Paste a share code first");
      if (input) input.focus();
      return;
    }
    try {
      const res = await api("/api/presets/import-share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await readJson(res);
      if (!res.ok || !data.ok) throw new Error(data.error || "import");
      if (data.data) cfg = data.data;
      if (data.presets) {
        presetInfo = {
          builtin: data.presets.builtin || [],
          user: data.presets.user || [],
          active: data.presets.active || "",
          active_kind: data.presets.active_kind || "user",
        };
      }
      selectedPreset = {
        name: cfg.active_preset || "",
        kind: cfg.active_preset_kind || "user",
      };
      if (input) input.value = "";
      bindForm();
      capturePresetBaseline();
      loadPreview();
      await refreshPresets();
      toast("Preset imported");
    } catch (e) {
      toast(String(e.message || e) || "Import failed");
    }
  }

  async function loadConfig() {
    const res = await api("/api/config");
    if (!res.ok) throw new Error("config");
    cfg = await res.json();
    await refreshPresets();
    previewMode = cfg.ui_preview_mode || "lite";
    if (previewModeEl) previewModeEl.value = previewMode;
    selectedPreset = {
      name: cfg.active_preset || "",
      kind: cfg.active_preset_kind || "builtin",
    };
    let section = cfg.ui_section || (!cfg.ui_obs_setup_done ? "obs" : "presets");
    if (section === "backup") section = "settings";
    showSection(section, false);
    bindForm();
    capturePresetBaseline();
    loadPreview();
    if (!cfg.ui_obs_setup_done) {
      showSection("obs", false);
    }
  }

  async function poll() {
    try {
      const res = await api("/api/status");
      const s = await res.json();
      applyExcludeKeys(s.exclude_keys);
      const parts = [];
      if (s.error || !s.running) {
        parts.push(s.error || "Server offline");
      } else {
        parts.push("Online, " + (s.clients || 0) + " client(s)");
      }
      if (s.capture_error) parts.push("Capture: " + s.capture_error);
      else if (s.running && s.capture_running === false) parts.push("Capture offline");
      if (s.version) parts.push("v" + s.version);
      statusEl.textContent = parts.join(" · ");
      statusEl.title = parts.join("\n");
      statusEl.classList.toggle("err", !!(s.error || s.capture_error || !s.running));
    } catch (_) {
      statusEl.textContent = "Offline";
      statusEl.classList.add("err");
    }
  }

  async function exportSettings() {
    try {
      const res = await api("/api/config/export-dialog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_connection: true }),
      });
      const data = await readJson(res);
      if (data.cancelled) return;
      if (!res.ok || !data.ok) throw new Error(data.error || "export");
      toast(data.path ? "Saved" : "Exported");
    } catch (e) {
      toast(String(e.message || e) || "Export failed");
    }
  }

  async function importSettings() {
    try {
      const choice = await showModal({
        title: "Import settings",
        message:
          "Choose what to restore from the file.\n\nFull import includes host, port, and auth token.",
        confirmText: "Full import",
        secondaryText: "Visuals only",
        cancelText: "Cancel",
      });
      if (!choice.ok || choice.action === "cancel") return;
      const include = choice.action === "confirm";
      const res = await api("/api/config/import-dialog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_connection: include }),
      });
      const data = await readJson(res);
      if (data.cancelled) return;
      if (!res.ok || !data.ok) throw new Error(data.error || "import");
      if (data.data) cfg = data.data;
      selectedPreset = {
        name: cfg.active_preset || "",
        kind: cfg.active_preset_kind || "builtin",
      };
      bindForm();
      capturePresetBaseline();
      loadPreview();
      await refreshPresets();
      toast("Imported");
    } catch (e) {
      toast(String(e.message || e) || "Import failed");
    }
  }

  async function copySize() {
    const w = Math.round(Number(cfg.canvas_width) || 640);
    const h = Math.round(Number(cfg.canvas_height) || 360);
    const text = w + " x " + h;
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      await copyText(text);
    }
    toast("Size " + text);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  async function copyUrl() {
    if (await copyText(overlayUrl())) {
      toast("URL copied");
      if (!cfg.ui_obs_setup_done) {
        queuePatch({ ui_obs_setup_done: true });
        updateObsSetupUi();
      }
    } else {
      toast("Copy failed");
    }
  }

  const tipEl = document.createElement("div");
  tipEl.id = "tip-float";
  document.body.appendChild(tipEl);
  let tipAnchor = null;

  function placeTip(el) {
    const text = el.getAttribute("data-tip");
    if (!text) return;
    tipAnchor = el;
    tipEl.textContent = text;
    tipEl.classList.add("show");
    const r = el.getBoundingClientRect();
    const pad = 8;
    const tw = tipEl.offsetWidth || 200;
    const th = tipEl.offsetHeight || 40;
    let left = r.right + pad;
    let top = r.top + r.height / 2 - th / 2;
    if (left + tw > window.innerWidth - pad) {
      left = r.left - tw - pad;
    }
    if (left < pad) left = pad;
    if (top < pad) top = pad;
    if (top + th > window.innerHeight - pad) {
      top = window.innerHeight - th - pad;
    }
    tipEl.style.left = Math.round(left) + "px";
    tipEl.style.top = Math.round(top) + "px";
  }

  function hideTip() {
    tipAnchor = null;
    tipEl.classList.remove("show");
  }

  document.addEventListener(
    "mouseover",
    (e) => {
      const el = e.target.closest(".info[data-tip]");
      if (el) placeTip(el);
    },
    true
  );
  document.addEventListener(
    "mouseout",
    (e) => {
      const el = e.target.closest(".info[data-tip]");
      if (!el) return;
      const to = e.relatedTarget;
      if (to && el.contains(to)) return;
      if (tipAnchor === el) hideTip();
    },
    true
  );
  document.addEventListener("focusin", (e) => {
    const el = e.target.closest && e.target.closest(".info[data-tip]");
    if (el) placeTip(el);
  });
  document.addEventListener("focusout", (e) => {
    const el = e.target.closest && e.target.closest(".info[data-tip]");
    if (el && tipAnchor === el) hideTip();
  });
  document.addEventListener(
    "scroll",
    () => {
      if (tipAnchor) placeTip(tipAnchor);
    },
    true
  );
  window.addEventListener("resize", () => {
    if (tipAnchor) placeTip(tipAnchor);
  });

  function onClickColor(which, hex) {
    let c = String(hex || "#ffffff");
    if (c.length > 7) c = c.slice(0, 7);
    const next = { ...(cfg.click_colors || {}) };
    if (which === "side") {
      next.x1 = c;
      next.x2 = c;
    } else {
      next[which] = c;
    }
    queuePatch({ click_colors: next });
  }

  function onClickShow(which, on) {
    const next = { ...(cfg.click_show || {}) };
    next[which] = !!on;
    queuePatch({ click_show: next });
  }

  function onSpeedStopColor(index, hex) {
    let c = String(hex || "#ffffff");
    if (c.length > 7) c = c.slice(0, 7);
    const stops = normalizeSpeedStops(cfg.speed_stops);
    if (index < 0 || index >= stops.length) return;
    stops[index] = { t: stops[index].t, color: c };
    queuePatch({ speed_stops: stops });
  }

  document.addEventListener("input", onInput);
  document.addEventListener("change", onInput);

  const HUD_CORNERS = {
    tl: { stats_x_pct: 0, stats_y_pct: 0 },
    tr: { stats_x_pct: 100, stats_y_pct: 0 },
    bl: { stats_x_pct: 0, stats_y_pct: 100 },
    br: { stats_x_pct: 100, stats_y_pct: 100 },
  };
  document.querySelectorAll("[data-hud-corner]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const patch = HUD_CORNERS[btn.getAttribute("data-hud-corner")];
      if (patch) queuePatch(patch);
    });
  });

  if ($("btn-stats-reset")) {
    $("btn-stats-reset").addEventListener("click", async () => {
      try {
        const res = await api("/api/stats/reset", { method: "POST" });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "reset");
        toast("Stats reset");
      } catch (_) {
        toast("Could not reset stats");
      }
    });
  }
  if ($("btn-hotkey-bind")) {
    $("btn-hotkey-bind").addEventListener("click", startHotkeyListen);
  }
  if ($("btn-hotkey-clear")) {
    $("btn-hotkey-clear").addEventListener("click", () => {
      stopHotkeyListen();
      queuePatch({ stats_reset_hotkey: "" });
      cfg.stats_reset_hotkey = "";
      updateHotkeyUi();
      toast("Hotkey cleared");
    });
  }

  const clickColorMap = {
    "click-color-left": "left",
    "click-color-right": "right",
    "click-color-middle": "middle",
    "click-color-side": "side",
  };
  Object.keys(clickColorMap).forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("input", () => onClickColor(clickColorMap[id], el.value));
    el.addEventListener("change", () => onClickColor(clickColorMap[id], el.value));
  });

  const clickShowMap = {
    "click-show-left": "left",
    "click-show-right": "right",
    "click-show-middle": "middle",
    "click-show-side": "side",
  };
  Object.keys(clickShowMap).forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("change", () => onClickShow(clickShowMap[id], el.checked));
  });

  for (let i = 0; i < 4; i++) {
    const el = $("speed-stop-" + i);
    if (!el) continue;
    el.addEventListener("input", () => onSpeedStopColor(i, el.value));
    el.addEventListener("change", () => onSpeedStopColor(i, el.value));
  }

  document.querySelectorAll(".sec-btn").forEach((btn) => {
    btn.addEventListener("click", () => showSection(btn.dataset.section, true));
  });

  document.querySelectorAll(".feel-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      queuePatch({ motion_feel: btn.dataset.feel });
    });
  });

  if ($("btn-copy")) $("btn-copy").addEventListener("click", copyUrl);
  if ($("btn-copy-size")) $("btn-copy-size").addEventListener("click", copySize);
  if ($("btn-export")) $("btn-export").addEventListener("click", exportSettings);
  if ($("btn-import")) $("btn-import").addEventListener("click", importSettings);
  if ($("btn-reset-visuals")) {
    $("btn-reset-visuals").addEventListener("click", async () => {
      const ok = await confirmDialog(
        "Reset look settings only?\nHost, port, and auth token stay.",
        { title: "Reset look", confirmText: "Reset look" }
      );
      if (!ok) return;
      const res = await api("/api/config/reset-visuals", { method: "POST" });
      const data = await res.json();
      cfg = data.data || cfg;
      bindForm();
      capturePresetBaseline();
      loadPreview();
      toast("Look reset");
    });
  }
  if ($("btn-setup-done")) {
    $("btn-setup-done").addEventListener("click", () => {
      queuePatch({ ui_obs_setup_done: true });
      updateObsSetupUi();
      toast("OK");
    });
  }
  if (btnDirtyUpdate) btnDirtyUpdate.addEventListener("click", updateSelectedPreset);
  if (btnDirtySave) btnDirtySave.addEventListener("click", () => {
    if (presetNameInput && !presetNameInput.value.trim() && selectedPreset.name) {
      presetNameInput.value = selectedPreset.kind === "builtin"
        ? selectedPreset.name + " custom"
        : selectedPreset.name + " copy";
    }
    savePresetAs();
  });
  $("btn-reload").addEventListener("click", loadPreview);
  if (previewModeEl) {
    previewModeEl.addEventListener("change", (e) => {
      setPreviewMode(e.target.value, true);
    });
  }
  $("checker").addEventListener("change", (e) => {
    stage.classList.toggle("plain", !e.target.checked);
  });
  if (typeof ResizeObserver !== "undefined" && stage) {
    new ResizeObserver(() => layoutPreviewCanvas()).observe(stage);
  }
  window.addEventListener("resize", layoutPreviewCanvas);

  $("btn-preset-save").addEventListener("click", savePresetAs);
  $("btn-preset-update").addEventListener("click", updateSelectedPreset);
  if ($("btn-preset-rename")) $("btn-preset-rename").addEventListener("click", renameSelectedPreset);
  if ($("btn-preset-delete")) $("btn-preset-delete").addEventListener("click", deleteSelectedPreset);
  if ($("btn-preset-export")) $("btn-preset-export").addEventListener("click", exportSelectedPresetFile);
  if ($("btn-preset-copy")) $("btn-preset-copy").addEventListener("click", copySelectedPreset);
  if ($("btn-preset-import")) $("btn-preset-import").addEventListener("click", importPresetFile);
  if ($("btn-preset-import-code")) $("btn-preset-import-code").addEventListener("click", importPresetFromCodeInput);
  const codeInput = $("preset-code-input");
  if (codeInput) {
    codeInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        importPresetFromCodeInput();
      }
    });
  }
  if (presetNameInput) {
    presetNameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        savePresetAs();
      }
    });
  }

  $("btn-reset").addEventListener("click", async () => {
    const ok = await confirmDialog(
      "Reset all settings to defaults?\nAuth token is kept so your OBS URL still works.",
      { title: "Reset all", confirmText: "Reset all", danger: true }
    );
    if (!ok) return;
    const res = await api("/api/config/reset", { method: "POST" });
    const data = await res.json();
    cfg = data.data || cfg;
    selectedPreset = {
      name: cfg.active_preset || "",
      kind: cfg.active_preset_kind || "builtin",
    };
    bindForm();
    capturePresetBaseline();
    loadPreview();
    toast("Reset");
  });

  $("btn-restart").addEventListener("click", async () => {
    await persist({
      host: cfg.host,
      port: cfg.port,
      auth_token: cfg.auth_token,
    });
    toast("Restarting...");
    try {
      await api("/api/server/restart", { method: "POST" });
    } catch (_) {}
    setTimeout(() => {
      location.href =
        location.pathname +
        (cfg.auth_token ? `?token=${encodeURIComponent(cfg.auth_token)}` : "");
    }, 700);
  });

  Promise.all([loadConfig()])
    .then(() => {
      statusEl.textContent = "Online";
      poll();
      setInterval(poll, 2500);
    })
    .catch((e) => {
      statusEl.textContent = "Failed to load";
      console.error(e);
    });

