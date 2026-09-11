// Time is measured at frame capture, not when a slow API response arrives.
import policy from "./confidencePolicy.json" with { type: "json" };
export const AUTO_ADD_CONFIDENCE = policy.default;
const CLASS_NAMES = { 사과: "apple", 마늘: "galic", 대파: "l_onion", 새우: "shrimp" };
export function getConfidenceThreshold(item) {
  const modelClass = item.class_name?.trim().toLowerCase();
  return policy.classes[modelClass] ?? policy.classes[CLASS_NAMES[item.name]] ?? policy.default;
}
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
    const threshold = getConfidenceThreshold(item);
    if (item.confidence >= threshold) track.since ??= now;
    else track.since = null;
    const seconds = track.since === null ? 0 : (now - track.since) / 1000;
    return { ...item, threshold, seconds, added: track.added, ready: !track.added && seconds >= 1 };
  });
}
