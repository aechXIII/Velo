const PREVIEW_MODES = new Set(["off", "lite", "live", "auto"]);

function normalizePreviewMode(mode) {
  return PREVIEW_MODES.has(mode) ? mode : "lite";
}

export function beginCropPreviewSession(currentMode) {
  return {
    mode: "live",
    restoreMode: normalizePreviewMode(currentMode),
  };
}

export function finishCropPreviewSession(session, explicitMode) {
  return {
    mode: normalizePreviewMode(explicitMode ?? session?.restoreMode),
    restoreMode: null,
  };
}
