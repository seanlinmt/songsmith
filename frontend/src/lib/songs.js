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

export const JOB_STAGES = ["queued", "writing_lyrics", "naming_song", "generating_music", "generating_cover", "complete"];

export function stageFromJob(job) {
  const s = String((job && (job.stage || job.status)) || "queued").toLowerCase().replace(/[\s-]+/g, "_");
  const i = JOB_STAGES.indexOf(s);
  if (i < 0) return 1;
  return i;
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
