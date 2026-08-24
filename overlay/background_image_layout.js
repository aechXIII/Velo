function finitePositive(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function clampPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 50;
  return Math.max(0, Math.min(100, number));
}

function baseImageScale({ naturalWidth, naturalHeight, frameWidth, frameHeight, fit }) {
  const widthScale = frameWidth / naturalWidth;
  const heightScale = frameHeight / naturalHeight;
  return fit === "contain"
    ? Math.min(widthScale, heightScale)
    : Math.max(widthScale, heightScale);
}

export function calculateBackgroundImageLayout(options) {
  const naturalWidth = finitePositive(options.naturalWidth, 1);
  const naturalHeight = finitePositive(options.naturalHeight, 1);
  const frameWidth = finitePositive(options.frameWidth, 1);
  const frameHeight = finitePositive(options.frameHeight, 1);
  const zoom = finitePositive(options.zoom, 1);
  const positionX = clampPercent(options.positionX);
  const positionY = clampPercent(options.positionY);

  let width;
  let height;
  if (options.fit === "100% 100%") {
    width = frameWidth * zoom;
    height = frameHeight * zoom;
  } else {
    const scale = baseImageScale({
      naturalWidth,
      naturalHeight,
      frameWidth,
      frameHeight,
      fit: options.fit,
    });
    width = naturalWidth * scale * zoom;
    height = naturalHeight * scale * zoom;
  }

  return {
    width,
    height,
    left: positionX === 0 ? 0 : (frameWidth - width) * (positionX / 100),
    top: positionY === 0 ? 0 : (frameHeight - height) * (positionY / 100),
  };
}

export function calculateActualSizeZoom(options) {
  const naturalWidth = finitePositive(options.naturalWidth, 1);
  const naturalHeight = finitePositive(options.naturalHeight, 1);
  const frameWidth = finitePositive(options.frameWidth, 1);
  const frameHeight = finitePositive(options.frameHeight, 1);
  const scale = baseImageScale({
    naturalWidth,
    naturalHeight,
    frameWidth,
    frameHeight,
    fit: options.fit,
  });
  return 1 / scale;
}

export function calculatePositionNudge(position, frameSize, imageSize, direction, step) {
  const range = Number(frameSize) - Number(imageSize);
  if (!Number.isFinite(range) || Math.abs(range) <= 0.5) return clampPercent(position);
  return clampPercent(Number(position) + Math.sign(range) * Number(direction) * Number(step));
}
