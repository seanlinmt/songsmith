export const fmtDur = (s) => {
  const n = Math.max(0, Math.round(Number(s) || 0));
  return Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");
};

export const fmtBytes = (b) => {
  if (b == null || isNaN(b)) return "";
  if (b > 1048576) return (b / 1048576).toFixed(1) + " MB";
  if (b > 1024) return Math.round(b / 1024) + " KB";
  return b + " B";
};

export const fileUrl = (p) => {
  if (!p) return "";
  return "/" + String(p).replace(/^\.?\//, "").replace(/^\/+/, "");
};

export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
