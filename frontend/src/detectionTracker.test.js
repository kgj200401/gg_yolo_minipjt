import test from "node:test";
import assert from "node:assert/strict";
import { getConfidenceThreshold, updateTracker } from "./detectionTracker.js";

const prediction = (confidence = 0.65) => [{ name: "식빵", confidence }];

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
  tracks.get("식빵").added = true;
  assert.equal(updateTracker(tracks, prediction(), 3000)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(0.5), 3200)[0].added, true);
  updateTracker(tracks, [], 3500);
  assert.equal(tracks.has("식빵"), false);
  assert.equal(updateTracker(tracks, prediction(), 4000)[0].added, false);
  assert.equal(updateTracker(tracks, prediction(), 4999)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 5000)[0].ready, true);
});

test("class thresholds include the boundary and reset the one-second timer below it", () => {
  for (const [name, class_name, threshold] of [
    ["사과", "apple", .5], ["마늘", "galic", .6], ["대파", "l_onion", .6],
    ["새우", "shrimp", .6], ["고기", "raw_pork", .65],
  ]) {
    const tracks = new Map();
    const item = { name, class_name, confidence: threshold };
    assert.equal(getConfidenceThreshold(item), threshold);
    assert.equal(updateTracker(tracks, [item], 0)[0].ready, false);
    assert.equal(updateTracker(tracks, [item], 1000)[0].ready, true);
    updateTracker(tracks, [{ ...item, confidence: threshold - .0001 }], 1500);
    assert.equal(updateTracker(tracks, [item], 2000)[0].ready, false);
  }
  assert.equal(getConfidenceThreshold({ name: "대파", class_name: "large green onion" }), .6);
  assert.equal(getConfidenceThreshold({ name: "unknown" }), .65);
});

test("low-confidence apple does not unlock an already-added item until absent", () => {
  const tracks = new Map();
  const item = { name: "사과", class_name: "apple", confidence: .5 };
  updateTracker(tracks, [item], 0);
  tracks.get(item.name).added = true;
  assert.equal(updateTracker(tracks, [{ ...item, confidence: .4 }], 1500)[0].added, true);
  assert.equal(updateTracker(tracks, [item], 3000)[0].ready, false);
  updateTracker(tracks, [], 3500);
  assert.equal(updateTracker(tracks, [item], 4000)[0].ready, false);
  assert.equal(updateTracker(tracks, [item], 5000)[0].ready, true);
});

test("missing frames and long gaps reset candidate confirmation", () => {
  const tracks = new Map();
  updateTracker(tracks, prediction(), 0);
  updateTracker(tracks, [], 1000);
  assert.equal(updateTracker(tracks, prediction(), 2000)[0].ready, false);
  assert.equal(updateTracker(tracks, prediction(), 7000)[0].ready, false);
});
