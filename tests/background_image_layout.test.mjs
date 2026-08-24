import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateActualSizeZoom,
  calculateBackgroundImageLayout,
  calculatePositionNudge,
} from "../overlay/background_image_layout.js";

test("200% zoom selects a 600x300 fragment from a 1200x600 image", () => {
  const layout = calculateBackgroundImageLayout({
    naturalWidth: 1200,
    naturalHeight: 600,
    frameWidth: 600,
    frameHeight: 300,
    fit: "cover",
    zoom: 2,
    positionX: 50,
    positionY: 50,
  });

  assert.deepEqual(layout, {
    width: 1200,
    height: 600,
    left: -300,
    top: -150,
  });
});

test("position selects either edge of a zoomed image", () => {
  const base = {
    naturalWidth: 1200,
    naturalHeight: 600,
    frameWidth: 600,
    frameHeight: 300,
    fit: "cover",
    zoom: 2,
    positionY: 50,
  };

  assert.equal(calculateBackgroundImageLayout({ ...base, positionX: 0 }).left, 0);
  assert.equal(calculateBackgroundImageLayout({ ...base, positionX: 100 }).left, -600);
});

test("zooming out centers the whole image inside the frame", () => {
  const layout = calculateBackgroundImageLayout({
    naturalWidth: 1200,
    naturalHeight: 600,
    frameWidth: 600,
    frameHeight: 300,
    fit: "cover",
    zoom: 0.5,
    positionX: 50,
    positionY: 50,
  });

  assert.deepEqual(layout, {
    width: 300,
    height: 150,
    left: 150,
    top: 75,
  });
});

test("actual-size zoom preserves one image pixel per frame pixel", () => {
  assert.equal(
    calculateActualSizeZoom({
      naturalWidth: 1200,
      naturalHeight: 600,
      frameWidth: 600,
      frameHeight: 300,
      fit: "cover",
    }),
    2,
  );
});

test("arrow nudges move the image in the requested direction at any zoom", () => {
  assert.equal(calculatePositionNudge(50, 600, 1200, -1, 1), 51);
  assert.equal(calculatePositionNudge(50, 600, 300, -1, 1), 49);
  assert.equal(calculatePositionNudge(50, 600, 1200, 1, 5), 45);
  assert.equal(calculatePositionNudge(50, 600, 300, 1, 5), 55);
});
