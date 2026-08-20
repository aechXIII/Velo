  const token = new URLSearchParams(location.search).get("token") || "";
  const authHeaders = token ? { Authorization: "Bearer " + token } : {};
  if (token) {
    try { history.replaceState(null, "", location.pathname + location.hash); } catch (_) {}
  }

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

  const SECTION_KEYS = {
    presets: [],
    size: ["canvas_aspect", "canvas_width", "canvas_height"],
    background: ["pad_shape", "pad_radius", "pad_bg_enabled", "pad_bg_color", "pad_bg_opacity", "pad_blur", "pad_shadow", "pad_shadow_opacity", "pad_vignette", "pad_vignette_opacity", "pad_clip_trail", "source_bg_enabled", "source_bg_color", "source_bg_opacity", "overlay_opacity", "pad_grid", "pad_grid_size", "pad_grid_thickness", "pad_grid_color", "pad_grid_opacity", "pad_border_enabled", "pad_border_color", "pad_border_opacity", "pad_border_width", "pad_glow_enabled", "pad_glow_color", "pad_glow_opacity", "pad_glow_blur"],
    motion: ["capture_mode", "invert_y", "sensitivity", "view_mode", "camera_lag", "camera_look_ahead", "camera_follow", "view_zoom", "motion_scale", "motion_ease", "motion_feel"],
    trail: ["trail_enabled", "trail_lifetime_ms", "trail_max_points", "trail_width", "trail_glow", "trail_glow_blur", "trail_glow_opacity", "trail_glow_width", "trail_glow_custom_color", "trail_glow_custom_color_val", "trail_min_distance", "trail_smoothing", "trail_curve", "trail_samples", "fade_style", "trail_color", "speed_colorize", "speed_stops", "speed_max", "speed_min"],
    cursor: ["show_cursor_dot", "cursor_dot_size", "cursor_dot_color", "cursor_dot_opacity", "show_clicks", "click_lifetime_ms", "click_radius", "click_line_width", "click_opacity", "click_expand", "click_style", "click_show", "click_colors"],
    hud: ["show_stats", "stats_opacity", "stats_bg", "stats_border", "stats_x_pct", "stats_y_pct", "stats_show_speed", "stats_show_peak", "stats_show_cps", "stats_show_clicks", "stats_show_distance", "stats_units", "stats_dpi", "stats_update_rate", "hud_show_avg_speed", "hud_show_sparkline", "chart_color"],
    performance: ["render_quality", "target_fps", "ws_send_hz", "trail_max_points", "trail_samples"],
    obs: [],
    settings: [],
  };

  const DEFAULT_CFG = {
    host: "[IP_ADDRESS]",
    port: 27180,
    auth_token: "",
    capture_mode: "relative",
    invert_y: false,
    sensitivity: 1.0,
    view_mode: "infinite",
    camera_lag: 0.15,
    camera_look_ahead: 0.0,
    camera_follow: 1.0,
    view_zoom: 1.0,
    motion_scale: 1.0,
    motion_ease: 0.2,
    motion_feel: "normal",
    target_fps: 60,
    render_quality: "balanced",
    ws_send_hz: 120,
    trail_enabled: true,
    trail_lifetime_ms: 1100,
    trail_max_points: 120,
    trail_width: 2.4,
    trail_glow: true,
    trail_glow_blur: 6,
    trail_glow_opacity: 1.0,
    trail_glow_width: 1.0,
    trail_glow_custom_color: false,
    trail_glow_custom_color_val: "#ffffff",
    trail_min_distance: 1.2,
    trail_smoothing: 0.0,
    trail_curve: 0.55,
    trail_samples: 2,
    fade_style: "smooth",
    trail_color: "#ffffff",
    speed_min: 40.0,
    speed_max: 3200.0,
    speed_stops: [
      { t: 0.0, color: "#ffffff" },
      { t: 0.45, color: "#a0a0a0" },
      { t: 0.75, color: "#ffcc66" },
      { t: 1.0, color: "#ff4444" },
    ],
    speed_colorize: true,
    show_cursor_dot: true,
    cursor_dot_size: 4.5,
    cursor_dot_color: "#ffffff",
    cursor_dot_opacity: 0.95,
    show_clicks: true,
    click_lifetime_ms: 280,
    click_radius: 16.0,
    click_line_width: 1.5,
    click_opacity: 0.85,
    click_expand: true,
    click_style: "ring",
    click_show: { left: true, right: true, middle: true, side: true },
    click_colors: { left: "#ffffff", right: "#cccccc", middle: "#888888", x1: "#aaaaaa", x2: "#aaaaaa" },
    pad_shape: "rounded",
    pad_radius: 12,
    pad_bg_enabled: true,
    pad_bg_color: "#0a0a0a",
    pad_bg_opacity: 0.72,
    pad_blur: false,
    pad_border_enabled: true,
    pad_border_color: "#ffffff",
    pad_border_opacity: 0.12,
    pad_border_width: 1.5,
    pad_shadow: false,
    pad_shadow_opacity: 0.4,
    pad_grid: false,
    pad_grid_size: 40,
    pad_grid_thickness: 1.0,
    pad_grid_color: "#ffffff",
    pad_grid_opacity: 0.08,
    pad_vignette: false,
    pad_vignette_opacity: 0.3,
    pad_clip_trail: true,
    pad_glow_enabled: false,
    pad_glow_color: "#ffffff",
    pad_glow_opacity: 0.5,
    pad_glow_blur: 24,
    canvas_aspect: "16:9",
    canvas_width: 640,
    canvas_height: 360,
    source_bg_enabled: false,
    source_bg_color: "#000000",
    source_bg_opacity: 0.0,
    overlay_opacity: 1.0,
    show_stats: false,
    stats_opacity: 0.55,
    stats_bg: true,
    stats_border: true,
    stats_x_pct: 0.0,
    stats_y_pct: 100.0,
    stats_show_speed: true,
    stats_show_peak: false,
    stats_show_cps: true,
    stats_show_clicks: true,
    stats_show_distance: true,
    stats_units: "cm",
    stats_dpi: 800,
    stats_update_rate: "normal",
    stats_reset_hotkey: "",
    start_minimized: false,
    start_with_windows: false,
    update_check_mode: "launch",
    show_onboarding: true,
    hud_show_avg_speed: true,
    hud_show_sparkline: true,
    chart_color: "#a677ff",
    accent_color: "#a277ff",
    bg_color: "#0f0f0f",
    backup_enabled: true,
    backup_max_count: 10,
  };

  let cfg = {};
  let presetInfo = { builtin: [], user: [], active: "", active_kind: "builtin" };
  let selectedPreset = { name: "", kind: "builtin" };
  let applyTimer = null;
  let suppress = false;
  let previewMode = "lite";
  let previewAuto = false;
  let currentSection = "presets";
  let presetBaseline = null;
  let presetDirty = false;

  const undoStack = [];
  const redoStack = [];
  const MAX_UNDO = 50;
  let undoSnapshot = null;

  // Populated from /api/presets (single source: velo.defaults.PRESET_EXCLUDE)
  let presetExclude = new Set();

  const FEEL_HINTS = {
    tight: "Faster / snappier",
    normal: "Default balance",
    soft: "Slower / smoother",
    custom: "Custom values",
  };

  const $ = (id) => document.getElementById(id);
  const frame = $("frame");
  const stage = $("stage");
  const previewViewport = $("preview-viewport");
  const previewOff = $("preview-off");
  const previewModeBtns = $("preview-mode-btns");
  const previewLoading = $("preview-loading");
  const previewError = $("preview-error");
  const btnPreviewRetry = $("btn-preview-retry");
  const btnUndo = $("btn-undo");
  const btnRedo = $("btn-redo");
  const toastContainer = $("toast-container");
  const obsUrl = $("obs-url");
  const statusEl = $("status");
  const sizeLabel = $("size-label");
  const sizeLabel2 = $("size-label-2");
  const presetList = $("preset-list");
  const btnDirtySave = $("btn-dirty-save");
  const btnDirtyDiscard = $("btn-dirty-discard");
  const btnDirtyUpdate = $("btn-dirty-update");

  /* Preset toolbar more menu */
  const presetMenu = $("preset-toolbar-menu");
  const presetMoreBtn = $("btn-preset-more-btn");
  if (presetMoreBtn && presetMenu) {
    presetMoreBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      presetMenu.hidden = !presetMenu.hidden;
    });
  }
  document.addEventListener("click", () => {
    if (presetMenu && !presetMenu.hidden) {
      presetMenu.hidden = true;
    }
  });
  if (presetMenu) {
    presetMenu.addEventListener("click", () => {
      presetMenu.hidden = true;
    });
  }

  const MAX_TOASTS = 5;

  function toast(msg, type) {
    if (!toastContainer) return;
    const t = type || "info";

    const el = document.createElement("div");
    el.className = "toast-item toast-" + t;
    el.innerHTML =
      '<span class="toast-msg"></span>' +
      '<button type="button" class="toast-close" aria-label="Close">&times;</button>';
    el.querySelector(".toast-msg").textContent = msg;

    const closeBtn = el.querySelector(".toast-close");
    closeBtn.addEventListener("click", () => removeToast(el));

    toastContainer.appendChild(el);

    const items = Array.from(toastContainer.querySelectorAll(".toast-item"));
    const overflow = Math.max(0, items.length - MAX_TOASTS);
    for (let i = 0; i < overflow; i++) {
      removeToast(items[i]);
    }

    const duration = (t === "error" || t === "warning") ? 5000 : 3000;
    el._timer = setTimeout(() => removeToast(el), duration);
  }

  function removeToast(el) {
    if (el._removed) return;
    el._removed = true;
    clearTimeout(el._timer);
    el.classList.add("removing");
    el.addEventListener("animationend", () => {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, { once: true });
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
    } else if (e.key === "Tab") {
      var modal = modalRoot.querySelector('.modal');
      if (!modal) return;
      var focusable = modal.querySelectorAll(
        'button:not([hidden]):not([disabled]), input:not([hidden]):not([disabled]), textarea:not([hidden]):not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  });

  function api(path, opts = {}) {
    return fetch(path, {
      ...opts,
      headers: {
        ...(opts.headers || {}),
        ...authHeaders,
      },
    }).catch((e) => {
      toast("Connection lost", "error");
      throw e;
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

  /* Inline rename: double-click preset name */
  function initInlineRename() {
    const nameEl = $("preset-selected-name");
    if (!nameEl) return;
    let input = null;
    nameEl.addEventListener("dblclick", () => {
      if (!selectedPreset.name || selectedPreset.kind !== "user") return;
      if (input) return;
      const currentName = selectedPreset.name;
      input = document.createElement("input");
      input.type = "text";
      input.className = "preset-rename-input";
      input.value = currentName;
      input.maxLength = 48;
      input.spellcheck = false;
      nameEl.textContent = "";
      nameEl.appendChild(input);
      input.focus();
      input.select();
      function finish(accepted) {
        if (!input) return;
        const newName = input.value.trim();
        input.remove();
        input = null;
        if (accepted && newName && newName !== currentName) {
          doRenamePreset(currentName, newName);
        } else {
          updateDirtyUi();
        }
      }
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); finish(true); }
        else if (e.key === "Escape") { e.preventDefault(); finish(false); }
      });
      input.addEventListener("blur", () => finish(true));
    });
  }

  async function doRenamePreset(oldName, newName) {
    try {
      const res = await api("/api/presets/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_name: oldName, new_name: newName }),
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
      toast("Renamed to " + newName, "success");
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Rename failed", "error");
      updateDirtyUi();
    }
  }

  async function renameSelectedPreset() {
    if (!selectedPreset.name || selectedPreset.kind !== "user") {
      toast("Pick a saved preset first", "warning");
      return;
    }
    const newName = await promptDialog("New name for this preset:", {
      title: "Rename preset",
      value: selectedPreset.name,
      confirmText: "Rename",
    });
    if (newName == null) return;
    if (!newName) { toast("Enter a name", "warning"); return; }
    if (newName === selectedPreset.name) return;
    await doRenamePreset(selectedPreset.name, newName);
  }

  async function duplicateSelectedPreset() {
    if (!selectedPreset.name) {
      toast("Select a preset first", "warning");
      return;
    }
    let name = selectedPreset.kind === "builtin"
      ? selectedPreset.name + " custom"
      : selectedPreset.name + " copy";
    const existing = (presetInfo.user || []).map(p => p.name);
    if (existing.indexOf(name) !== -1) {
      let i = 2;
      while (existing.indexOf(name + " (" + i + ")") !== -1) i++;
      name = name + " (" + i + ")";
    }
    try {
      const res = await api("/api/presets/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "duplicate");
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
      bindForm();
      capturePresetBaseline();
      toast("Duplicated as " + name, "success");
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Duplicate failed", "error");
    }
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
    const dirtyRow = $("preset-toolbar-dirty");
    if (dirtyRow) dirtyRow.hidden = !presetDirty;
    const selName = $("preset-selected-name");
    if (selName) {
      const label = hasSelection ? name : "Unsaved changes";
      const dirtyMark = hasSelection && presetDirty ? " *" : "";
      selName.textContent = label + dirtyMark;
      selName.title = name || "";
    }
    const setBtn = (id, enabled) => {
      const el = $(id);
      if (el) el.disabled = !enabled;
    };
    setBtn("btn-preset-export", hasSelection);
    setBtn("btn-preset-copy", hasSelection);
    setBtn("btn-preset-more-btn", hasSelection);
    const dirtyUpdate = $("btn-dirty-update");
    if (dirtyUpdate) {
      dirtyUpdate.style.display = (isUser && presetDirty) ? "" : "none";
    }
  }

  function updateFeelUi() {
    const feel = cfg.motion_feel || "normal";
    document.querySelectorAll(".feel-pill").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.feel === feel);
    });
    const hint = $("feel-hint");
    if (hint) hint.textContent = FEEL_HINTS[feel] || FEEL_HINTS.custom;
  }

  function updateViewModeUi() {
    const mode = cfg.view_mode === "wrap" ? "infinite" : cfg.view_mode || "infinite";
    const pan = mode !== "fixed";
    document.querySelectorAll("[data-pan-only]").forEach((el) => {
      el.hidden = !pan;
    });
  }

  function updateObsSetupUi() {
    const done = !!cfg.ui_obs_setup_done;
    const card = $("obs-setup-card");
    const badge = $("obs-setup-badge");
    const title = $("obs-setup-title");
    const doneBtn = $("btn-setup-done");
    if (card) card.classList.toggle("first-run", !done);
    if (badge) {
      badge.hidden = done;
    }
    if (title) title.textContent = "Browser source";
    if (doneBtn) doneBtn.hidden = done;
  }

  function loadPreview() {
    const mode = previewAuto
      ? (document.hasFocus() ? "live" : "off")
      : (previewMode || "lite");
    if (mode === "off") {
      try {
        frame.removeAttribute("src");
        frame.src = "about:blank";
      } catch (_) {}
      frame.hidden = true;
      if (previewViewport) previewViewport.classList.add("is-off");
      if (previewOff) {
        previewOff.hidden = false;
        previewOff.classList.add("is-visible");
      }
      if (previewLoading) previewLoading.hidden = true;
      if (previewError) previewError.hidden = true;
      return;
    }
    if (previewOff) {
      previewOff.classList.remove("is-visible");
      previewOff.hidden = true;
    }
    if (previewViewport) previewViewport.classList.remove("is-off");
    if (previewError) previewError.hidden = true;
    frame.hidden = false;
    layoutPreviewCanvas();
    const u = overlayUrl();
    if (!u || !cfg.port) return;
    const sep = u.includes("?") ? "&" : "?";
    const extra = mode === "lite" ? "preview=lite&" : "";
    if (previewLoading) previewLoading.hidden = false;
    frame.src = u + sep + extra + "_=" + Date.now();
  }

  function updatePreviewModeBtns() {
    if (!previewModeBtns) return;
    const mode = previewMode || "lite";
    previewModeBtns.querySelectorAll(".preview-mode-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.mode === mode);
    });
  }

  function onPreviewLoad() {
    if (previewLoading) previewLoading.hidden = true;
    if (previewError) previewError.hidden = true;
  }

  function onPreviewError() {
    if (previewLoading) previewLoading.hidden = true;
    if (previewError) previewError.hidden = false;
  }

  function setPreviewMode(mode, persist) {
    const valid = ["off", "lite", "live", "auto"];
    previewMode = valid.indexOf(mode) !== -1 ? mode : "lite";
    previewAuto = mode === "auto";
    updatePreviewModeBtns();
    loadPreview();
    if (persist) queuePatch({ ui_preview_mode: previewMode });
  }

  function showSection(id, persist) {
    if (id === "grid" || id === "border") id = "background";
    currentSection = id || "presets";
    document.querySelectorAll(".sec-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.section === currentSection);
    });
    document.querySelectorAll(".block.sec").forEach((el) => {
      el.hidden = el.dataset.section !== currentSection;
    });
    if (persist) queuePatch({ ui_section: currentSection });
  }

  function updateSectionDots() {
    document.querySelectorAll(".sec-btn").forEach((btn) => {
      var section = btn.dataset.section;
      var keys = SECTION_KEYS[section];
      if (!keys || !keys.length) {
        btn.querySelector(".sec-dot").classList.remove("modified");
        return;
      }
      var baseline = presetBaseline || DEFAULT_CFG;
      var modified = keys.some(function (key) {
        if (presetExclude.has(key)) return false;
        var cur = cfg[key];
        var def = baseline[key];
        if (cur == null && def == null) return false;
        if (cur == null || def == null) return true;
        if (typeof cur === "object" || typeof def === "object") {
          return JSON.stringify(cur) !== JSON.stringify(def);
        }
        return cur !== def;
      });
      btn.querySelector(".sec-dot").classList.toggle("modified", modified);
    });
  }

  function getFieldRows(section) {
    const rows = [];
    const children = section.children;
    for (let i = 0; i < children.length; i++) {
      const el = children[i];
      if (el.tagName === 'H2') continue;
      if (el.classList.contains('row2') || el.classList.contains('click-buttons')) {
        for (let j = 0; j < el.children.length; j++) {
          rows.push(el.children[j]);
        }
      } else {
        rows.push(el);
      }
    }
    return rows;
  }

  function getRowSearchText(row) {
    const labels = row.querySelectorAll('label, .slider-h span, h3, .feel-pill, .btn, strong, .setup-card-h strong');
    let text = '';
    labels.forEach(function(el) {
      text += ' ' + (el.textContent || '');
    });
    return text;
  }

  function filterSettings(query) {
    var q = query.toLowerCase().trim();
    var sections = document.querySelectorAll('.block.sec');
    var anyVisible = false;
    var searchEmpty = document.getElementById('search-empty');

    sections.forEach(function(section) {
      var heading = section.querySelector('h2');
      var headingText = heading ? heading.textContent.toLowerCase() : '';
      var headingMatch = q === '' || headingText.indexOf(q) !== -1;

      var rows = getFieldRows(section);
      var sectionHasMatch = headingMatch;

      rows.forEach(function(row) {
        var rowText = getRowSearchText(row).toLowerCase();
        var match = q === '' || headingMatch || rowText.indexOf(q) !== -1;
        row.classList.toggle('search-hidden', !match);
        if (match) sectionHasMatch = true;
      });

      if (q === '') {
        section.hidden = section.dataset.section !== currentSection;
      } else {
        section.hidden = !sectionHasMatch;
      }

      if (!section.hidden) anyVisible = true;
    });

    if (searchEmpty) {
      searchEmpty.hidden = q === '' || anyVisible;
    }
  }

  function pushUndo() {
    undoStack.push(structuredClone(cfg));
    if (undoStack.length > MAX_UNDO) undoStack.shift();
    redoStack.length = 0;
  }

  async function undo() {
    if (undoStack.length === 0) return;
    redoStack.push(structuredClone(cfg));
    var prev = undoStack.pop();
    cfg = prev;
    bindForm();
    flashSettingsPanel();
    updateUndoRedoButtons();
    try {
      await api("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
    } catch (_) {}
  }

  async function redo() {
    if (redoStack.length === 0) return;
    undoStack.push(structuredClone(cfg));
    var next = redoStack.pop();
    cfg = next;
    bindForm();
    flashSettingsPanel();
    updateUndoRedoButtons();
    try {
      await api("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
    } catch (_) {}
  }

  function flashSettingsPanel() {
    var main = document.querySelector(".panel-main");
    if (!main) return;
    main.classList.remove("settings-flash");
    void main.offsetWidth;
    main.classList.add("settings-flash");
  }

  function updateUndoRedoButtons() {
    if (btnUndo) btnUndo.disabled = undoStack.length === 0;
    if (btnRedo) btnRedo.disabled = redoStack.length === 0;
  }

  function bindForm() {
    suppress = true;
    document.querySelectorAll("[data-key]").forEach((el) => {
      const key = el.getAttribute("data-key");
      let val = cfg[key];
      if (el.type === "checkbox") {
        el.checked = !!val;
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
    updateFeelUi();
    updateViewModeUi();

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
    updateGlowOptionsUi();
    updateHotkeyUi();
    updateStartupUi();

    suppress = false;
    updateSizeLabels();
    updateFeelUi();
    updateObsSetupUi();
    renderPresetList();
    recomputePresetDirty();
    updateSectionDots();
  }

  function updateStartupUi() {
    const auto = !!cfg.start_with_windows;
    const autostartSupported = !runtimeStatus || runtimeStatus.autostart_supported !== false;
    const autoChk = $("chk-autostart");
    const autoNote = $("autostart-note");
    const minLabel = $("label-minimized");
    const minChk = $("chk-minimized");
    if (autoChk) autoChk.disabled = !autostartSupported;
    if (autoNote) {
      autoNote.hidden = autostartSupported;
      autoNote.textContent = autostartSupported
        ? ""
        : "Autostart is unavailable in the itch.io edition so uninstalling cannot leave a registry entry behind.";
    }
    if (minLabel) minLabel.classList.toggle("is-disabled", !auto || !autostartSupported);
    if (minChk) {
      minChk.disabled = !auto || !autostartSupported;
      if (!auto) minChk.checked = false;
    }
  }

  function applyAccentColors(cfg) {
    var root = document.documentElement;
    if (cfg.accent_color) {
      root.style.setProperty('--accent', cfg.accent_color);
      root.style.setProperty('--accent-hover', cfg.accent_color);
      root.style.setProperty('--focus', cfg.accent_color);
    }
    if (cfg.bg_color) {
      root.style.setProperty('--bg', cfg.bg_color);
    }
  }

  let runtimeStatus = null;
  let updateState = null;
  let updatePollBusy = false;
  let updateModalOpen = false;
  let updateModalVersion = null;

  const updateModalRoot = $("update-modal-root");
  const updateModalTitle = $("update-modal-title");
  const updateModalNotes = $("update-modal-notes");
  const updateModalInstall = $("update-modal-install");
  const updateModalLater = $("update-modal-later");
  const updateModalSkip = $("update-modal-skip");

  function renderUpdatePanel(state) {
    updateState = state || null;
    const line = $("update-status-line");
    const errEl = $("update-error");
    const btnCheck = $("btn-update-check");

    const current = (state && state.current_version) || (cfg && cfg.version) || "";
    const checking = !!(state && state.checking);
    const installing = !!(state && state.installing);
    const progress = state && state.download_progress;
    const available = !!(state && state.available && state.pending);
    const latest = state && (state.latest_version || (state.pending && state.pending.version));
    const managedExternally = !!(state && state.managed_externally);
    const updateSelect = $("sel-update-check");

    if (line) {
      let text = current ? "v" + current : "-";
      if (managedExternally) text += " - Updates managed by itch.io";
      else if (checking) text += " - Checking...";
      else if (installing) {
        const pct =
          progress != null && progress >= 0
            ? " " + Math.round(Number(progress) * 100) + "%"
            : "";
        text += " - Downloading..." + pct;
      } else if (available && latest) text += " - v" + latest + " available";
      line.textContent = text;
    }

    if (errEl) {
      const err = state && state.last_error;
      if (err) {
        errEl.hidden = false;
        errEl.textContent = err;
      } else {
        errEl.hidden = true;
        errEl.textContent = "";
      }
    }

    const busy = checking || installing;
    if (btnCheck) {
      btnCheck.disabled = busy || managedExternally;
      btnCheck.textContent = managedExternally
        ? "Managed by itch.io"
        : checking
          ? "Checking..."
          : "Check now";
    }
    if (updateSelect) updateSelect.disabled = managedExternally;

    if (managedExternally && updateModalOpen) {
      closeUpdateModal();
    } else if (updateModalOpen) {
      syncUpdateModal(state);
    } else {
      maybeShowUpdateModal(state);
    }
  }

  function maybeShowUpdateModal(state) {
    if (!updateModalRoot || !state) return;
    if (!state.should_prompt || !state.available || !state.pending) return;
    if (state.checking || state.installing) return;
    const ver = String(state.latest_version || state.pending.version || "");
    if (!ver) return;
    if (updateModalOpen && updateModalVersion === ver) return;
    openUpdateModal(state);
  }

  function openUpdateModal(state) {
    if (!updateModalRoot) return;
    updateModalOpen = true;
    updateModalVersion = String(
      (state && (state.latest_version || (state.pending && state.pending.version))) || ""
    );
    syncUpdateModal(state);
    updateModalRoot.hidden = false;
    setTimeout(() => {
      if (updateModalInstall) updateModalInstall.focus();
    }, 0);
  }

  function closeUpdateModal() {
    if (!updateModalRoot) return;
    updateModalRoot.hidden = true;
    updateModalOpen = false;
    updateModalVersion = null;
  }

  function formatUpdateNotes(raw) {
    let text = String(raw || "").replace(/\r\n/g, "\n");
    const lines = text.split("\n").map((line) => {
      let s = line.replace(/\*\*/g, "").replace(/__/g, "");
      const t = s.trim();
      if (t.startsWith("#")) s = t.replace(/^#+\s*/, "");
      return s;
    });
    text = lines.join("\n");
    while (text.indexOf("\n\n\n") >= 0) text = text.replace(/\n\n\n/g, "\n\n");
    text = text.trim();
    return text || "(No release notes)";
  }

  function syncUpdateModal(state) {
    if (!state) return;
    const ver =
      state.latest_version ||
      (state.pending && state.pending.version) ||
      updateModalVersion ||
      "";
    const notes = formatUpdateNotes(
      state.notes || (state.pending && state.pending.notes) || ""
    );
    const installing = !!(state.installing);
    const progress = state.download_progress;
    const busy = !!(state.checking || installing);

    if (updateModalTitle) {
      updateModalTitle.textContent = ver ? "Velo " + ver + " available" : "Update available";
    }
    if (updateModalNotes) updateModalNotes.textContent = notes;
    if (updateModalInstall) {
      updateModalInstall.disabled = busy || !state.available;
      updateModalInstall.textContent = installing
        ? progress != null
          ? "Downloading... " + Math.round(Number(progress) * 100) + "%"
          : "Downloading..."
        : "Download and install";
    }
    if (updateModalLater) updateModalLater.disabled = busy;
    if (updateModalSkip) updateModalSkip.disabled = busy;
  }

  async function refreshUpdateStatus() {
    if (updatePollBusy) return;
    updatePollBusy = true;
    try {
      const res = await api("/api/update");
      const data = await readJson(res);
      if (res.ok) renderUpdatePanel(data);
    } catch (_) {
      /* keep last panel */
    } finally {
      updatePollBusy = false;
    }
  }

  async function checkForUpdates() {
    const btnCheck = $("btn-update-check");
    if (btnCheck) {
      btnCheck.disabled = true;
      btnCheck.textContent = "Checking\u2026";
    }
    toast("Checking for updates\u2026");
    try {
      const res = await api("/api/update/check", { method: "POST" });
      const data = await readJson(res);
      if (!res.ok || data.ok === false) throw new Error(data.error || "Check failed");
      renderUpdatePanel(data);
      if (data.available && data.latest_version) {
        openUpdateModal(data);
      } else if (!data.last_error) {
        toast("Up to date", "success");
      } else {
        toast(data.last_error, "error");
      }
    } catch (e) {
      toast(String(e.message || e) || "Check failed", "error");
      await refreshUpdateStatus();
    }
  }

  async function remindUpdateLater() {
    try {
      const res = await api("/api/update/remind", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await readJson(res);
      if (!res.ok || data.ok === false) throw new Error(data.error || "Failed");
      closeUpdateModal();
      renderUpdatePanel(data);
      toast("Later");
    } catch (e) {
      toast(String(e.message || e) || "Failed", "error");
    }
  }

  async function skipUpdateVersion() {
    const ver =
      (updateState && updateState.latest_version) ||
      (updateState && updateState.pending && updateState.pending.version) ||
      updateModalVersion ||
      "";
    try {
      const res = await api("/api/update/skip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ver ? { version: ver } : {}),
      });
      const data = await readJson(res);
      if (!res.ok || data.ok === false) throw new Error(data.error || "Failed");
      closeUpdateModal();
      renderUpdatePanel(data);
      toast(ver ? "Skipped v" + ver : "Skipped");
    } catch (e) {
      toast(String(e.message || e) || "Failed", "error");
    }
  }

  async function installUpdate() {
    try {
      const res = await api("/api/update/install", { method: "POST" });
      const data = await readJson(res);
      if (!res.ok || data.ok === false) throw new Error(data.error || "Install failed");
      renderUpdatePanel(data);
      if (!updateModalOpen) openUpdateModal(data);
      else syncUpdateModal(data);
      const tick = async () => {
        await refreshUpdateStatus();
        if (updateState && updateState.installing) {
          setTimeout(tick, 500);
        } else if (updateState && updateState.last_error) {
          toast(updateState.last_error, "error");
          if (updateModalOpen) syncUpdateModal(updateState);
        }
      };
      setTimeout(tick, 400);
    } catch (e) {
      toast(String(e.message || e) || "Install failed", "error");
      await refreshUpdateStatus();
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

  function updateGlowOptionsUi() {
    const glowOn = !!cfg.trail_glow;
    const glowOpts = $("glow-options");
    if (glowOpts) glowOpts.hidden = !glowOn;
    const customColor = !!cfg.trail_glow_custom_color;
    const colorField = $("glow-color-field");
    if (colorField) colorField.hidden = !customColor;
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
    if (!applyTimer) {
      undoSnapshot = structuredClone(cfg);
    }
    Object.assign(cfg, patch);
    // push to preview iframe immediately for live slider feedback
    if (frame && frame.contentWindow) {
      try { frame.contentWindow.postMessage({ type: "velo-patch", data: patch }, "*"); } catch (_) {}
    }
    updateSectionDots();
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
        } else {
          el.value = patch[key];
        }
      });
      document.querySelectorAll(`[data-link="${key}"]`).forEach((el) => {
        el.value = patch[key];
      });
    });
    suppress = false;

    if (
      "motion_feel" in patch ||
      "motion_scale" in patch ||
      "motion_ease" in patch ||
      "camera_lag" in patch ||
      "view_zoom" in patch
    ) {
      updateFeelUi();
    }
    if ("view_mode" in patch) {
      if (patch.view_mode === "wrap") patch.view_mode = "infinite";
      updateViewModeUi();
    }
    if ("speed_colorize" in patch) updateTrailColorUi();
    if ("trail_glow" in patch || "trail_glow_custom_color" in patch) updateGlowOptionsUi();
    if ("start_with_windows" in patch || "start_minimized" in patch) {
      if ("start_with_windows" in patch && !patch.start_with_windows) {
        cfg.start_minimized = false;
        patch.start_minimized = false;
      }
      updateStartupUi();
    }
    if ("accent_color" in patch || "bg_color" in patch) {
      applyAccentColors(cfg);
    }
    if ("pad_bg_image" in patch || "pad_bg_image_enabled" in patch) {
      updateBgImageUi();
    }
    const dirtyKeys = Object.keys(patch).filter((k) => !presetExclude.has(k));
    if (dirtyKeys.length) recomputePresetDirty();

    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => {
      if (undoSnapshot) {
        undoStack.push(undoSnapshot);
        if (undoStack.length > MAX_UNDO) undoStack.shift();
        redoStack.length = 0;
        undoSnapshot = null;
        updateUndoRedoButtons();
      }
      persist(patch);
    }, 80);
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
      if (!res.ok) {
        let msg = "Save failed";
        try {
          const errData = await res.json();
          if (errData.error) msg += ": " + errData.error;
        } catch (_) {}
        throw new Error(msg);
      }
      const data = await res.json();
      if (data.data) {
        cfg = data.data;
        updateSectionDots();
        if ("render_quality" in patch || "motion_feel" in patch || "preset_hotkeys" in patch || "pad_bg_image" in patch || "pad_bg_image_enabled" in patch) bindForm();
        else {
          updateFeelUi();
          recomputePresetDirty();
          updateSectionDots();
        }
      }
      updateSizeLabels();
      updateObsSetupUi();
    } catch (e) {
      statusEl.textContent = e.message || "Save failed";
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
    var activeName = cfg.active_preset || presetInfo.active || "";
    var activeKind = cfg.active_preset_kind || presetInfo.active_kind || "builtin";
    var users = presetInfo.user || [];
    var builtins = presetInfo.builtin || [];
    var hiddenPresets = cfg.hidden_presets || [];

    var html = "";

    users.forEach(function (p) {
      html += renderPresetItem(p.name, "user", activeName, activeKind);
    });

    builtins.forEach(function (p) {
      if (hiddenPresets.indexOf(p.name) === -1) {
        html += renderPresetItem(p.name, "builtin", activeName, activeKind);
      }
    });

    if (!html) {
      html = '<div class="preset-empty">No presets.</div>';
    }

    presetList.innerHTML = html;

    presetList.querySelectorAll(".preset-item").forEach(function (el) {
      el.addEventListener("click", function (e) {
        if (e.target.closest(".preset-delete")) return;
        applyPreset(el.dataset.preset, el.dataset.type);
      });
    });

    presetList.querySelectorAll(".preset-delete").forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.stopPropagation();
        var item = el.closest(".preset-item");
        var name = item.dataset.preset;
        var type = item.dataset.type;
        if (type === "user") {
          deletePresetByName(name);
        } else {
          hidePreset(name);
        }
      });
    });

    updateDirtyUi();
  }

  function renderPresetItem(name, type, activeName, activeKind) {
    var isActive = name === activeName && type === activeKind;
    var cls = "preset-item" + (isActive ? " active" : "");
    var badge = "";
    if (isActive) {
      badge = '<span class="preset-badge active-badge">active</span>';
    } else if (type === "builtin") {
      badge = '<span class="preset-badge default-badge">default</span>';
    }
    return (
      '<div class="' + cls + '" data-preset="' + escapeHtml(name) + '" data-type="' + type + '">' +
      '<span class="preset-name">' + escapeHtml(name) + (isActive && presetDirty ? " *" : "") + '</span>' +
      badge +
      '<button class="preset-delete" title="Remove">&times;</button>' +
      '</div>'
    );
  }

  function hidePreset(name) {
    var hidden = cfg.hidden_presets || [];
    if (hidden.indexOf(name) === -1) {
      hidden = hidden.concat([name]);
      queuePatch({ hidden_presets: hidden });
      renderPresetList();
    }
  }

  async function deletePresetByName(name) {
    var ok = await confirmDialog('Delete "' + name + '"?', {
      title: "Delete preset",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      var res = await api("/api/presets/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name }),
      });
      var data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "delete");
      if (data.data) cfg = data.data;
      toast("Deleted " + name, "success");
      if (selectedPreset.name === name && selectedPreset.kind === "user") {
        selectedPreset = { name: cfg.active_preset || "", kind: cfg.active_preset_kind || "builtin" };
      }
      await refreshPresets();
      bindForm();
    } catch (e) {
      toast(String(e.message || e) || "Delete failed", "error");
    }
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

  async function applyPreset(name, kind, opts) {
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
      updateSectionDots();
      if (!(opts && opts.silent)) toast(name);
      await refreshPresets();
    } catch (e) {
      toast("Couldn't load preset", "error");
    }
  }

  async function savePresetAs() {
    let name = "";
    if (presetDirty && selectedPreset.name) {
      name = selectedPreset.kind === "builtin"
        ? selectedPreset.name + " custom"
        : selectedPreset.name + " copy";
    }
    name = await promptDialog("Name for new preset:", {
      title: "Save preset",
      value: name,
      confirmText: "Save",
    });
    if (name == null) return;
    if (!name) { toast("Enter a name", "warning"); return; }
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
      bindForm();
      capturePresetBaseline();
      updateSectionDots();
      toast("Saved " + name, "success");
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Save failed", "error");
    }
  }

  async function updateSelectedPreset() {
    if (!selectedPreset.name || selectedPreset.kind !== "user") {
      toast("Pick a saved preset first", "warning");
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
      updateSectionDots();
      updateDirtyUi();
      toast("Updated " + selectedPreset.name, "success");
      await refreshPresets();
    } catch (e) {
      toast(String(e.message || e) || "Update failed", "error");
    }
  }

  async function exportSelectedPresetFile() {
    if (!selectedPreset.name) {
      toast("Select a preset first", "warning");
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
      toast("Preset exported", "success");
    } catch (e) {
      toast(String(e.message || e) || "Export failed", "error");
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
      toast("Select a preset first", "warning");
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
      toast(ok ? "Preset code copied" : "Code ready to copy", "success");
    } catch (e) {
      toast(String(e.message || e) || "Copy failed", "error");
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
      await refreshPresets();
      toast("Preset imported", "success");
    } catch (e) {
      toast(String(e.message || e) || "Import failed", "error");
    }
  }

  async function importPresetFromCodeInput() {
    const input = $("preset-code-input");
    const text = input ? String(input.value || "").trim() : "";
    if (!text) {
      toast("Paste a share code first", "warning");
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
      await refreshPresets();
      toast("Preset imported", "success");
    } catch (e) {
      toast(String(e.message || e) || "Import failed", "error");
    }
  }

  async function loadConfig() {
    const res = await api("/api/config");
    if (!res.ok) throw new Error("config");
    cfg = await res.json();
    if (cfg.view_mode === "wrap") cfg.view_mode = "infinite";
    await refreshPresets();
    previewMode = cfg.ui_preview_mode || "lite";
    previewAuto = previewMode === "auto";
    updatePreviewModeBtns();
    selectedPreset = {
      name: cfg.active_preset || "",
      kind: cfg.active_preset_kind || "builtin",
    };
    let section = cfg.ui_section || (!cfg.ui_obs_setup_done ? "obs" : "presets");
    if (section === "backup") section = "settings";
    showSection(section, false);
    bindForm();
    applyAccentColors(cfg);
    capturePresetBaseline();
    updateSectionDots();
    loadPreview();
    updateUndoRedoButtons();
    document.getElementById("skeleton-loader")?.remove();
    if (!cfg.ui_obs_setup_done) {
      showSection("obs", false);
    }
    refreshUpdateStatus();
  }

  async function poll() {
    try {
      const res = await api("/api/status");
      const s = await res.json();
      runtimeStatus = s;
      updateStartupUi();
      const aboutVersion = $("about-version");
      const aboutDistribution = $("about-distribution");
      const recoveryNotice = $("recovery-notice");
      if (aboutVersion) aboutVersion.textContent = s.version ? "v" + s.version : "-";
      if (aboutDistribution) {
        aboutDistribution.textContent = s.distribution_label || "Standard edition";
      }
      if (recoveryNotice) {
        const notice = String(s.recovery_notice || "").trim();
        recoveryNotice.hidden = !notice;
        recoveryNotice.textContent = notice;
      }
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
    refreshUpdateStatus();
  }

  async function exportSettings() {
    try {
      const choice = await showModal({
        title: "Export settings",
        message:
          "A safe export excludes the local host, port, and authentication token. Use a full backup only for private recovery.",
        confirmText: "Safe export",
        secondaryText: "Full backup",
        cancelText: "Cancel",
      });
      if (!choice.ok || choice.action === "cancel") return;
      const includeConnection = choice.action === "secondary";
      const res = await api("/api/config/export-dialog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_connection: includeConnection }),
      });
      const data = await readJson(res);
      if (data.cancelled) return;
      if (!res.ok || !data.ok) throw new Error(data.error || "export");
      toast(includeConnection ? "Full backup saved" : "Safe settings export saved", "success");
    } catch (e) {
      toast(String(e.message || e) || "Export failed", "error");
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
      await refreshPresets();
      toast("Imported", "success");
    } catch (e) {
      toast(String(e.message || e) || "Import failed", "error");
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
    toast("Size " + text, "success");
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

  async function copyDiagnostics() {
    try {
      const res = await api("/api/diagnostics");
      const data = await readJson(res);
      if (!res.ok || !data.ok) throw new Error(data.error || "diagnostics");
      const ok = await copyText(String(data.text || ""));
      if (!ok) throw new Error("Clipboard unavailable");
      toast("Diagnostics copied", "success");
    } catch (e) {
      toast(String(e.message || e) || "Could not copy diagnostics", "error");
    }
  }

  async function runSupportAction(endpoint, successMessage) {
    try {
      const res = await api(endpoint, { method: "POST" });
      const data = await readJson(res);
      if (!res.ok || !data.ok) throw new Error(data.error || "action failed");
      toast(successMessage, "success");
    } catch (e) {
      toast(String(e.message || e) || "Action failed", "error");
    }
  }

  async function copyUrl() {
    if (await copyText(overlayUrl())) {
      toast("URL copied", "success");
      if (!cfg.ui_obs_setup_done) {
        queuePatch({ ui_obs_setup_done: true });
        updateObsSetupUi();
      }
    } else {
      toast("Copy failed", "error");
    }
  }

  const tipEl = document.createElement("div");
  tipEl.id = "tip-float";
  document.body.appendChild(tipEl);
  let tipAnchor = null;
  let tipTimer = null;

  function placeTip(el) {
    const text = el.getAttribute("data-tip");
    if (!text) return;
    tipAnchor = el;
    tipEl.textContent = text;
    const r = el.getBoundingClientRect();
    const pad = 8;
    const tw = tipEl.offsetWidth || 200;
    const th = tipEl.offsetHeight || 40;
    let left = r.left + r.width / 2 - tw / 2;
    let top = r.top - th - pad;
    if (top < pad) {
      top = r.bottom + pad;
    }
    if (left < pad) left = pad;
    if (left + tw > window.innerWidth - pad) {
      left = window.innerWidth - tw - pad;
    }
    if (top + th > window.innerHeight - pad) {
      top = window.innerHeight - th - pad;
    }
    tipEl.style.left = Math.round(left) + "px";
    tipEl.style.top = Math.round(top) + "px";
    tipEl.classList.add("show");
  }

  function hideTip() {
    tipAnchor = null;
    clearTimeout(tipTimer);
    tipTimer = null;
    tipEl.classList.remove("show");
  }

  document.addEventListener(
    "mouseover",
    (e) => {
      const el = e.target.closest(".info[data-tip]");
      if (!el) return;
      clearTimeout(tipTimer);
      tipTimer = setTimeout(() => placeTip(el), 300);
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
      clearTimeout(tipTimer);
      tipTimer = null;
      if (tipAnchor === el) hideTip();
    },
    true
  );
  document.addEventListener("focusin", (e) => {
    const el = e.target.closest && e.target.closest(".info[data-tip]");
    if (!el) return;
    clearTimeout(tipTimer);
    tipTimer = null;
    placeTip(el);
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
        toast("Stats reset", "success");
      } catch (_) {
        toast("Could not reset stats", "error");
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
    btn.addEventListener("click", () => {
      if (searchInput && searchInput.value) {
        searchInput.value = '';
        filterSettings('');
        if (searchClear) searchClear.hidden = true;
      }
      showSection(btn.dataset.section, true);
    });
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
  if ($("btn-copy-diagnostics")) {
    $("btn-copy-diagnostics").addEventListener("click", copyDiagnostics);
  }
  if ($("btn-open-logs")) {
    $("btn-open-logs").addEventListener("click", () =>
      runSupportAction("/api/support/open-logs", "Logs folder opened")
    );
  }
  if ($("btn-open-config")) {
    $("btn-open-config").addEventListener("click", () =>
      runSupportAction("/api/support/open-config", "Config folder opened")
    );
  }
  if ($("btn-report-problem")) {
    $("btn-report-problem").addEventListener("click", () =>
      runSupportAction("/api/support/report", "Issue page opened")
    );
  }
  if ($("btn-project-page")) {
    $("btn-project-page").addEventListener("click", () =>
      runSupportAction("/api/support/project", "GitHub opened")
    );
  }
  if ($("btn-third-party")) {
    $("btn-third-party").addEventListener("click", () =>
      runSupportAction("/api/support/licenses", "Third-party notices opened")
    );
  }
  if ($("btn-update-check")) $("btn-update-check").addEventListener("click", checkForUpdates);
  if (updateModalInstall) updateModalInstall.addEventListener("click", installUpdate);
  if (updateModalLater) updateModalLater.addEventListener("click", remindUpdateLater);
  if (updateModalSkip) updateModalSkip.addEventListener("click", skipUpdateVersion);
  document.addEventListener("keydown", (e) => {
    if (!updateModalRoot || updateModalRoot.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      if (updateState && updateState.installing) return;
      if (updateModalLater && !updateModalLater.disabled) remindUpdateLater();
    }
  }, true);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshUpdateStatus();
  });
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
      toast("Look reset", "success");
    });
  }
  if ($("btn-setup-done")) {
    $("btn-setup-done").addEventListener("click", () => {
      queuePatch({ ui_obs_setup_done: true });
      updateObsSetupUi();
      toast("OK", "success");
    });
  }
  if (btnDirtySave) btnDirtySave.addEventListener("click", savePresetAs);
  if (btnDirtyDiscard) {
    btnDirtyDiscard.addEventListener("click", async () => {
      const name = selectedPreset.name || cfg.active_preset || "";
      const kind = selectedPreset.kind || cfg.active_preset_kind || "builtin";
      if (!name) {
        toast("No preset selected", "warning");
        return;
      }
      await applyPreset(name, kind, { silent: true });
      toast("Changes discarded", "success");
    });
  }
  $("btn-reload").addEventListener("click", loadPreview);
  if (frame) {
    frame.addEventListener("load", onPreviewLoad);
    frame.addEventListener("error", onPreviewError);
  }
  if (btnPreviewRetry) btnPreviewRetry.addEventListener("click", loadPreview);
  if (btnUndo) btnUndo.addEventListener("click", undo);
  if (btnRedo) btnRedo.addEventListener("click", redo);
  if (previewModeBtns) {
    previewModeBtns.querySelectorAll(".preview-mode-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        setPreviewMode(btn.dataset.mode, true);
      });
    });
  }
  // Handle actual tab/window hiding (browser tab switch)
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (previewAuto && !frame.hidden) {
        frame.hidden = true;
        if (previewViewport) previewViewport.classList.add("is-off");
        if (previewOff) {
          previewOff.hidden = false;
          previewOff.classList.add("is-visible");
        }
      }
    } else {
      if (previewAuto && frame.hidden) loadPreview();
    }
  });

  window.addEventListener("blur", () => {
    if (previewAuto && !frame.hidden) {
      frame.hidden = true;
      if (previewViewport) previewViewport.classList.add("is-off");
      if (previewOff) {
        previewOff.hidden = false;
        previewOff.classList.add("is-visible");
      }
    }
  });

  window.addEventListener("focus", () => {
    if (previewAuto && frame.hidden) loadPreview();
  });
  $("checker").addEventListener("change", (e) => {
    stage.classList.toggle("plain", !e.target.checked);
  });
  if (typeof ResizeObserver !== "undefined" && stage) {
    new ResizeObserver(() => layoutPreviewCanvas()).observe(stage);
  }
  window.addEventListener("resize", layoutPreviewCanvas);

  if ($("btn-preset-export")) $("btn-preset-export").addEventListener("click", exportSelectedPresetFile);
  if ($("btn-preset-copy")) $("btn-preset-copy").addEventListener("click", copySelectedPreset);
  if ($("btn-preset-rename")) $("btn-preset-rename").addEventListener("click", renameSelectedPreset);
  if ($("btn-preset-duplicate")) $("btn-preset-duplicate").addEventListener("click", duplicateSelectedPreset);
  if (btnDirtyUpdate) btnDirtyUpdate.addEventListener("click", updateSelectedPreset);
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
    toast("Reset", "success");
  });

  $("btn-restart").addEventListener("click", async () => {
    await persist({
      host: cfg.host,
      port: cfg.port,
      auth_token: cfg.auth_token,
    });
    toast("Restarting…");
    try {
      await api("/api/server/restart", { method: "POST" });
    } catch (_) {}
    setTimeout(() => {
      location.href =
        location.pathname +
        (cfg.auth_token ? `?token=${encodeURIComponent(cfg.auth_token)}` : "");
    }, 700);
  });

  /* Double-click slider/val-input - reset to default */
  document.addEventListener("dblclick", (e) => {
    const slider = e.target.closest("[data-key]");
    const valInput = e.target.closest(".val-input[data-link]");
    if (!slider && !valInput) return;
    const key = slider ? slider.getAttribute("data-key") : valInput.getAttribute("data-link");
    if (!key || !(key in DEFAULT_CFG)) return;
    queuePatch({ [key]: DEFAULT_CFG[key] });
    e.preventDefault();
  });

  /* Background image */
  const btnBgImage = $("btn-bg-image");
  const btnBgImageClear = $("btn-bg-image-clear");
  function updateBgImageUi() {
    const enabled = !!cfg.pad_bg_image_enabled;
    const has = enabled && !!cfg.pad_bg_image;
    if (btnBgImage) btnBgImage.textContent = has ? "Change image..." : "Choose image...";
    if (btnBgImageClear) btnBgImageClear.hidden = !has;
    const opts = $("bg-image-opts");
    if (opts) opts.hidden = !has;
  }
  if (btnBgImage) {
    btnBgImage.addEventListener("click", async () => {
      try {
        const res = await api("/api/config/bg-image-dialog", { method: "POST" });
        const data = await readJson(res);
        if (data.cancelled) return;
        if (!res.ok || !data.ok) throw new Error(data.error || "bg image");
        if (data.data && data.data.pad_bg_image) {
          queuePatch({ pad_bg_image: data.data.pad_bg_image });
        }
      } catch (e) {
        toast(String(e.message || e) || "Image failed", "error");
      }
    });
  }
  if (btnBgImageClear) {
    btnBgImageClear.addEventListener("click", () => {
      queuePatch({ pad_bg_image: "" });
    });
  }

  /* Preset hotkeys - dynamic from cfg.preset_hotkeys */
  const presetHotkeysEl = $("preset-hotkeys");
  let presetHotkeyListeningIdx = -1;
  let presetHotkeyStop = null;

  function getPresetNames() {
    const names = [];
    (presetInfo.user || []).forEach(p => names.push(p.name));
    (presetInfo.builtin || []).forEach(p => {
      if (!(cfg.hidden_presets || []).includes(p.name)) names.push(p.name);
    });
    return names;
  }

  function renderPresetHotkeys() {
    if (!presetHotkeysEl) return;
    const hotkeys = cfg.preset_hotkeys || [];
    const names = getPresetNames();
    presetHotkeysEl.replaceChildren();
    hotkeys.forEach((entry, i) => {
      const key = String(entry.key || "");
      const target = String(entry.target || "");
      const row = document.createElement("div");
      row.className = "phk";
      row.dataset.idx = String(i);
      const select = document.createElement("select");
      select.className = "phk-target";
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "Empty";
      select.appendChild(empty);
      names.forEach((name) => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        option.selected = name === target;
        select.appendChild(option);
      });
      const bind = document.createElement("button");
      bind.type = "button";
      bind.className = "btn btn-sm phk-bind";
      bind.textContent = key || "Click to bind";
      const clear = document.createElement("button");
      clear.type = "button";
      clear.className = "phk-clear";
      clear.title = "Remove";
      clear.textContent = "X";
      row.append(select, bind, clear);
      presetHotkeysEl.appendChild(row);
    });
    wirePresetHotkeyEvents();
  }

  function wirePresetHotkeyEvents() {
    if (!presetHotkeysEl) return;
    presetHotkeysEl.querySelectorAll(".phk-target").forEach((sel) => {
      sel.addEventListener("change", () => {
        const idx = parseInt(sel.closest(".phk").dataset.idx, 10);
        const hotkeys = (cfg.preset_hotkeys || []).slice();
        if (idx < hotkeys.length) hotkeys[idx] = { ...hotkeys[idx], target: sel.value };
        queuePatch({ preset_hotkeys: hotkeys });
      });
    });
    presetHotkeysEl.querySelectorAll(".phk-bind").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.closest(".phk").dataset.idx, 10);
        if (presetHotkeyListeningIdx >= 0) {
          stopPresetHotkeyListen();
          return;
        }
        presetHotkeyListeningIdx = idx;
        btn.textContent = "Press keys...";
        btn.classList.add("listening");
        function stop() {
          window.removeEventListener("keydown", handler, true);
          presetHotkeyListeningIdx = -1;
          presetHotkeyStop = null;
          // refresh all
          renderPresetHotkeys();
        }
        presetHotkeyStop = stop;
        const handler = (e) => {
          e.preventDefault();
          e.stopPropagation();
          const spec = formatHotkeyFromEvent(e);
          if (!spec) return;
          const hotkeys = (cfg.preset_hotkeys || []).slice();
          if (idx < hotkeys.length) hotkeys[idx] = { ...hotkeys[idx], key: spec };
          stop();
          queuePatch({ preset_hotkeys: hotkeys });
          toast("Bound " + spec);
        };
        window.addEventListener("keydown", handler, true);
      });
    });
    presetHotkeysEl.querySelectorAll(".phk-clear").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.closest(".phk").dataset.idx, 10);
        const hotkeys = (cfg.preset_hotkeys || []).slice();
        hotkeys.splice(idx, 1);
        queuePatch({ preset_hotkeys: hotkeys });
      });
    });
  }

  function stopPresetHotkeyListen() {
    if (presetHotkeyStop) presetHotkeyStop();
  }

  if ($("btn-add-hotkey")) {
    $("btn-add-hotkey").addEventListener("click", () => {
      const hotkeys = (cfg.preset_hotkeys || []).slice();
      hotkeys.push({ key: "", target: "" });
      queuePatch({ preset_hotkeys: hotkeys });
    });
  }

  /* Override bindForm to also update bg image UI and hotkey UI */
  const origBindForm = bindForm;
  bindForm = function() {
    origBindForm();
    updateBgImageUi();
    renderPresetHotkeys();
  };

  const searchInput = document.getElementById('settings-search');
  const searchClear = document.getElementById('search-clear');

  if (searchInput) {
    searchInput.addEventListener('keyup', function() {
      var q = searchInput.value.trim();
      if (q.length < 2 && q.length > 0) {
        if (searchClear) searchClear.hidden = false;
        return;
      }
      filterSettings(q);
      if (searchClear) searchClear.hidden = q === '';
    });

    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        filterSettings('');
        if (searchClear) searchClear.hidden = true;
        searchInput.blur();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        var visibleSection = document.querySelector('.block.sec:not([hidden])');
        if (visibleSection) {
          var firstField = visibleSection.querySelector('input:not([type="hidden"]):not([hidden]), select:not([hidden]), button:not([hidden])');
          if (firstField) firstField.focus();
        }
      }
    });
  }

  if (searchClear) {
    searchClear.addEventListener('click', function() {
      if (searchInput) {
        searchInput.value = '';
        filterSettings('');
      }
      searchClear.hidden = true;
      searchInput.focus();
    });
  }

  document.addEventListener('keydown', function(e) {
    if (hotkeyListening) return;

    if (e.ctrlKey && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
      if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA')) return;
      e.preventDefault();
      undo();
    } else if (e.ctrlKey && e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
      if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA')) return;
      e.preventDefault();
      redo();
    } else if (e.key === 'Escape') {
      if (searchInput && document.activeElement === searchInput) {
        searchInput.value = '';
        filterSettings('');
        if (searchClear) searchClear.hidden = true;
        searchInput.blur();
      }
    }
  });

  document.addEventListener('keydown', function(e) {
    if (!e.target.classList.contains('val-input')) return;
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      var step = parseFloat(e.target.step) || 1;
      var val = parseFloat(e.target.value);
      if (!Number.isFinite(val)) val = 0;
      e.target.value = val + step;
      e.target.dispatchEvent(new Event('input', { bubbles: true }));
      e.target.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      var step = parseFloat(e.target.step) || 1;
      var val = parseFloat(e.target.value);
      if (!Number.isFinite(val)) val = 0;
      e.target.value = val - step;
      e.target.dispatchEvent(new Event('input', { bubbles: true }));
      e.target.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  let onboardingStep = 0;
  let onboardingSelectedPreset = null;

  const ONBOARDING_PRESETS = [
    { name: "16:9 pad", label: "Standard 16:9", desc: "Widescreen layout" },
    { name: "Square HUD", label: "Square HUD", desc: "Compact, shows stats" },
    { name: "Border only", label: "Border Only", desc: "Minimal, just the pad border" },
    { name: "Corner mini", label: "Corner Mini", desc: "Small, in the corner" },
  ];

  const ONBOARDING_STEPS = [
    {
      title: "Welcome to Velo!",
      desc: "Configure the overlay in a few steps.",
      render: function () {
        var url = overlayUrl();
        return (

          '<p><strong>1. Open OBS and add a Browser Source</strong></p>' +
          '<p><strong>2. Set the URL to:</strong></p>' +
          '<div class="onboarding-url">' + escapeHtml(url) + '</div>' +
          '<p>Recommended size: <strong>' + (cfg.canvas_width || 640) + ' × ' + (cfg.canvas_height || 360) + '</strong></p>' +
          '<p class="onboarding-tip">Turn off "Shutdown source when not visible" in OBS for best results.</p>'
        );
      },
    },
    {
      title: 'Choose Your Colors',
      desc: 'Choose your desired colors.',
      render: function () {
        var trailColor = cfg.trail_color || '#888888';
        var bgColor = cfg.pad_bg_color || '#1a1a1a';
        var cursorColor = cfg.cursor_dot_color || '#ffffff';
        return '<div class="onboarding-step-content">' +
          '<div class="onboarding-color-row">' +
          '<label>Trail Color</label>' +
          '<input type="color" id="onboarding-trail-color" value="' + escapeHtml(trailColor) + '">' +
          '</div>' +
          '<div class="onboarding-color-row">' +
          '<label>Background</label>' +
          '<input type="color" id="onboarding-bg-color" value="' + escapeHtml(bgColor) + '">' +
          '</div>' +
          '<div class="onboarding-color-row">' +
          '<label>Cursor</label>' +
          '<input type="color" id="onboarding-cursor-color" value="' + escapeHtml(cursorColor) + '">' +
          '</div>' +
          '</div>';
      },
    },
    {
      title: "Choose a Starting Preset",
      desc: "Pick a preset that matches your needs. You can customize everything later.",
      render: function () {
        var html = '<div class="onboarding-preset-grid">';
        ONBOARDING_PRESETS.forEach(function (p) {
          var sel = onboardingSelectedPreset === p.name ? " selected" : "";
          var rec = p.name === "16:9 pad" ? '<span class="recommended-badge">Recommended</span>' : "";
          html +=
            '<div class="onboarding-preset-card' + sel + '" data-preset="' + escapeHtml(p.name) + '">' +
            '<h4>' + escapeHtml(p.label) + '</h4>' +
            '<p>' + escapeHtml(p.desc) + '</p>' +
            rec +
            '</div>';
        });
        html += '</div>';
        return html;
      },
    },
    {
      title: "Quick Settings",
      desc: "Adjust a few basic settings to get started.",
      render: function () {
        var sens = cfg.motion_scale != null ? Math.round(cfg.motion_scale * 10) / 10 : 1.0;
        var trailOn = cfg.trail_enabled !== false;
        var clicksOn = cfg.show_clicks !== false;
        var hudOn = cfg.show_stats === true;
        return (
          '<div class="onboarding-quick-settings">' +
          '<div class="onboarding-quick-setting">' +
          '<label>Motion sensitivity</label>' +
          '<input type="range" id="ob-sensitivity" min="0.1" max="3" step="0.1" value="' + sens + '" />' +
          '<span class="onboarding-range-val" id="ob-sensitivity-val">' + sens + '</span>' +
          '</div>' +
          '<div class="onboarding-quick-setting">' +
          '<label>Show trail</label>' +
          '<label class="toggle"><input type="checkbox" id="ob-trail"' + (trailOn ? ' checked' : '') + ' /><span class="track"></span></label>' +
          '</div>' +
          '<div class="onboarding-quick-setting">' +
          '<label>Click effects</label>' +
          '<label class="toggle"><input type="checkbox" id="ob-clicks"' + (clicksOn ? ' checked' : '') + ' /><span class="track"></span></label>' +
          '</div>' +
          '<div class="onboarding-quick-setting">' +
          '<label>Show HUD</label>' +
          '<label class="toggle"><input type="checkbox" id="ob-hud"' + (hudOn ? ' checked' : '') + ' /><span class="track"></span></label>' +
          '</div>' +
          '</div>'
        );
      },
    },
    {
      title: "",
      desc: "",
      render: function () {
        return '<div class="onboarding-done-big">Done</div>';
      },
    },
  ];

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function showOnboarding() {
    onboardingStep = 0;
    onboardingSelectedPreset = null;
    var overlay = $("onboarding-overlay");
    if (overlay) overlay.hidden = false;
    renderOnboardingStep(0);
    bindOnboardingEvents();
  }

  function renderOnboardingStep(step) {
    var content = $("onboarding-content");
    var title = $("onboarding-title");
    var desc = $("onboarding-desc");
    var backBtn = $("onboarding-back");
    var nextBtn = $("onboarding-next");
    var finishBtn = $("onboarding-finish");
    var progressFill = $("onboarding-progress-fill");

    if (!content) return;

    var s = ONBOARDING_STEPS[step];
    if (!s) return;

    if (title) title.textContent = s.title;
    if (desc) desc.textContent = s.desc;

    content.classList.add("fade");
    setTimeout(function () {
      content.innerHTML = s.render();
      content.classList.remove("fade");

      if (step === 2) {
        content.querySelectorAll(".onboarding-preset-card").forEach(function (card) {
          card.addEventListener("click", function () {
            content.querySelectorAll(".onboarding-preset-card").forEach(function (c) {
              c.classList.remove("selected");
            });
            card.classList.add("selected");
            onboardingSelectedPreset = card.getAttribute("data-preset");
          });
        });
      }

      if (step === 3) {
        var sensSlider = $("ob-sensitivity");
        var sensVal = $("ob-sensitivity-val");
        if (sensSlider && sensVal) {
          sensSlider.addEventListener("input", function () {
            sensVal.textContent = parseFloat(sensSlider.value).toFixed(1);
          });
        }
      }
    }, 100);

    if (progressFill) {
      progressFill.style.width = ((step / 4) * 100) + "%";
    }

    if (backBtn) backBtn.hidden = step === 0;
    if (nextBtn) nextBtn.hidden = step === 4;
    if (finishBtn) finishBtn.hidden = step !== 4;
  }

  function nextStep() {
    if (onboardingStep === 1) {
      var trailColor = $("onboarding-trail-color");
      var bgColor = $("onboarding-bg-color");
      var cursorColor = $("onboarding-cursor-color");
      var patch = {};
      if (trailColor) patch.trail_color = trailColor.value;
      if (bgColor) patch.pad_bg_color = bgColor.value;
      if (cursorColor) patch.cursor_dot_color = cursorColor.value;
      if (Object.keys(patch).length) queuePatch(patch);
    }
    if (onboardingStep === 2 && onboardingSelectedPreset) {
      applyPreset(onboardingSelectedPreset, "builtin", { silent: true });
    }
    if (onboardingStep === 3) {
      var sensSlider = $("ob-sensitivity");
      var trailChk = $("ob-trail");
      var clicksChk = $("ob-clicks");
      var hudChk = $("ob-hud");
      var patch = {};
      if (sensSlider) patch.motion_scale = parseFloat(sensSlider.value);
      if (trailChk) patch.trail_enabled = trailChk.checked;
      if (clicksChk) patch.show_clicks = clicksChk.checked;
      if (hudChk) patch.show_stats = hudChk.checked;
      if (Object.keys(patch).length) queuePatch(patch);
    }
    if (onboardingStep < 4) {
      onboardingStep++;
      renderOnboardingStep(onboardingStep);
    }
  }

  function prevStep() {
    if (onboardingStep > 0) {
      onboardingStep--;
      renderOnboardingStep(onboardingStep);
    }
  }

  async function finishOnboarding() {
    var dontShow = $("onboarding-dont-show");
    if (dontShow && dontShow.checked) {
      try {
        await api("/api/onboarding/dismiss", { method: "POST" });
      } catch (_) {}
    }
    var overlay = $("onboarding-overlay");
    if (overlay) overlay.hidden = true;
  }

  function bindOnboardingEvents() {
    var nextBtn = $("onboarding-next");
    var backBtn = $("onboarding-back");
    var skipBtn = $("onboarding-skip");
    var finishBtn = $("onboarding-finish");
    var backdrop = $("onboarding-backdrop");

    if (nextBtn) {
      var newNext = nextBtn.cloneNode(true);
      nextBtn.parentNode.replaceChild(newNext, nextBtn);
      newNext.addEventListener("click", nextStep);
    }
    if (backBtn) {
      var newBack = backBtn.cloneNode(true);
      backBtn.parentNode.replaceChild(newBack, backBtn);
      newBack.addEventListener("click", prevStep);
    }
    if (skipBtn) {
      var newSkip = skipBtn.cloneNode(true);
      skipBtn.parentNode.replaceChild(newSkip, skipBtn);
      newSkip.addEventListener("click", finishOnboarding);
    }
    if (finishBtn) {
      var newFinish = finishBtn.cloneNode(true);
      finishBtn.parentNode.replaceChild(newFinish, finishBtn);
      newFinish.addEventListener("click", finishOnboarding);
    }
    if (backdrop) {
      var newBackdrop = backdrop.cloneNode(true);
      backdrop.parentNode.replaceChild(newBackdrop, backdrop);
      newBackdrop.addEventListener("click", finishOnboarding);
    }
  }

  async function checkOnboarding() {
    try {
      var resp = await api("/api/onboarding");
      var data = await resp.json();
      if (data.show) {
        showOnboarding();
      }
    } catch (_) {}
  }

  Promise.all([loadConfig()])
    .then(() => {
      initInlineRename();
      statusEl.textContent = "Online";
      poll();
      setInterval(poll, 2500);
      checkOnboarding();
    })
    .catch((e) => {
      statusEl.textContent = "Failed to load";
      console.error(e);
    });
