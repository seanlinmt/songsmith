import { fileUrl } from "./format.js";

export const PRESETS = [
  { tag: "synth-pop" }, { tag: "lo-fi" }, { tag: "funk rock" }, { tag: "dream pop" },
  { tag: "synthwave" }, { tag: "jazz" }, { tag: "orchestral" }, { tag: "trap" },
  { tag: "acoustic folk" }, { tag: "city pop" },
];

export const DURATIONS = [15, 30, 60, 120, 240];

export const STAGES = [
  { key: "writing lyrics", label: "Writing lyrics" },
  { key: "naming song", label: "Naming your song" },
  { key: "generating music", label: "Generating music" },
  { key: "generating cover art", label: "Painting cover art" },
];

export const DONE_STATUSES = ["done", "complete", "completed"];

export function stageFromJob(job) {
  if (!job) return 0;
  // Server reports the live stage via job.message (e.g. "naming song"),
  // which matches the STAGES keys exactly.
  const msg = String(job.message || "").toLowerCase().replace(/[\s-]+/g, " ").trim();
  if (msg) {
    const i = STAGES.findIndex((s) => s.key === msg);
    if (i >= 0) return i;
  }
  // Fall back to pipeline progress fractions (0.1 lyrics, 0.2 naming,
  // 0.25 style, 0.3 music, 0.8 cover).
  const p = Number(job.progress) || 0;
  if (p >= 0.8) return 3;
  if (p >= 0.3) return 2;
  if (p >= 0.2) return 1;
  return 0;
}

export function songCoverUrl(s) {
  if (s.cover_url) return fileUrl(s.cover_url);
  if (s.cover_path) return fileUrl(s.cover_path);
  if (s.id) return "/files/covers/" + s.id + ".png";
  return "";
}

export function songAudioUrl(s) {
  if (s.audio_url) return fileUrl(s.audio_url);
  if (s.audio_path) return fileUrl(s.audio_path);
  if (s.id) return "/files/audio/" + s.id + ".wav";
  return "";
}

export function supportsExtend(config) {
  return !!(config && config.supports_extend);
}
