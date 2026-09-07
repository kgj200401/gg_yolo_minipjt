// Time is measured at frame capture, not when a slow API response arrives.
export const AUTO_ADD_CONFIDENCE = 0.65;
export function updateTracker(tracks, predictions, now) {
  const visible = new Set(predictions.map((item) => item.name));
  for (const name of tracks.keys()) {
    if (!visible.has(name)) {
      tracks.delete(name);
    }
  }
  return predictions.map((item) => {
    let track = tracks.get(item.name);
    if (!track) {
      track = { since: null, last: now, added: false };
      tracks.set(item.name, track);
    }
    if (now - track.last > 4000) track.since = null;
    track.last = now;
    if (item.confidence >= AUTO_ADD_CONFIDENCE) track.since ??= now;
    else track.since = null;
    const seconds = track.since === null ? 0 : (now - track.since) / 1000;
    return { ...item, seconds, added: track.added, ready: !track.added && seconds >= 1 };
  });
}
