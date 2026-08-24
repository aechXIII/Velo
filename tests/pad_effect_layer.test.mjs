import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const appSource = readFileSync(new URL("../overlay/app.js", import.meta.url), "utf8");
const styleSource = readFileSync(new URL("../overlay/style.css", import.meta.url), "utf8");

test("pad border and glow render on a foreground layer above the background image", () => {
  const imageCreation = appSource.indexOf('padBgImage.className = "pad-bg-image"');
  const effectsCreation = appSource.indexOf('padBgEffects.className = "pad-bg-effects"');
  const imageAppend = appSource.indexOf("padBg.appendChild(padBgImage)");
  const effectsAppend = appSource.indexOf("padBg.appendChild(padBgEffects)");

  assert.ok(imageCreation >= 0, "the background image layer should exist");
  assert.ok(effectsCreation >= 0, "a foreground effects layer should exist");
  assert.ok(imageAppend >= 0 && effectsAppend > imageAppend, "effects should be appended after the image");
  assert.match(styleSource, /\.pad-bg-effects\s*{[^}]*z-index:\s*1;/s);
  assert.match(appSource, /padBgEffects\.style\.boxShadow\s*=/);
});
