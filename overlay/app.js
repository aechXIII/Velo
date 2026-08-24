  import {
    calculateActualSizeZoom,
    calculateBackgroundImageLayout,
    calculatePositionNudge,
  } from "./background_image_layout.js";
  import { updateBackgroundCropSession } from "./background_crop_session.js";

  const pad = document.getElementById("pad");
  const padBg = document.getElementById("pad-bg");
  const padBgImage = document.createElement("img");
  padBgImage.id = "pad-bg-image";
  padBgImage.className = "pad-bg-image";
  padBgImage.alt = "";
  padBgImage.draggable = false;
  padBgImage.hidden = true;
  padBg.appendChild(padBgImage);
  const cropHint = document.getElementById("crop-hint");
  const padGrid = document.getElementById("pad-grid");
  const padGridPat = document.getElementById("pad-grid-pat");
  const padVignette = document.getElementById("pad-vignette");
  const sourceBg = document.getElementById("source-bg");
  const canvas = document.getElementById("trail");
  const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
  const statsEl = document.getElementById("stats");
  const sSpeed = document.getElementById("s-speed");
  const sPeak = document.getElementById("s-peak");
  const sCps = document.getElementById("s-cps");
  const sClicks = document.getElementById("s-clicks");
  const sDist = document.getElementById("s-dist");
  const sSpeedUnit = document.getElementById("s-speed-unit");
  const sPeakUnit = document.getElementById("s-peak-unit");
  const sDistUnit = document.getElementById("s-dist-unit");
  const sAvgSpeed = document.getElementById("s-avg-speed");
  const sAvgSpeedUnit = document.getElementById("s-avg-speed-unit");

  const qs = new URLSearchParams(location.search);
  const previewLite = qs.get("preview") === "lite";

  let cfg = {
    capture_mode: "relative",
    view_mode: "infinite",
    camera_lag: 0.15,
    view_zoom: 1,
    motion_scale: 1,
    motion_ease: 0.35,
    motion_feel: "normal",
    target_fps: 60,
    render_quality: "balanced",
    trail_enabled: true,
    trail_lifetime_ms: 1100,
    trail_max_points: 120,
    trail_width: 2.4,
    trail_glow: true,
    trail_glow_blur: 6,
    trail_glow_opacity: 1,
    trail_glow_width: 1,
    trail_glow_custom_color: false,
    trail_glow_custom_color_val: "#ffffff",
    trail_min_distance: 1.2,
    trail_smoothing: 0,
    trail_curve: 0.55,
    trail_samples: 2,
    fade_style: "smooth",
    trail_color: "#ffffff",
    speed_min: 40,
    speed_max: 3200,
    speed_colorize: true,
    speed_stops: [
      { t: 0, color: "#ffffff" },
      { t: 0.45, color: "#a0a0a0" },
      { t: 0.75, color: "#ffcc66" },
      { t: 1, color: "#ff4444" },
    ],
    show_cursor_dot: true,
    cursor_dot_size: 4.5,
    cursor_dot_color: "#ffffff",
    cursor_dot_opacity: 0.95,
    show_clicks: true,
    click_lifetime_ms: 280,
    click_radius: 16,
    click_line_width: 1.5,
    click_opacity: 0.85,
    click_expand: true,
    click_style: "ring",
    click_show: {
      left: true,
      right: true,
      middle: true,
      side: true,
    },
    click_colors: {
      left: "#ffffff",
      right: "#cccccc",
      middle: "#888888",
      x1: "#aaaaaa",
      x2: "#aaaaaa",
    },
    pad_enabled: true,
    pad_shape: "rounded",
    pad_width_pct: 100,
    pad_height_pct: 100,
    pad_x_pct: 50,
    pad_y_pct: 50,
    pad_radius: 12,
    pad_bg_enabled: true,
    pad_bg_color: "#0a0a0a",
    pad_bg_opacity: 0.72,
    pad_bg_image: "",
    pad_bg_image_enabled: false,
    pad_bg_image_opacity: 1.0,
    pad_bg_image_size: "cover",
    pad_bg_image_zoom: 1.0,
    pad_blur: false,
    pad_border_enabled: true,
    pad_border_color: "#ffffff",
    pad_border_opacity: 0.12,
    pad_border_width: 1.5,
    pad_shadow: false,
    pad_shadow_opacity: 0.4,
    pad_grid: false,
    pad_grid_size: 40,
    pad_grid_thickness: 1,
    pad_grid_color: "#ffffff",
    pad_grid_opacity: 0.08,
    pad_crosshair: false,
    pad_crosshair_color: "#ffffff",
    pad_crosshair_opacity: 0.14,
    pad_crosshair_size: 14,
    pad_vignette: false,
    pad_vignette_opacity: 0.3,
    pad_clip_trail: true,
    pad_glow_enabled: false,
    pad_glow_color: "#ffffff",
    pad_glow_opacity: 0.5,
    pad_glow_blur: 24,
    source_bg_enabled: false,
    source_bg_color: "#000000",
    source_bg_opacity: 0,
    overlay_opacity: 1,
    show_stats: false,
    stats_opacity: 0.55,
    stats_bg: true,
    stats_bg_color: "#0a0b0f",
    stats_border: true,
    stats_x_pct: 2,
    stats_y_pct: 86,
    stats_show_speed: true,
    stats_show_peak: false,
    stats_show_cps: true,
    stats_show_clicks: true,
    stats_show_distance: true,
    stats_units: "cm",
    stats_dpi: 800,
    hud_show_avg_speed: true,
    hud_show_sparkline: true,
chart_color: "#a677ff",
};

  const CM_PER_INCH = 2.54;

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

  let points = [];
  let clicks = [];
  let wx = 0;
  let wy = 0;
  let tx = 0;
  let ty = 0;
  let swx = 0;
  let swy = 0;
  let camX = 0;
  let camY = 0;
  let camTx = 0;
  let camTy = 0;
  let lastMoveT = performance.now() / 1000;
  let dpr = 1;
  let pw = 0;
  let ph = 0;
  let ws = null;
  let reconnectTimer = null;
  const colorCache = new Map();
  let timeOrigin = null;
  let serverOrigin = null;
  let needsDraw = true;
  let backgroundImageLayout = null;
  let bgCropSession = { requested: false, imageAvailable: false, active: false };
  let bgCropDrag = null;

  let hudDrag = null;
  let shiftHeld = false;

  let speedSamples = 0;
  let accumulatedSpeed = 0;

  let speedHistory = [];
  const SPARKLINE_DURATION = 5;
