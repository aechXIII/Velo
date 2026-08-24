import assert from "node:assert/strict";
import test from "node:test";

import {
  beginCropPreviewSession,
  finishCropPreviewSession,
} from "../config_ui/crop_preview_session.js";

test("crop editing temporarily uses Live and restores every prior preview mode", () => {
  for (const mode of ["auto", "lite", "live", "off"]) {
    const session = beginCropPreviewSession(mode);

    assert.deepEqual(session, { mode: "live", restoreMode: mode });
    assert.deepEqual(finishCropPreviewSession(session), {
      mode,
      restoreMode: null,
    });
  }
});

test("an explicit preview choice replaces the saved mode while cropping", () => {
  const session = beginCropPreviewSession("auto");

  assert.deepEqual(finishCropPreviewSession(session, "off"), {
    mode: "off",
    restoreMode: null,
  });
});
