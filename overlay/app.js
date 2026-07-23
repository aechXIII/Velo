  const pad = document.getElementById("pad");
  const padBg = document.getElementById("pad-bg");
  const padGrid = document.getElementById("pad-grid");
  const padGridPat = document.getElementById("pad-grid-pat");
  const padVignette = document.getElementById("pad-vignette");
  const padCrosshair = document.getElementById("pad-crosshair");
  const sourceBg = document.getElementById("source-bg");
  const canvas = document.getElementById("trail");
  const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
  const statsEl = document.getElementById("stats");
  const statusEl = document.getElementById("status");
  const sSpeed = document.getElementById("s-speed");
  const sPeak = document.getElementById("s-peak");
  const sCps = document.getElementById("s-cps");
  const sClicks = document.getElementById("s-clicks");
  const sDist = document.getElementById("s-dist");
  const sSpeedUnit = document.getElementById("s-speed-unit");
  const sPeakUnit = document.getElementById("s-peak-unit");
  const sDistUnit = document.getElementById("s-dist-unit");

  const qs = new URLSearchParams(location.search);
  const previewLite = qs.get("preview") === "lite";

  let cfg = {
    capture_mode: "relative",
    view_mode: "infinite",
    camera_lag: 0.28,
    motion_scale: 0.55,
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
    click_colors: {
      left: "#ffffff",
      right: "#cccccc",
      middle: "#888888",
      x1: "#aaaaaa",
      x2: "#666666",
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
    source_bg_enabled: false,
    source_bg_color: "#000000",
    source_bg_opacity: 0,
    overlay_opacity: 1,
    show_stats: false,
    stats_opacity: 0.55,
    stats_bg: true,
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
  };

  const CM_PER_INCH = 2.54;

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

  function hexToRgb(hex) {
    if (colorCache.has(hex)) return colorCache.get(hex);
    let h = String(hex || "#ffffff").replace("#", "").trim();
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    if (h.length >= 8) h = h.slice(0, 6);
    // parseInt("#000000") is 0 — must not use || fallback (that forced white)
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
    return Math.pow(u, 1.35);
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

  function applyPadLayout() {
    if (!cfg.pad_enabled) {
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

    const shape = cfg.pad_shape || "rounded";
    pad.className = "pad shape-" + shape;
    if (!cfg.pad_bg_enabled) pad.classList.add("no-bg");
    if (!cfg.pad_border_enabled) pad.classList.add("no-border");
    if (!cfg.pad_shadow) pad.classList.add("no-shadow");
    if (cfg.pad_blur) pad.classList.add("frost");

    const radius = Number(cfg.pad_radius) || 12;
    pad.style.setProperty("--pad-radius", radius + "px");

    if (cfg.pad_bg_enabled) {
      padBg.style.background = rgba(hexToRgb(cfg.pad_bg_color), Number(cfg.pad_bg_opacity) ?? 0.72);
    } else {
      padBg.style.background = "transparent";
    }

    padBg.style.border = "none";
    const shadows = [];
    if (cfg.pad_border_enabled) {
      const bw = Math.max(0.5, Number(cfg.pad_border_width) || 1.5);
      const bc = rgba(
        hexToRgb(cfg.pad_border_color),
        Number(cfg.pad_border_opacity) ?? 0.12
      );
      shadows.push(`inset 0 0 0 ${bw}px ${bc}`);
    }
    if (cfg.pad_shadow && cfg.pad_bg_enabled) {
      const so = Number(cfg.pad_shadow_opacity) ?? 0.4;
      shadows.push(`0 10px 36px rgba(0,0,0,${so})`);
    }
    padBg.style.boxShadow = shadows.length ? shadows.join(", ") : "none";

    const br =
      shape === "rect"
        ? "0"
        : shape === "pill"
          ? "999px"
          : shape === "circle"
            ? "50%"
            : shape === "stadium"
              ? "40% / 50%"
              : radius + "px";
    padBg.style.borderRadius = br;
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

    padCrosshair.hidden = !cfg.pad_crosshair;
    if (cfg.pad_crosshair) {
      const size = Number(cfg.pad_crosshair_size) || 14;
      padCrosshair.style.width = size + "px";
      padCrosshair.style.height = size + "px";
      padCrosshair.style.opacity = String(Number(cfg.pad_crosshair_opacity) ?? 0.14);
      padCrosshair.querySelectorAll("span").forEach((el) => {
        el.style.background = rgba(hexToRgb(cfg.pad_crosshair_color), 1);
      });
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
    if (previewLite) {
      cfg.target_fps = Math.min(Number(cfg.target_fps) || 60, 30);
      cfg.trail_glow = false;
      cfg.trail_samples = 1;
      cfg.trail_curve = Math.min(Number(cfg.trail_curve) || 0, 0.25);
      cfg.trail_max_points = Math.min(Number(cfg.trail_max_points) || 120, 64);
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

    statsEl.style.opacity = String(cfg.stats_opacity ?? 0.55);

    const bg = truthyFlag(cfg.stats_bg, true);
    const border = truthyFlag(cfg.stats_border, true);
    statsEl.classList.toggle("no-bg", !bg);
    statsEl.classList.toggle("no-border", !border);
    statsEl.classList.toggle("bare", !bg && !border);

    if (bg) {
      statsEl.style.removeProperty("background");
      statsEl.style.removeProperty("background-color");
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
    setStatRow("distance", truthyFlag(cfg.stats_show_distance, true));
    setStatRow("clicks", truthyFlag(cfg.stats_show_clicks, true));
    setStatRow("cps", truthyFlag(cfg.stats_show_cps, true));

    const units = cfg.stats_units || "cm";
    const rateUnit = units === "raw" ? "" : units === "m" ? "m/s" : "cm/s";
    const distUnit = units === "raw" ? "" : units === "m" ? "m" : "cm";
    if (sSpeedUnit) sSpeedUnit.textContent = rateUnit;
    if (sPeakUnit) sPeakUnit.textContent = rateUnit;
    if (sDistUnit) sDistUnit.textContent = distUnit;

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

  function updateCameraTarget() {
    camTx = wx - pw / 2;
    camTy = wy - ph / 2;
  }

  let lastGridOx = null;
  let lastGridOy = null;

  function updateGridOffset() {
    if (!cfg.pad_grid || !padGridPat) return;
    const g = Math.max(4, Math.round(Number(cfg.pad_grid_size) || 40));
    let ox = ((-camX % g) + g) % g;
    let oy = ((-camY % g) + g) % g;
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

  function motionScale() {
    const s = Number(cfg.motion_scale);
    return Number.isFinite(s) && s > 0 ? Math.max(0.05, Math.min(3, s)) : 0.5;
  }

  function applyMotionDelta(mdx, mdy, t, dt) {
    const infinite = (cfg.view_mode || "infinite") === "infinite";
    const speed = Math.hypot(mdx, mdy) / Math.max(dt, 1e-4);
    tx += mdx;
    ty += mdy;
    if (!infinite) {
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
    const infinite = (cfg.view_mode || "infinite") === "infinite";
    const mScale = motionScale();

    if (mode === "absolute" && msg.x != null && msg.y != null) {
      const sw = window.screen.width || window.innerWidth;
      const sh = window.screen.height || window.innerHeight;
      const nx = (msg.x / sw) * pw;
      const ny = (msg.y / sh) * ph;
      const dt = Math.max(t - lastMoveT, 1e-4);
      if (infinite) {
        if (handleMouse._lx != null) {
          const mdx = ((msg.x - handleMouse._lx) / sw) * pw * 2.2 * mScale;
          const mdy = ((msg.y - handleMouse._ly) / sh) * ph * 2.2 * mScale;
          applyMotionDelta(mdx, mdy, t, dt);
        }
        handleMouse._lx = msg.x;
        handleMouse._ly = msg.y;
      } else {
        tx = nx;
        ty = ny;
        wx = nx;
        wy = ny;
        lastMoveT = t;
        if (cfg.trail_enabled) pushPoint(wx, wy, t, 0);
      }
      lastMoveT = t;
    } else if (dx !== 0 || dy !== 0) {
      const padScale = Math.min(pw, ph) / 480;
      const mdx = dx * padScale * mScale;
      const mdy = dy * padScale * mScale;
      const dt = Math.max(t - lastMoveT, 1e-4);
      applyMotionDelta(mdx, mdy, t, dt);
    }

    if (msg.btn && String(msg.btn).endsWith("_down") && cfg.show_clicks) {
      const button = String(msg.btn).replace(/_down$/, "");
      const colors = cfg.click_colors || {};
      clicks.push({
        x: wx,
        y: wy,
        t,
        color: colors[button] || "#ffffff",
      });
      needsDraw = true;
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
    return { x: x - camX, y: y - camY };
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
    const infinite = (cfg.view_mode || "infinite") === "infinite";
    if (infinite) {
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
    for (let i = 0; i < screen.length - 1; i++) {
      const p0 = screen[Math.max(0, i - 1)];
      const p1 = screen[i];
      const p2 = screen[i + 1];
      const p3 = screen[Math.min(screen.length - 1, i + 2)];
      const segs = Math.max(1, Math.round(samples * curve));
      for (let s = 0; s < segs; s++) {
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
    }
    path.push(screen[screen.length - 1]);
    return path;
  }

  function strokePolyline(path, startI, endI) {
    if (endI <= startI) return;
    ctx.beginPath();
    ctx.moveTo(path[startI].x, path[startI].y);
    for (let i = startI + 1; i <= endI; i++) {
      ctx.lineTo(path[i].x, path[i].y);
    }
    ctx.stroke();
  }

  function drawSoftGlow(path, width, glowMul) {
    if (path.length < 2) return;
    const tip = path[path.length - 1];
    const mid = path[Math.floor(path.length * 0.65)] || tip;
    const rgb = speedToColor(mid.speed || tip.speed || 0);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = rgba(rgb, 0.16);
    ctx.lineWidth = width * glowMul * 1.75;
    let segStart = 0;
    for (let i = 1; i < path.length; i++) {
      if (offscreen(path[i - 1], path[i])) {
        strokePolyline(path, segStart, i - 1);
        segStart = i;
      }
    }
    strokePolyline(path, segStart, path.length - 1);
    ctx.strokeStyle = rgba(rgb, 0.28);
    ctx.lineWidth = width * glowMul;
    segStart = 0;
    for (let i = 1; i < path.length; i++) {
      if (offscreen(path[i - 1], path[i])) {
        strokePolyline(path, segStart, i - 1);
        segStart = i;
      }
    }
    strokePolyline(path, segStart, path.length - 1);
    ctx.restore();
  }

  function drawTrail(now) {
    if (!cfg.trail_enabled || points.length < 2) return;

    const life = (Number(cfg.trail_lifetime_ms) || 750) / 1000;
    const width = Number(cfg.trail_width) || 2.4;
    const glow = !!cfg.trail_glow;
    const glowMul = 1.4 + Math.min(2.5, (Number(cfg.trail_glow_blur) || 6) / 10);
    const path = buildTrailPath();

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (glow) drawSoftGlow(path, width, glowMul);

    ctx.save();
    let lastStyle = "";
    let lastWidth = -1;
    let pathOpen = false;
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1];
      const b = path[i];
      const alpha = fadeAlpha(now - b.t, life);
      if (alpha <= 0.008 || offscreen(a, b)) {
        pathOpen = false;
        continue;
      }
      const rgb = speedToColor(b.speed);
      const aq = Math.round(alpha * 8) / 8;
      const style = rgba(rgb, aq);
      const sp = Math.min(1, b.speed / (Number(cfg.speed_max) || 3200));
      const lw = width * (0.9 + sp * 0.55);
      if (style !== lastStyle || Math.abs(lw - lastWidth) > 0.35) {
        if (pathOpen) ctx.stroke();
        ctx.strokeStyle = style;
        ctx.lineWidth = lw;
        lastStyle = style;
        lastWidth = lw;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        pathOpen = true;
      } else if (!pathOpen) {
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        pathOpen = true;
      } else {
        ctx.lineTo(b.x, b.y);
      }
    }
    if (pathOpen) ctx.stroke();
    ctx.restore();
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

    for (const c of clicks) {
      const u = (now - c.t) / life;
      if (u < 0 || u > 1) continue;
      const s = worldToScreen(c.x, c.y);
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
  function frame(ts) {
    requestAnimationFrame(frame);
    const fps = Number(cfg.target_fps);
    if (fps > 0) {
      const minDelta = 1000 / Math.min(240, Math.max(15, fps));
      if (ts - lastDraw < minDelta - 0.5) return;
    }

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

    const infinite = (cfg.view_mode || "infinite") === "infinite";
    if (infinite) {
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

    needsDraw = isAnimating(now);
  }

  function qsToken() {
    return new URL(window.location.href).searchParams.get("token") || "";
  }
  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.classList.remove("ok", "err");
    if (kind) statusEl.classList.add(kind);
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
  }

  function connect() {
    const token = qsToken();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const q = token ? `?token=${encodeURIComponent(token)}` : "";
    if (ws) try { ws.close(); } catch (_) {}
    setStatus("Connecting");
    ws = new WebSocket(`${proto}://${location.host}/ws${q}`);
    ws.onopen = () => setStatus("Live", "ok");
    ws.onclose = () => {
      setStatus("Reconnecting", "err");
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 900);
    };
    ws.onerror = () => setStatus("Connection error", "err");
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (_) { return; }
      if (msg.type === "hello" || msg.type === "config") {
        applyConfig(msg.data || {});
        setStatus("Live", "ok");
      } else if (msg.type === "mouse") {
        handleMouse(normalizeTime(msg));
      } else if (msg.type === "stats") {
        updateStats(msg.data || {});
      }
    };
  }

  window.addEventListener("resize", () => {
    applyPadLayout();
    placeStatsPanel();
    needsDraw = true;
  });
  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => {
      resizeCanvas();
      needsDraw = true;
    }).observe(pad);
  }

  applyConfig(cfg);
  connect();
  requestAnimationFrame(frame);