const SPARKLINE_MAX_POINTS = 100;

  function hexToRgb(hex) {
    if (colorCache.has(hex)) return colorCache.get(hex);
    let h = String(hex || "#ffffff").replace("#", "").trim();
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    if (h.length >= 8) h = h.slice(0, 6);
    // parseInt("#000000") is 0 -- must not use || fallback (that forced white)
    let n = parseInt(h, 16);
    if (!Number.isFinite(n)) n = 0xffffff;
    const rgb = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    colorCache.set(hex, rgb);
    return rgb;
  }
  function rgba(rgb, a) {
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;
  }
  function lerp(a, b, t) {
    return a + (b - a) * t;
  }
  function lerpColor(c1, c2, t) {
    return [
      Math.round(lerp(c1[0], c2[0], t)),
      Math.round(lerp(c1[1], c2[1], t)),
      Math.round(lerp(c1[2], c2[2], t)),
    ];
  }

  function speedToColor(speed) {
    if (cfg.speed_colorize === false) {
      return hexToRgb(cfg.trail_color || cfg.cursor_dot_color || "#ffffff");
    }
    const mn = Number(cfg.speed_min) || 0;
    const mx = Math.max(Number(cfg.speed_max) || 1, mn + 1);
    let t = (speed - mn) / (mx - mn);
    t = Math.max(0, Math.min(1, t));
    t = t * t * (3 - 2 * t);
    const stops = (cfg.speed_stops || []).slice().sort((a, b) => a.t - b.t);
    if (!stops.length) return hexToRgb(cfg.trail_color || "#ffffff");
    if (t <= stops[0].t) return hexToRgb(stops[0].color);
    if (t >= stops[stops.length - 1].t) return hexToRgb(stops[stops.length - 1].color);
    for (let i = 0; i < stops.length - 1; i++) {
      const a = stops[i];
      const b = stops[i + 1];
      if (t >= a.t && t <= b.t) {
        const u = (t - a.t) / Math.max(b.t - a.t, 1e-6);
        return lerpColor(hexToRgb(a.color), hexToRgb(b.color), u);
      }
    }
    return hexToRgb(stops[stops.length - 1].color);
  }

