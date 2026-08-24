import assert from "node:assert/strict";
import test from "node:test";

import { updateBackgroundCropSession } from "../overlay/background_crop_session.js";

test("a crop request received before image config activates after hydration", () => {
  let state = { requested: false, imageAvailable: false, active: false };

  state = updateBackgroundCropSession(state, { type: "request", enabled: true });
  assert.deepEqual(state, {
    requested: true,
    imageAvailable: false,
    active: false,
  });

  state = updateBackgroundCropSession(state, { type: "image", available: true });
  assert.deepEqual(state, {
    requested: true,
    imageAvailable: true,
    active: true,
  });
});

test("disabling crop clears a pending request", () => {
  const state = updateBackgroundCropSession(
    { requested: true, imageAvailable: false, active: false },
    { type: "request", enabled: false },
  );

  assert.deepEqual(state, {
    requested: false,
    imageAvailable: false,
    active: false,
  });
});
