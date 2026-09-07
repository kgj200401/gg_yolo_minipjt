import test from "node:test";
import assert from "node:assert/strict";
import { updateTracker } from "./detectionTracker.js";

const prediction = (confidence = 0.65) => [{ name: "사과", confidence }];

test("requires one second and resets on low confidence", () => {
  const tracks = new Map();
  assert.equal(updateTracker(tracks, prediction(), 0)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 999)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 1000)[0].ready, true);
  updateTracker(tracks, prediction(0.6499), 2100);
  assert.equal(updateTracker(tracks, prediction(), 3000)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 3999)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 4000)[0].ready, true);
});

test("one absent sample unlocks item, reappearance requires a new second", () => {
  const tracks = new Map();
  updateTracker(tracks, prediction(), 0);
  tracks.get("사과").added = true;
  assert.equal(updateTracker(tracks, prediction(), 3000)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(0.5), 3200)[0].added, true);
  updateTracker(tracks, [], 3500);
  assert.equal(tracks.has("사과"), false);
  assert.equal(updateTracker(tracks, prediction(), 4000)[0].added, false);
  assert.equal(updateTracker(tracks, prediction(), 4999)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 5000)[0].ready, true);
});

test("missing frames and long gaps reset candidate confirmation", () => {
  const tracks = new Map();
  updateTracker(tracks, prediction(), 0);
  updateTracker(tracks, [], 1000);
  assert.equal(updateTracker(tracks, prediction(), 2000)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 7000)[0].ready, false);
});