function fadeAlpha(age, life) {
    const u = Math.max(0, Math.min(1, 1 - age / life));
    const style = cfg.fade_style || "smooth";
    if (style === "linear") return u;
    if (style === "hard") return u > 0.1 ? 1 : u / 0.1;
    if (style === "ease-in") return 1 - Math.pow(1 - u, 2);
    if (style === "ease-out") return u * u;
    if (style === "snap") return u < 0.6 ? 1 : 1 - Math.pow((u - 0.6) / 0.4, 2);
    return Math.pow(u, 1.35); // smooth
  }

  function catmull(p0, p1, p2, p3, t) {
    const t2 = t * t;
    const t3 = t2 * t;
    return (
      0.5 *
      (2 * p1 +
        (-p0 + p2) * t +
        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
        (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
    );
  }

  function maxDpr() {
    if (previewLite || cfg.render_quality === "performance") return 1;
    return Math.min(window.devicePixelRatio || 1, 1.5);
  }

  function resizeCanvas() {
    const rect = pad.getBoundingClientRect();
    pw = Math.max(1, rect.width);
    ph = Math.max(1, rect.height);
    dpr = maxDpr();
    canvas.width = Math.floor(pw * dpr);
    canvas.height = Math.floor(ph * dpr);
    canvas.style.width = pw + "px";
    canvas.style.height = ph + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    updateCameraTarget();
    camX = camTx;
    camY = camTy;
  }

  function imageEnabled() {
    return !!(cfg.pad_bg_image_enabled && cfg.pad_bg_image);
  }

  function applyBackgroundImageLayout() {
    if (!imageEnabled()) {
      backgroundImageLayout = null;
      padBgImage.hidden = true;
      return;
    }

    const src = String(cfg.pad_bg_image);
    if (padBgImage.getAttribute("src") !== src) {
      padBgImage.src = src;
    }
    padBgImage.hidden = false;
    padBgImage.style.opacity = String(cfg.pad_bg_image_opacity ?? 1);
    if (!padBgImage.complete || !padBgImage.naturalWidth || !padBgImage.naturalHeight) {
      return;
    }

    const frameWidth = Math.max(1, pad.clientWidth);
    const frameHeight = Math.max(1, pad.clientHeight);
    backgroundImageLayout = calculateBackgroundImageLayout({
      naturalWidth: padBgImage.naturalWidth,
      naturalHeight: padBgImage.naturalHeight,
      frameWidth,
      frameHeight,
      fit: cfg.pad_bg_image_size || "cover",
      zoom: cfg.pad_bg_image_zoom ?? 1,
      positionX: cfg.pad_bg_image_pos_x ?? 50,
      positionY: cfg.pad_bg_image_pos_y ?? 50,
    });
    padBgImage.style.width = backgroundImageLayout.width + "px";
    padBgImage.style.height = backgroundImageLayout.height + "px";
    padBgImage.style.left = backgroundImageLayout.left + "px";
    padBgImage.style.top = backgroundImageLayout.top + "px";
  }

  padBgImage.addEventListener("load", applyBackgroundImageLayout);
  padBgImage.addEventListener("error", () => {
    backgroundImageLayout = null;
    padBgImage.hidden = true;
  });

  function applyPadLayout() {
    if (!cfg.pad_enabled) {
      if (bgCropSession.requested) setBackgroundCropEditing(false);
      pad.style.display = "none";
      return;
    }
    pad.style.display = "block";
    const w = Number(cfg.pad_width_pct) || 100;
    const h = Number(cfg.pad_height_pct) || 100;
    const x = Number(cfg.pad_x_pct) ?? 50;
    const y = Number(cfg.pad_y_pct) ?? 50;
    pad.style.width = w + "%";
    pad.style.height = h + "%";
    pad.style.left = x + "%";
    pad.style.top = y + "%";
    pad.style.transform = "translate(-50%, -50%)";

    const hasImage = imageEnabled();
    updateBackgroundCropImageAvailability(hasImage);
    const shape = cfg.pad_shape || "rounded";
    pad.className = "pad shape-" + shape;
    if (bgCropSession.active) pad.classList.add("crop-editing");
    if (bgCropDrag) pad.classList.add("crop-dragging");
    if (!cfg.pad_bg_enabled) pad.classList.add("no-bg");
    if (!cfg.pad_border_enabled) pad.classList.add("no-border");
    if (!cfg.pad_shadow) pad.classList.add("no-shadow");
    if (cfg.pad_blur) pad.classList.add("frost");

    const radius = Number(cfg.pad_radius) || 12;
    pad.style.setProperty("--pad-radius", radius + "px");

    const br =
      shape === "rect"
        ? "0"
        : shape === "pill"
          ? "999px"
          : shape === "circle"
            ? "50%"
            : shape === "stadium"
              ? ""
              : radius + "px";

    const bw = Math.max(0.5, Number(cfg.pad_border_width) || 1.5);

    const showBg = cfg.pad_bg_enabled || cfg.pad_glow_enabled || hasImage;
    if (cfg.pad_bg_enabled) {
      padBg.style.background = rgba(hexToRgb(cfg.pad_bg_color || "#0a0a0a"), Number(cfg.pad_bg_opacity) ?? 0.72);
    } else if (hasImage) {
      padBg.style.background = "transparent";
    } else {
      padBg.style.background = "transparent";
    }
    padBg.style.backgroundImage = "none";
    padBg.style.opacity = "1";
    padBg.hidden = !showBg;

    padBg.style.border = "none";
    padBg.style.top = "0";
    padBg.style.right = "0";
    padBg.style.bottom = "0";
    padBg.style.left = "0";
    padBg.style.borderRadius = br;
    applyBackgroundImageLayout();

    const shadows = [];

    if (cfg.pad_border_enabled) {
      const bc = rgba(hexToRgb(cfg.pad_border_color || "#ffffff"), Number(cfg.pad_border_opacity) ?? 0.12);
      shadows.push(`inset 0 0 0 ${bw}px ${bc}`);
    }

    if (cfg.pad_glow_enabled) {
      const glowBlur = Number(cfg.pad_glow_blur) || 24;
      const glowColor = cfg.pad_glow_color || "#ffffff";
      const glowOpacity = Number(cfg.pad_glow_opacity) ?? 0.5;
      shadows.push(`inset 0 0 ${glowBlur}px ${rgba(hexToRgb(glowColor), glowOpacity)}`);
    }

    if (cfg.pad_shadow && cfg.pad_bg_enabled) {
      const so = Number(cfg.pad_shadow_opacity) ?? 0.4;
      shadows.push(`0 10px 36px rgba(0,0,0,${so})`);
    }
    padBg.style.boxShadow = shadows.length ? shadows.join(", ") : "none";

    pad.style.borderRadius = br;
    canvas.style.borderRadius = br;

    padGrid.hidden = !cfg.pad_grid;
    if (cfg.pad_grid && padGridPat) {
      const g = Math.max(4, Math.round(Number(cfg.pad_grid_size) || 40));
      const line = Math.max(1, Math.round(Number(cfg.pad_grid_thickness) || 1));
      padGrid.style.borderRadius = br;
      padGridPat.style.color = rgba(hexToRgb(cfg.pad_grid_color), 1);
      padGridPat.style.opacity = String(Number(cfg.pad_grid_opacity) ?? 0.08);
      padGridPat.style.backgroundSize = g + "px " + g + "px";
      padGridPat.style.backgroundImage = [
        "linear-gradient(to right, currentColor " + line + "px, transparent " + line + "px)",
        "linear-gradient(to bottom, currentColor " + line + "px, transparent " + line + "px)",
      ].join(", ");
      lastGridOx = null;
      lastGridOy = null;
    }

    padVignette.hidden = !cfg.pad_vignette;
    if (cfg.pad_vignette) {
      const vo = Number(cfg.pad_vignette_opacity) ?? 0.3;
      padVignette.style.background = `radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,${vo}) 100%)`;
      padVignette.style.borderRadius = br;
    }

    if (cfg.source_bg_enabled && Number(cfg.source_bg_opacity) > 0.001) {
      sourceBg.hidden = false;
      sourceBg.style.background = rgba(
        hexToRgb(cfg.source_bg_color),
        Number(cfg.source_bg_opacity)
      );
    } else {
      sourceBg.hidden = true;
    }

    document.body.style.opacity = String(cfg.overlay_opacity ?? 1);
    resizeCanvas();
    updateGridOffset();
  }

  function applyConfig(next) {
    if (!next || typeof next !== "object") return;
    cfg = { ...cfg, ...next };
    if (cfg.view_mode === "wrap") cfg.view_mode = "infinite";
    if (previewLite) {
      cfg.target_fps = Math.min(Number(cfg.target_fps) || 60, 30);
      cfg.trail_glow = false;
      cfg.trail_samples = 1;
      cfg.trail_curve = Math.min(Number(cfg.trail_curve) || 0, 0.25);
      cfg.trail_max_points = Math.min(Number(cfg.trail_max_points) || 120, 64);
    }
    if (cfg.render_quality === "performance") {
      cfg.trail_samples = Math.min(Number(cfg.trail_samples) || 2, 2);
      cfg.trail_curve = Math.min(Number(cfg.trail_curve) || 0, 0.4);
      cfg.trail_max_points = Math.min(Number(cfg.trail_max_points) || 120, 80);
      cfg.trail_glow = false;
    }
    if (pw > 0 && ph > 0 && viewMode() === "fixed") {
      tx = Math.max(0, Math.min(pw, tx));
      ty = Math.max(0, Math.min(ph, ty));
      wx = Math.max(0, Math.min(pw, wx));
      wy = Math.max(0, Math.min(ph, wy));
      swx = wx;
      swy = wy;
      camX = 0;
      camY = 0;
      camTx = 0;
      camTy = 0;
    }
    colorCache.clear();
    applyPadLayout();
    applyStatsLayout();
    needsDraw = true;
  }

  function truthyFlag(v, defaultOn) {
    if (v === undefined || v === null) return defaultOn;
    if (v === false || v === 0 || v === "0" || v === "false" || v === "off") return false;
    return true;
  }

  function applyStatsLayout() {
    if (!statsEl) return;
    const on = truthyFlag(cfg.show_stats, false);
    statsEl.classList.toggle("hidden", !on);
    if (!on) return;

    statsEl.style.removeProperty("opacity");

    const bg = truthyFlag(cfg.stats_bg, true);
    const border = truthyFlag(cfg.stats_border, true);
    statsEl.classList.toggle("no-bg", !bg);
    statsEl.classList.toggle("no-border", !border);
    statsEl.classList.toggle("bare", !bg && !border);

    if (bg) {
      const backgroundColor = hexToRgb(cfg.stats_bg_color || "#0a0b0f");
      const backgroundOpacity = Math.max(0, Math.min(1, Number(cfg.stats_opacity ?? 0.55)));
      statsEl.style.removeProperty("background");
      statsEl.style.setProperty("background-color", rgba(backgroundColor, backgroundOpacity), "important");
      statsEl.style.removeProperty("backdrop-filter");
      statsEl.style.removeProperty("-webkit-backdrop-filter");
    } else {
      statsEl.style.setProperty("background", "transparent", "important");
      statsEl.style.setProperty("background-color", "transparent", "important");
      statsEl.style.setProperty("backdrop-filter", "none", "important");
      statsEl.style.setProperty("-webkit-backdrop-filter", "none", "important");
    }
    if (border) {
      statsEl.style.removeProperty("border");
      statsEl.style.removeProperty("border-width");
      statsEl.style.removeProperty("border-color");
      statsEl.style.removeProperty("border-style");
    } else {
      statsEl.style.setProperty("border", "none", "important");
      statsEl.style.setProperty("border-width", "0", "important");
      statsEl.style.setProperty("box-shadow", "none", "important");
    }
    if (!bg && !border) {
      statsEl.style.setProperty("padding", "0", "important");
      statsEl.style.setProperty("min-width", "0", "important");
      statsEl.style.setProperty("border-radius", "0", "important");
    } else {
      statsEl.style.removeProperty("padding");
      statsEl.style.removeProperty("min-width");
      statsEl.style.removeProperty("border-radius");
    }

    setStatRow("speed", truthyFlag(cfg.stats_show_speed, true));
    setStatRow("peak", truthyFlag(cfg.stats_show_peak, false));
    setStatRow("avg-speed", truthyFlag(cfg.hud_show_avg_speed, true));
    setStatRow("distance", truthyFlag(cfg.stats_show_distance, true));
    setStatRow("clicks", truthyFlag(cfg.stats_show_clicks, true));
    setStatRow("cps", truthyFlag(cfg.stats_show_cps, true));
    setStatRow("sparkline", truthyFlag(cfg.hud_show_sparkline, true));

    const units = cfg.stats_units || "cm";
    const rateUnit = units === "raw" ? "" : units === "m" ? "m/s" : "cm/s";
    const distUnit = units === "raw" ? "" : units === "m" ? "m" : "cm";
    if (sSpeedUnit) sSpeedUnit.textContent = rateUnit;
    if (sPeakUnit) sPeakUnit.textContent = rateUnit;
    if (sDistUnit) sDistUnit.textContent = distUnit;
    if (sAvgSpeedUnit) sAvgSpeedUnit.textContent = rateUnit;

    placeStatsPanel();
  }

  function statsEdgeInset() {
    const shape = cfg.pad_shape || "rounded";
    const vw = window.innerWidth || 1;
    const vh = window.innerHeight || 1;
    const minSide = Math.min(vw, vh);
    if (shape === "circle") {
      return Math.max(14, Math.round(minSide * 0.14));
    }
    if (shape === "pill") {
      return Math.max(12, Math.round(minSide * 0.1));
    }
    const radius = Math.max(0, Number(cfg.pad_radius) || 0);
    return Math.max(10, Math.round(radius + 8));
  }

  function placeStatsPanel() {
    if (!statsEl || statsEl.classList.contains("hidden")) return;
    const x = Math.max(0, Math.min(100, Number(cfg.stats_x_pct) || 0));
    const y = Math.max(0, Math.min(100, Number(cfg.stats_y_pct) || 0));
    statsEl.style.left = x + "%";
    statsEl.style.top = y + "%";
    statsEl.style.right = "auto";
    statsEl.style.bottom = "auto";
    statsEl.style.transform = "translate(-" + x + "%, -" + y + "%)";

    requestAnimationFrame(() => {
      if (!statsEl || statsEl.classList.contains("hidden")) return;
      const inset = statsEdgeInset();
      const r = statsEl.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      let dx = 0;
      let dy = 0;
      if (r.left < inset) dx = inset - r.left;
      if (r.top < inset) dy = inset - r.top;
      if (r.right > vw - inset) dx = vw - inset - r.right;
      if (r.bottom > vh - inset) dy = vh - inset - r.bottom;
      if (dx || dy) {
        statsEl.style.transform =
          "translate(calc(-" + x + "% + " + dx + "px), calc(-" + y + "% + " + dy + "px))";
      }
    });
  }

  function setStatRow(name, visible) {
    const row = statsEl.querySelector(`[data-stat="${name}"]`);
    if (row) row.hidden = !visible;
  }

  function drawSparkline() {
    const canvas = document.getElementById("s-sparkline");
    if (!canvas || !cfg.show_stats || !cfg.hud_show_sparkline || speedHistory.length < 2) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    const values = speedHistory.map((p) => convertCounts(p.speed));
    const max = Math.max(...values, 1);
    const min = 0;
    const range = max - min || 1;

    ctx.beginPath();
    const chartColor = cfg.chart_color || "#a677ff";
    const chartRgb = hexToRgb(chartColor);
    ctx.strokeStyle = rgba(chartRgb, 0.7);
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const padding = 2;
    const drawW = w - padding * 2;
    const drawH = h - padding * 2;

    for (let i = 0; i < values.length; i++) {
      const x = padding + (i / (values.length - 1)) * drawW;
      const y = padding + drawH - ((values[i] - min) / range) * drawH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    const lastX = padding + drawW;
    const lastY = padding + drawH - ((values[values.length - 1] - min) / range) * drawH;
    ctx.lineTo(lastX, padding + drawH);
    ctx.lineTo(padding, padding + drawH);
    ctx.closePath();
    ctx.fillStyle = rgba(chartRgb, 0.08);
    ctx.fill();
  }

  function mouseDpi() {
    const dpi = Number(cfg.stats_dpi);
    return Number.isFinite(dpi) && dpi > 0 ? dpi : 800;
  }

  function convertCounts(counts) {
    const n = Number(counts) || 0;
    const units = cfg.stats_units || "cm";
    if (units === "raw") return n;
    const cm = (n / mouseDpi()) * CM_PER_INCH;
    if (units === "m") return cm / 100;
    return cm;
  }

  function recordSpeedSample(speed) {
    const now = performance.now() / 1000;
    speedHistory.push({ t: now, speed });
    if (speedHistory.length > SPARKLINE_MAX_POINTS) {
      speedHistory.shift();
    }
    const cutoff = now - SPARKLINE_DURATION;
    while (speedHistory.length > 0 && speedHistory[0].t < cutoff) {
      speedHistory.shift();
    }
  }

  function formatStat(value, isRate) {
    const units = cfg.stats_units || "cm";
    const n = Number(value) || 0;
    if (units === "raw") return String(Math.round(n));
    if (units === "m") {
      if (isRate) return n < 0.01 ? n.toFixed(3) : n.toFixed(2);
      return n < 10 ? n.toFixed(2) : n.toFixed(1);
    }
    if (isRate) return n < 10 ? n.toFixed(1) : String(Math.round(n));
    return n < 1000 ? n.toFixed(1) : String(Math.round(n));
  }

  function viewMode() {
    const m = cfg.view_mode === "wrap" ? "infinite" : cfg.view_mode;
    if (m === "fixed") return "fixed";
    return "infinite";
  }

  function isPanView() {
    return viewMode() === "infinite";
  }

  function viewZoom() {
    const z = Number(cfg.view_zoom);
    if (!Number.isFinite(z) || z <= 0) return 1;
    return Math.max(0.25, Math.min(1.5, z));
  }

  function updateCameraTarget() {
    if (!isPanView()) {
      camTx = 0;
      camTy = 0;
      return;
    }
    const z = viewZoom();
    const viewW = pw / z;
    const viewH = ph / z;
    camTx = wx - viewW / 2;
    camTy = wy - viewH / 2;
  }

  let lastGridOx = null;
  let lastGridOy = null;

  function updateGridOffset() {
    if (!cfg.pad_grid || !padGridPat) return;
    const g = Math.max(4, Math.round(Number(cfg.pad_grid_size) || 40));
    const z = isPanView() ? viewZoom() : 1;
    let ox = (((-camX * z) % g) + g) % g;
    let oy = (((-camY * z) % g) + g) % g;
    ox = Math.round(ox);
    oy = Math.round(oy);
    if (ox === lastGridOx && oy === lastGridOy) return;
    lastGridOx = ox;
    lastGridOy = oy;
    padGridPat.style.transform = "translate3d(" + ox + "px," + oy + "px,0)";
  }

  function pushPoint(x, y, t, speed) {
    const minD = Number(cfg.trail_min_distance) || 0.8;
    if (points.length) {
      const last = points[points.length - 1];
      const ddx = x - last.x;
      const ddy = y - last.y;
      if (ddx * ddx + ddy * ddy < minD * minD) {
        last.t = t;
        last.speed = Math.max(last.speed, speed);
        last.x = x;
        last.y = y;
        return;
      }
    }
    points.push({ x, y, t, speed });
    const maxP = Number(cfg.trail_max_points) || 120;
    if (points.length > maxP) points.splice(0, points.length - maxP);
  }

  const MOTION_SCALE_MIN = 0.01;
  const MOTION_SCALE_MAX = 3;

  function motionScale() {
    const s = Number(cfg.motion_scale);
    if (!Number.isFinite(s) || s <= 0) return 1;
    return Math.max(MOTION_SCALE_MIN, Math.min(MOTION_SCALE_MAX, s));
  }

  function padMotionGain() {
    const areaScale = Math.sqrt((Math.max(1, pw) * Math.max(1, ph)) / (300 * 200));
    return 0.05 * motionScale() * areaScale;
  }

  function applyMotionDelta(mdx, mdy, t, dt) {
    const mode = viewMode();
    const speed = Math.hypot(mdx, mdy) / Math.max(dt, 1e-4);
    tx += mdx;
    ty += mdy;

    speedSamples++;
    accumulatedSpeed += speed;

    if (mode === "fixed") {
      tx = Math.max(0, Math.min(pw, tx));
      ty = Math.max(0, Math.min(ph, ty));
    }

    const ease = Math.max(0, Math.min(0.95, Number(cfg.motion_ease) || 0));
    if (ease <= 0.01) {
      wx = tx;
      wy = ty;
      lastMoveT = t;
      smoothAndRecord(t, speed);
    } else {
      lastMoveT = t;
      applyMotionDelta._lastSpeed = speed;
    }
  }

  function handleMouse(msg) {
    const t = typeof msg.t === "number" ? msg.t : performance.now() / 1000;
    const dx = Number(msg.dx) || 0;
    const dy = Number(msg.dy) || 0;
    const mode = cfg.capture_mode || "relative";
    const vmode = viewMode();
    const gain = padMotionGain();

    if (mode === "absolute" && msg.x != null && msg.y != null) {
      const sw = window.screen.width || window.innerWidth;
      const sh = window.screen.height || window.innerHeight;
      const nx = (msg.x / sw) * pw;
      const ny = (msg.y / sh) * ph;
      const dt = Math.max(t - lastMoveT, 1e-4);
      if (vmode === "infinite") {
        if (handleMouse._lx != null) {
          const mdx = (msg.x - handleMouse._lx) * gain;
          const mdy = (msg.y - handleMouse._ly) * gain;
          applyMotionDelta(mdx, mdy, t, dt);
        }
        handleMouse._lx = msg.x;
        handleMouse._ly = msg.y;
      } else {
        tx = Math.max(0, Math.min(pw, nx));
        ty = Math.max(0, Math.min(ph, ny));
        wx = tx;
        wy = ty;
        lastMoveT = t;
        if (cfg.trail_enabled) pushPoint(wx, wy, t, 0);
      }
      lastMoveT = t;
    } else if (dx !== 0 || dy !== 0) {
      const dt = Math.max(t - lastMoveT, 1e-4);
      const mdx = dx * gain;
      const mdy = dy * gain;
      applyMotionDelta(mdx, mdy, t, dt);
    }

    if (msg.btn && String(msg.btn).endsWith("_down") && cfg.show_clicks) {
      const button = String(msg.btn).replace(/_down$/, "");
      const btnIdx = button === "left" ? 0 : button === "right" ? 1 : button === "middle" ? 2 : 3;
      if (isClickButtonShown(button)) {
        const colors = cfg.click_colors || {};
        const color =
          button === "x1" || button === "x2"
            ? colors.x1 || colors.x2 || "#aaaaaa"
            : colors[button] || "#ffffff";
        clicks.push({ t, color });
        needsDraw = true;
      }
    }

    updateCameraTarget();
    needsDraw = true;
  }

  function smoothAndRecord(t, speed) {
    const sm = Math.max(0, Math.min(0.92, Number(cfg.trail_smoothing) || 0));
    if (sm <= 0.01 || !points.length) {
      swx = wx;
      swy = wy;
    } else {
      const k = 1 - sm;
      swx += (wx - swx) * Math.max(0.08, k);
      swy += (wy - swy) * Math.max(0.08, k);
    }
    if (cfg.trail_enabled) pushPoint(swx, swy, t, speed);
  }

  function stepMotionEase(dt) {
    const ease = Math.max(0, Math.min(0.95, Number(cfg.motion_ease) || 0));
    if (ease <= 0.01) {
      wx = tx;
      wy = ty;
      return;
    }
    const prevX = wx;
    const prevY = wy;
    const rate = 1 - Math.pow(ease, Math.max(dt, 1e-4) * 48);
    const k = Math.max(0.02, Math.min(1, rate));
    wx += (tx - wx) * k;
    wy += (ty - wy) * k;
    const moved = Math.hypot(wx - prevX, wy - prevY);
    if (cfg.trail_enabled && moved > 0.12) {
      const catchSpeed = moved / Math.max(dt, 1e-4);
      const inputSpeed = applyMotionDelta._lastSpeed || catchSpeed;
      const speed = inputSpeed * 0.65 + catchSpeed * 0.35;
      smoothAndRecord(performance.now() / 1000, speed);
    }
  }

  function worldToScreen(x, y) {
    if (!isPanView()) return { x, y };
    const z = viewZoom();
    return { x: (x - camX) * z, y: (y - camY) * z };
  }

  function offscreen(a, b) {
    return (
      (a.x < -40 && b.x < -40) ||
      (a.x > pw + 40 && b.x > pw + 40) ||
      (a.y < -40 && b.y < -40) ||
      (a.y > ph + 40 && b.y > ph + 40)
    );
  }

  function pruneFx(now) {
    const life = (Number(cfg.trail_lifetime_ms) || 750) / 1000;
    const clickLife = (Number(cfg.click_lifetime_ms) || 280) / 1000;
    let changed = false;
    while (points.length && points[0].t < now - life) {
      points.shift();
      changed = true;
    }
    while (clicks.length && clicks[0].t < now - clickLife) {
      clicks.shift();
      changed = true;
    }
    return changed;
  }

  function isAnimating(now) {
    if (points.length > 0) return true;
    if (clicks.length > 0) return true;
    if (Math.hypot(tx - wx, ty - wy) > 0.08) return true;
    if (isPanView()) {
      const lag = Math.max(0, Math.min(0.95, Number(cfg.camera_lag) || 0));
      if (lag > 0.001 && Math.hypot(camTx - camX, camTy - camY) > 0.08) return true;
    }
    return false;
  }

  function buildTrailPath() {
    const curve = Math.max(0, Math.min(1, Number(cfg.trail_curve) ?? 0.55));
    const samples = Math.max(1, Math.round(Number(cfg.trail_samples) || 2));
    const screen = points.map((p) => {
      const s = worldToScreen(p.x, p.y);
      return { x: s.x, y: s.y, t: p.t, speed: p.speed };
    });
    if (!(curve > 0.05 && samples > 1 && screen.length >= 2)) return screen;

    const path = [];
    const maxInterpolated = 2000;
    for (let i = 0; i < screen.length - 1; i++) {
      const p0 = screen[Math.max(0, i - 1)];
      const p1 = screen[i];
      const p2 = screen[i + 1];
      const p3 = screen[Math.min(screen.length - 1, i + 2)];
      const segs = Math.max(1, Math.round(samples * curve));
      for (let s = 0; s < segs; s++) {
        if (path.length >= maxInterpolated) break;
        const u = s / segs;
        const cx = catmull(p0.x, p1.x, p2.x, p3.x, u);
        const cy = catmull(p0.y, p1.y, p2.y, p3.y, u);
        const lx = lerp(p1.x, p2.x, u);
        const ly = lerp(p1.y, p2.y, u);
        path.push({
          x: lerp(lx, cx, curve),
          y: lerp(ly, cy, curve),
          t: lerp(p1.t, p2.t, u),
          speed: lerp(p1.speed, p2.speed, u),
        });
      }
      if (path.length >= maxInterpolated) break;
    }
    path.push(screen[screen.length - 1]);
    return path;
  }

  function drawTrail(now) {
    if (!cfg.trail_enabled || points.length < 2) return;

    const life = (Number(cfg.trail_lifetime_ms) || 750) / 1000;
    const width = Number(cfg.trail_width) || 2.4;
    const glow = !!cfg.trail_glow;
    const glowBlur = Number(cfg.trail_glow_blur) || 6;
    const path = buildTrailPath();
    if (path.length < 2) return;

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Build a gradient from the given points (samples up to maxStops stops for performance).
    // When fullBrightAtEnd is true the final stop always has alpha=1 so the leading
    // edge of a chunk never fades below full brightness.
    function makePathGradient(pts, maxStops, fullBrightAtEnd) {
      const g = ctx.createLinearGradient(pts[0].x, pts[0].y, pts[pts.length - 1].x, pts[pts.length - 1].y);
      const s = Math.min(maxStops, pts.length);
      for (let i = 0; i < s; i++) {
        const p = pts[Math.floor(i * (pts.length - 1) / Math.max(s - 1, 1))];
        const fa = (fullBrightAtEnd && i === s - 1) ? 1 : fadeAlpha(now - p.t, life);
        g.addColorStop(i / Math.max(s - 1, 1), rgba(speedToColor(p.speed), fa));
      }
      return g;
    }

    // Draw a continuous path with offscreen splitting
    function strokePath(pts) {
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      let active = true;
      for (let i = 1; i < pts.length; i++) {
        if (offscreen(pts[i - 1], pts[i])) {
          if (active) ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          active = false;
        } else {
          ctx.lineTo(pts[i].x, pts[i].y);
          active = true;
        }
      }
      if (active) ctx.stroke();
    }

    // Glow pass
    if (glow && glowBlur > 0) {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.shadowBlur = glowBlur;
      if (cfg.trail_glow_custom_color) {
        const c = hexToRgb(cfg.trail_glow_custom_color_val || "#ffffff");
        const glowOpacity = Math.max(0, Math.min(1, Number(cfg.trail_glow_opacity) || 1));
        ctx.shadowColor = rgba(c, glowOpacity * 0.45);
      } else {
        ctx.shadowColor = "rgba(255,255,255,0.35)";
      }
      const widthFactor = Math.max(0.5, Math.min(3, Number(cfg.trail_glow_width) || 1));
      ctx.lineWidth = width * 2.5 * widthFactor;
      ctx.globalAlpha = 0.5;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = makePathGradient(path, 48);
      strokePath(path);
      ctx.restore();
    }

    // Core pass: per-chunk gradients
    ctx.shadowBlur = 0;
    ctx.lineWidth = width * 1.2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const CHUNK_SIZE = 12;
    for (let ci = 0; ci < path.length - 1; ci += CHUNK_SIZE) {
      const end = Math.min(ci + CHUNK_SIZE + 1, path.length);
      const chunk = path.slice(ci, end);
      ctx.strokeStyle = makePathGradient(chunk, 12, end >= path.length);
      strokePath(chunk);
    }
  }

  function isClickButtonShown(button) {
    const show = cfg.click_show || {};
    if (button === "x1" || button === "x2") return show.side !== false;
    return show[button] !== false;
  }

  function drawClicks(now) {
    if (!cfg.show_clicks || !clicks.length) return;
    const life = (Number(cfg.click_lifetime_ms) || 280) / 1000;
    const baseR = Number(cfg.click_radius) || 16;
    const lw = Number(cfg.click_line_width) || 1.5;
    const baseA = Number(cfg.click_opacity);
    const maxA = Number.isFinite(baseA) ? baseA : 0.85;
    const expand = cfg.click_expand !== false;
    const style = cfg.click_style || "ring";
    const s = worldToScreen(wx, wy);

    for (const c of clicks) {
      const u = (now - c.t) / life;
      if (u < 0 || u > 1) continue;
      const fade = (1 - u) * (1 - u);
      const alpha = fade * maxA;
      const r = expand
        ? baseR * (0.25 + u * 0.75)
        : baseR * (1 - u * 0.7);
      const rgb = hexToRgb(c.color);

      if (style === "fill") {
        ctx.beginPath();
        ctx.arc(s.x, s.y, Math.max(0.5, r), 0, Math.PI * 2);
        ctx.fillStyle = rgba(rgb, alpha * 0.45);
        ctx.fill();
        ctx.strokeStyle = rgba(rgb, alpha);
        ctx.lineWidth = lw;
        ctx.stroke();
      } else if (style === "double") {
        ctx.strokeStyle = rgba(rgb, alpha);
        ctx.lineWidth = lw;
        ctx.beginPath();
        ctx.arc(s.x, s.y, Math.max(0.5, r), 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(s.x, s.y, Math.max(0.5, r * 0.55), 0, Math.PI * 2);
        ctx.stroke();
      } else if (style === "cross") {
        const arm = Math.max(2, r);
        ctx.strokeStyle = rgba(rgb, alpha);
        ctx.lineWidth = lw;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(s.x - arm, s.y);
        ctx.lineTo(s.x + arm, s.y);
        ctx.moveTo(s.x, s.y - arm);
        ctx.lineTo(s.x, s.y + arm);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(s.x, s.y, Math.max(0.5, r), 0, Math.PI * 2);
        ctx.strokeStyle = rgba(rgb, alpha);
        ctx.lineWidth = lw;
        ctx.stroke();
      }
    }
  }

  function drawCursor() {
    if (!cfg.show_cursor_dot) return;
    const s = worldToScreen(wx, wy);
    const size = Math.max(1.5, Number(cfg.cursor_dot_size) || 4.5);
    const rgb = hexToRgb(cfg.cursor_dot_color || "#ffffff");
    const a = Number(cfg.cursor_dot_opacity);
    const alpha = Number.isFinite(a) ? a : 0.95;
    ctx.beginPath();
    ctx.arc(s.x, s.y, size, 0, Math.PI * 2);
    ctx.fillStyle = rgba(rgb, alpha);
    ctx.fill();
  }

  let lastFrame = performance.now();
  let lastDraw = 0;
  let fpsTick = performance.now();
  let fpsCount = 0;
  let fpsDisplay = 0;
  let fpsEl = null;
  function frame(ts) {
    requestAnimationFrame(frame);
    const fps = Number(cfg.target_fps);
    if (fps > 0) {
      const minDelta = 1000 / Math.min(240, Math.max(15, fps));
      if (ts - lastDraw < minDelta - 0.5) return;
    }

    try {
      const now = ts / 1000;
      if (pruneFx(now)) needsDraw = true;

      if (!needsDraw && !isAnimating(now)) {
        lastFrame = ts;
        return;
      }

      lastDraw = ts;
      const dt = Math.min(0.05, (ts - lastFrame) / 1000);
      lastFrame = ts;

      stepMotionEase(dt);

      if (isPanView()) {
        updateCameraTarget();
        const lag = Math.max(0, Math.min(0.95, Number(cfg.camera_lag) || 0));
        if (lag <= 0.001) {
          camX = camTx;
          camY = camTy;
        } else {
          const k = 1 - Math.pow(lag, dt * 55);
          camX += (camTx - camX) * k;
          camY += (camTy - camY) * k;
        }
        updateGridOffset();
      } else {
        camX = 0;
        camY = 0;
      }

      ctx.clearRect(0, 0, pw, ph);
      drawTrail(now);
      drawClicks(now);
      drawCursor();
      drawSparkline();

      needsDraw = isAnimating(now);
    } catch (e) {
      console.error("Render error:", e);
    }

    fpsCount++;
    if (ts - fpsTick >= 1000) {
      fpsDisplay = fpsCount;
      fpsCount = 0;
      fpsTick = ts;
    }
    if (fpsEl) {
      fpsEl.textContent = fpsDisplay + " fps";
    }
  }

  function qsToken() {
    return new URL(window.location.href).searchParams.get("token") || "";
  }
  function normalizeTime(msg) {
    const out = { ...msg };
    if (typeof msg.t === "number") {
      if (serverOrigin == null) {
        serverOrigin = msg.t;
        timeOrigin = performance.now() / 1000;
      }
      out.t = timeOrigin + (msg.t - serverOrigin);
    } else out.t = performance.now() / 1000;
    return out;
  }
  function updateStats(data) {
    if (!cfg.show_stats) return;
    if (cfg.stats_show_speed !== false && sSpeed) {
      sSpeed.textContent = formatStat(convertCounts(data.speed || 0), true);
    }
    if (cfg.stats_show_peak && sPeak) {
      sPeak.textContent = formatStat(convertCounts(data.peak_speed || 0), true);
    }
    if (cfg.stats_show_distance !== false && sDist) {
      sDist.textContent = formatStat(convertCounts(data.distance || 0), false);
    }
    if (cfg.stats_show_clicks !== false && sClicks) {
      sClicks.textContent = String(Math.round(data.clicks || 0));
    }
    if (cfg.stats_show_cps !== false && sCps) {
      sCps.textContent = (data.cps || 0).toFixed(1);
    }
    if (cfg.hud_show_avg_speed !== false && sAvgSpeed) {
      const avgSpeed = speedSamples > 0 ? (accumulatedSpeed / speedSamples) : 0;
      sAvgSpeed.textContent = formatStat(convertCounts(avgSpeed), true);
    }
    if (cfg.hud_show_sparkline !== false) {
      recordSpeedSample(data.speed || 0);
      drawSparkline();
    }
  }

  function connect() {
    const token = qsToken();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const q = token ? `?token=${encodeURIComponent(token)}` : "";
    if (ws) try { ws.close(); } catch (_) {}
    ws = new WebSocket(`${proto}://${location.host}/ws${q}`);
    // Server sends periodic pings to detect dropped connections;
    // the browser's WebSocket implementation handles pong responses automatically.
    ws.onopen = () => {};
    ws.onclose = () => {
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 900);
    };
    ws.onerror = () => {};
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (_) { return; }
      if (msg.type === "hello" || msg.type === "config") {
        applyConfig(msg.data || {});
      } else if (msg.type === "mouse") {
        handleMouse(normalizeTime(msg));
      } else if (msg.type === "stats") {
        updateStats(msg.data || {});
      }
    };
  }

  window.addEventListener("keydown", (e) => {
    if (e.key === "Shift") {
      shiftHeld = true;
      if (cfg.show_stats) statsEl.classList.add("draggable");
    }
  });
  window.addEventListener("keyup", (e) => {
    if (e.key === "Shift") {
      shiftHeld = false;
      statsEl.classList.remove("draggable");
    }
  });
  window.addEventListener("blur", () => {
    shiftHeld = false;
    statsEl.classList.remove("draggable");
    if (hudDrag) finishHudDrag();
  });

  statsEl.addEventListener("mousedown", (e) => {
    if (!shiftHeld || e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    hudDrag = {
      startX: e.clientX,
      startY: e.clientY,
      startLeft: statsEl.offsetLeft,
      startTop: statsEl.offsetTop,
    };
    statsEl.classList.add("dragging");
    statsEl.setPointerCapture(e.pointerId || 1);
  });

  window.addEventListener("mousemove", (e) => {
    if (!hudDrag) return;
    const dx = e.clientX - hudDrag.startX;
    const dy = e.clientY - hudDrag.startY;
    const newLeft = hudDrag.startLeft + dx;
    const newTop = hudDrag.startTop + dy;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const xPct = Math.max(0, Math.min(100, (newLeft / vw) * 100));
    const yPct = Math.max(0, Math.min(100, (newTop / vh) * 100));
    statsEl.style.left = xPct + "%";
    statsEl.style.top = yPct + "%";
    statsEl.style.transform = "translate(-" + xPct + "%, -" + yPct + "%)";
    statsEl.style.right = "auto";
    statsEl.style.bottom = "auto";
  });

  window.addEventListener("mouseup", () => {
    if (!hudDrag) return;
    finishHudDrag();
  });

  function finishHudDrag() {
    if (!hudDrag) return;
    const rect = statsEl.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const xPct = Math.round(((rect.left + rect.width / 2) / vw) * 100 * 2) / 2;
    const yPct = Math.round(((rect.top + rect.height / 2) / vh) * 100 * 2) / 2;
    cfg.stats_x_pct = Math.max(0, Math.min(100, xPct));
    cfg.stats_y_pct = Math.max(0, Math.min(100, yPct));
    statsEl.classList.remove("dragging");
    hudDrag = null;
    placeStatsPanel();
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({
          type: "config",
          data: {
            stats_x_pct: cfg.stats_x_pct,
            stats_y_pct: cfg.stats_y_pct,
          },
        }));
      } catch (_) {}
    }
  }

  function clampCropValue(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function emitBackgroundCropPatch(patch) {
    Object.assign(cfg, patch);
    applyPadLayout();
    if (window.parent !== window) {
      window.parent.postMessage({ type: "velo-bg-crop", data: patch }, location.origin);
    }
  }

  function syncBackgroundCropEditingUi() {
    const active = bgCropSession.active;
    bgCropDrag = null;
    pad.classList.toggle("crop-editing", active);
    pad.classList.remove("crop-dragging");
    cropHint.hidden = !active;
    if (active) {
      pad.tabIndex = 0;
      pad.focus({ preventScroll: true });
    } else {
      pad.removeAttribute("tabindex");
    }
  }

  function setBackgroundCropEditing(enabled) {
    bgCropSession = updateBackgroundCropSession(bgCropSession, {
      type: "request",
      enabled,
    });
    syncBackgroundCropEditingUi();
  }

  function updateBackgroundCropImageAvailability(available) {
    const wasActive = bgCropSession.active;
    bgCropSession = updateBackgroundCropSession(bgCropSession, {
      type: "image",
      available,
    });
    if (bgCropSession.active !== wasActive) syncBackgroundCropEditingUi();
  }

  function runBackgroundCropCommand(command) {
    if (command === "fit") {
      emitBackgroundCropPatch({
        pad_bg_image_size: "contain",
        pad_bg_image_zoom: 1,
        pad_bg_image_pos_x: 50,
        pad_bg_image_pos_y: 50,
      });
      return;
    }
    if (command === "fill") {
      emitBackgroundCropPatch({
        pad_bg_image_size: "cover",
        pad_bg_image_zoom: 1,
        pad_bg_image_pos_x: 50,
        pad_bg_image_pos_y: 50,
      });
      return;
    }
    if (command === "center") {
      emitBackgroundCropPatch({ pad_bg_image_pos_x: 50, pad_bg_image_pos_y: 50 });
      return;
    }
    if (command === "actual" && padBgImage.naturalWidth && padBgImage.naturalHeight) {
      const zoom = calculateActualSizeZoom({
        naturalWidth: padBgImage.naturalWidth,
        naturalHeight: padBgImage.naturalHeight,
        frameWidth: Math.max(1, pad.clientWidth),
        frameHeight: Math.max(1, pad.clientHeight),
        fit: "cover",
      });
      emitBackgroundCropPatch({
        pad_bg_image_size: "cover",
        pad_bg_image_zoom: Math.round(clampCropValue(zoom, 0.1, 8) * 1000) / 1000,
      });
    }
  }

  pad.addEventListener("pointerdown", (event) => {
    if (!bgCropSession.active || event.button !== 0 || !backgroundImageLayout) return;
    event.preventDefault();
    pad.focus({ preventScroll: true });
    bgCropDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPositionX: Number(cfg.pad_bg_image_pos_x ?? 50),
      startPositionY: Number(cfg.pad_bg_image_pos_y ?? 50),
      rangeX: pad.clientWidth - backgroundImageLayout.width,
      rangeY: pad.clientHeight - backgroundImageLayout.height,
    };
    pad.classList.add("crop-dragging");
    pad.setPointerCapture(event.pointerId);
  });

  pad.addEventListener("pointermove", (event) => {
    if (!bgCropDrag || event.pointerId !== bgCropDrag.pointerId) return;
    const patch = {};
    if (Math.abs(bgCropDrag.rangeX) > 0.5) {
      patch.pad_bg_image_pos_x = Math.round(
        clampCropValue(
          bgCropDrag.startPositionX + ((event.clientX - bgCropDrag.startX) / bgCropDrag.rangeX) * 100,
          0,
          100,
        ) * 100,
      ) / 100;
    }
    if (Math.abs(bgCropDrag.rangeY) > 0.5) {
      patch.pad_bg_image_pos_y = Math.round(
        clampCropValue(
          bgCropDrag.startPositionY + ((event.clientY - bgCropDrag.startY) / bgCropDrag.rangeY) * 100,
          0,
          100,
        ) * 100,
      ) / 100;
    }
    if (Object.keys(patch).length) emitBackgroundCropPatch(patch);
  });

  function finishBackgroundCropDrag(event) {
    if (!bgCropDrag || (event && event.pointerId !== bgCropDrag.pointerId)) return;
    try { pad.releasePointerCapture(bgCropDrag.pointerId); } catch (_) {}
    bgCropDrag = null;
    pad.classList.remove("crop-dragging");
  }

  pad.addEventListener("pointerup", finishBackgroundCropDrag);
  pad.addEventListener("pointercancel", finishBackgroundCropDrag);
  pad.addEventListener("wheel", (event) => {
    if (!bgCropSession.active) return;
    event.preventDefault();
    const current = Number(cfg.pad_bg_image_zoom ?? 1);
    const next = clampCropValue(current * Math.exp(-event.deltaY * 0.0015), 0.1, 8);
    emitBackgroundCropPatch({ pad_bg_image_zoom: Math.round(next * 1000) / 1000 });
  }, { passive: false });

  pad.addEventListener("keydown", (event) => {
    if (!bgCropSession.active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setBackgroundCropEditing(false);
      if (window.parent !== window) {
        window.parent.postMessage({ type: "velo-bg-editor-close" }, location.origin);
      }
      return;
    }
    const step = event.shiftKey ? 5 : 1;
    const patch = {};
    if (event.key === "ArrowLeft") patch.pad_bg_image_pos_x = calculatePositionNudge(cfg.pad_bg_image_pos_x ?? 50, pad.clientWidth, backgroundImageLayout?.width, -1, step);
    if (event.key === "ArrowRight") patch.pad_bg_image_pos_x = calculatePositionNudge(cfg.pad_bg_image_pos_x ?? 50, pad.clientWidth, backgroundImageLayout?.width, 1, step);
    if (event.key === "ArrowUp") patch.pad_bg_image_pos_y = calculatePositionNudge(cfg.pad_bg_image_pos_y ?? 50, pad.clientHeight, backgroundImageLayout?.height, -1, step);
    if (event.key === "ArrowDown") patch.pad_bg_image_pos_y = calculatePositionNudge(cfg.pad_bg_image_pos_y ?? 50, pad.clientHeight, backgroundImageLayout?.height, 1, step);
    if (!Object.keys(patch).length) return;
    event.preventDefault();
    emitBackgroundCropPatch(patch);
  });

  window.addEventListener("resize", () => {
    applyPadLayout();
    placeStatsPanel();
    needsDraw = true;
  });
  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => {
      resizeCanvas();
      applyBackgroundImageLayout();
      needsDraw = true;
    }).observe(pad);
  }

  applyConfig(cfg);
  if (qs.get("debug") === "1") {
    fpsEl = document.createElement("div");
    fpsEl.id = "debug-fps";
    fpsEl.style.cssText =
      "position:fixed;bottom:4px;right:8px;color:#0f0;font:10px monospace;" +
      "background:rgba(0,0,0,0.6);padding:2px 6px;border-radius:3px;pointer-events:none;z-index:999";
    document.body.appendChild(fpsEl);
  }
  connect();
  requestAnimationFrame(frame);

  window.addEventListener("message", (e) => {
    if (!e.data || (window.parent !== window && e.source !== window.parent)) return;
    try {
      if (e.data.type === "velo-bg-editor") {
        setBackgroundCropEditing(e.data.enabled);
        return;
      }
      if (e.data.type === "velo-bg-command") {
        runBackgroundCropCommand(e.data.command);
        return;
      }
      if (e.data.type !== "velo-patch") return;
      const patch = e.data.data;
      if (!patch || typeof patch !== "object") return;
      Object.assign(cfg, patch);
      applyConfig(cfg);
    } catch (_) {}
  });

