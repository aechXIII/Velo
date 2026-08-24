export function updateBackgroundCropSession(state, event) {
  const next = {
    requested: !!state.requested,
    imageAvailable: !!state.imageAvailable,
  };
  if (event.type === "request") next.requested = !!event.enabled;
  if (event.type === "image") next.imageAvailable = !!event.available;
  return {
    ...next,
    active: next.requested && next.imageAvailable,
  };
}
