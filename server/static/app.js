/* ============================================================
   Songsmith — SPA logic (vanilla JS, no frameworks)
   ============================================================ */
"use strict";

/* ---------- tiny helpers ---------- */
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

function esc(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtDuration(s) {
  if (s == null || isNaN(s)) return "—";
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return "—"; }
}

function elapsedSince(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s`;
  return `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s`;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function toast(msg, kind = "ok", ms = 4200) {
  const root = $("#toast-root");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = `<span class="toast-dot"></span><span>${esc(msg)}</span>`;
  root.appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, ms);
}

/* gradient placeholder colors, stable per song id */
function hashHues(id) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) % 360;
  return [h, (h + 70) % 360];
}

/* ---------- state ---------- */
const state = {
  tab: "create",
  config: null,
  health: null,
  songs: [],
  lyricsOpen: false,
  lyricsBusy: false,
  lyricsError: null,
  chipsActive: new Set(),
  form: { prompt: "", lyrics: "", instrumental: false, duration: 60 },
  activeGroups: new Map(),   // gid -> {jobs, type, startedAt}
  finishingGroups: new Map(),// gid -> {jobs, removeAt}
  knownNew: new Set(),
  audio: new Audio(),
  playingId: null,
  extendSongId: null,
};

const STYLE_CHIPS = [
  "synth-pop", "lo-fi", "funk rock", "dream pop", "synthwave",
  "jazz", "ambient", "indie rock", "orchestral", "house",
];

/* ---------- shared audio ---------- */
function stopAudio() {
  state.audio.pause();
  state.playingId = null;
  syncPlayIcons();
}

function togglePlay(song) {
  if (!song.audio_url) { toast("Audio is not ready yet", "err"); return; }
  if (state.playingId === song.id) { stopAudio(); return; }
  stopAudio();
  state.audio.src = song.audio_url;
  state.audio.play().catch(() => toast("Could not play audio", "err"));
  state.playingId = song.id;
  syncPlayIcons();
}

function syncPlayIcons() {
  $$('[data-action="play"]').forEach((btn) => {
    const on = state.playingId === btn.dataset.id;
    btn.innerHTML = svgUse(on ? "i-pause" : "i-play");
  });
  $$("[data-song-card]").forEach((c) => c.classList.toggle("playing", c.dataset.songCard === state.playingId));
}

state.audio.addEventListener("ended", stopAudio);

function svgUse(id, cls = "") {
  return `<svg class="${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
}

/* ---------- navigation ---------- */
function setTab(tab) {
  state.tab = tab;
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.nav === tab));
  ["create", "library", "settings"].forEach((t) => {
    $(`#view-${t}`).hidden = t !== tab;
  });
  if (tab === "library") loadSongs().then(renderLibrary).catch(() => {});
  if (tab === "settings") renderSettings();
  if (tab === "create") renderCreate();
  renderProgress();
}

/* ============================================================
   CREATE view
   ============================================================ */
function renderCreate() {
  const f = state.form;
  const fill = ((f.duration - 15) / (240 - 15)).toFixed(4);
  $("#view-create").innerHTML = `
    <div class="view-head">
      <h1>Create a song</h1>
      <p>Describe the sound you're after. One song is generated per request.</p>
    </div>
    <div id="progress-create"></div>
    <div class="create-panel">
      <div>
        <label class="field-label" for="prompt-input">Describe your song</label>
        <textarea id="prompt-input" class="prompt-input"
          placeholder="e.g. dreamy synthwave, warm analog pads, 104 bpm, distant female vocals">${esc(f.prompt)}</textarea>
      </div>

      <div class="control-block">
        <div class="field-label">Style tags <span class="hint">click to add to the prompt</span></div>
        <div class="chips" id="chips">
          ${STYLE_CHIPS.map((c) => `
            <button type="button" class="chip ${state.chipsActive.has(c) ? "active" : ""}" data-chip="${esc(c)}">${esc(c)}</button>
          `).join("")}
        </div>
      </div>

      <div class="collapsible ${state.lyricsOpen ? "open" : ""}" id="lyrics-collapsible">
        <button type="button" class="collapsible-head" data-action="toggle-lyrics">
          <span>Custom lyrics</span>
          <svg class="chev" width="16" height="16"><use href="#i-chev"/></svg>
        </button>
        <div class="collapsible-body">
          <textarea id="lyrics-input" class="lyrics-input"
            placeholder="[Verse]&#10;Write your own lines, or let the model draft them.&#10;[Chorus]&#10;Use [Verse] / [Chorus] / [Bridge] tags to structure sections.">${esc(f.lyrics)}</textarea>
          <div class="lyrics-actions">
            <button type="button" class="btn" data-action="write-lyrics" ${state.lyricsBusy ? "disabled" : ""}>
              ${state.lyricsBusy ? '<span class="spinner"></span> Writing…' : "✨ Write lyrics for me"}
            </button>
            ${state.lyricsError ? `<span class="lyrics-error">${esc(state.lyricsError)}</span>` : ""}
          </div>
        </div>
      </div>

      <div class="create-row">
        <div class="control-block">
          <span class="field-label">Vocals</span>
          <label class="toggle">
            <input type="checkbox" id="instrumental-toggle" ${f.instrumental ? "checked" : ""}>
            <span class="toggle-track"></span>
            <span class="toggle-label">Instrumental</span>
          </label>
        </div>
        <div class="control-block duration-block">
          <span class="field-label">Duration <span class="duration-value" id="duration-value">${f.duration}s</span></span>
          <div class="slider-wrap">
            <input type="range" id="duration-slider" class="slider" min="15" max="240" step="5" value="${f.duration}" style="--fill:${fill}">
            <div class="slider-marks">
              ${[15, 30, 60, 120, 240].map((m) => `<button type="button" data-mark="${m}">${m}s</button>`).join("")}
            </div>
          </div>
        </div>
      </div>

      <div class="create-foot">
        <span class="foot-hint">1 song is created per request.</span>
        <span id="create-error" class="form-error"></span>
        <button type="button" class="btn btn-primary btn-generate" data-action="generate">${svgUse("i-sparkle")} Generate</button>
      </div>
    </div>
  `;
}

function updateDurationUI(val) {
  state.form.duration = val;
  const slider = $("#duration-slider");
  if (slider) {
    const min = parseFloat(slider.min) || 15;
    const max = parseFloat(slider.max) || 240;
    slider.style.setProperty("--fill", String((val - min) / (max - min)));
  }
  const out = $("#duration-value");
  if (out) out.textContent = `${val}s`;
}

async function writeLyrics() {
  const prompt = $("#prompt-input").value.trim();
  const errEl = $("#create-error");
  if (errEl) errEl.textContent = "";
  if (!prompt) { toast("Describe the song first — the lyricist needs a direction", "err"); return; }
  state.lyricsBusy = true;
  renderCreate();
  try {
    const { lyrics } = await api("/api/lyrics", { method: "POST", body: JSON.stringify({ prompt }) });
    state.form.lyrics = lyrics;
    state.lyricsOpen = true;
    state.lyricsBusy = false;
    state.lyricsError = null;
    renderCreate();
  } catch (err) {
    state.lyricsBusy = false;
    state.lyricsError = err.message;
    renderCreate();
  }
}

async function generate() {
  const prompt = $("#prompt-input").value.trim();
  const lyrics = $("#lyrics-input") ? $("#lyrics-input").value.trim() : "";
  const errEl = $("#create-error");
  if (errEl) errEl.textContent = "";
  if (!prompt && !lyrics) {
    if (errEl) errEl.textContent = "Add a prompt or some lyrics first.";
    return;
  }
  state.form.prompt = prompt;
  state.form.lyrics = lyrics;
  const btn = $('[data-action="generate"]');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Starting…'; }
  try {
    const res = await api("/api/songs", {
      method: "POST",
      body: JSON.stringify({
        prompt: prompt || lyrics.slice(0, 120),
        lyrics,
        tags: [...state.chipsActive],
        instrumental: state.form.instrumental,
        duration_seconds: state.form.duration,
      }),
    });
    trackGroup(res.job_group_id, "generate");
    setTab("library");
    toast("Generation started — 1 song queued");
  } catch (err) {
    toast(`Could not start generation: ${err.message}`, "err");
    if (btn) { btn.disabled = false; renderCreate(); }
  }
}

/* ============================================================
   progress / skeletons
   ============================================================ */
function trackGroup(gid, type) {
  state.activeGroups.set(gid, { jobs: [], type, startedAt: new Date().toISOString() });
  pollTick();
}

function groupLabel(type) {
  return { generate: "Generating", regenerate: "Regenerating", extend: "Extending" }[type] || "Generating";
}

function jobStatusLine(job) {
  if (!job) return `<span class="msg"><span class="spinner" style="width:10px;height:10px;border-width:1.5px"></span> queued</span>`;
  if (job.status === "error") return `<span class="error-msg">${esc(job.message || "failed")}</span>`;
  if (job.status === "done") return `<span class="done-msg">ready ${svgUse("i-check", "ok-ic")}</span>`;
  return `<span class="msg blink-dots">${esc(job.message || "working")}</span>`;
}

function skeletonCard(job) {
  const pct = job ? Math.round((job.progress || 0) * 100) : 0;
  return `
    <div class="skeleton-card">
      <div class="skeleton-cover"></div>
      <div class="skeleton-body">
        <div class="sk-line w60"></div>
        <div class="sk-line w40"></div>
        <div class="sk-progress">
          <div class="sk-bar"><i style="width:${pct}%"></i></div>
          <div class="sk-status ${job?.status === "error" ? "error-msg" : ""}">
            <span class="status-line">${jobStatusLine(job)}</span>
            <span>${job?.status === "done" ? "" : `${pct}%`}</span>
          </div>
        </div>
      </div>
    </div>`;
}

function renderProgress() {
  const containers = ["#progress-create", "#progress-library"]
    .map((s) => $(s))
    .filter(Boolean);
  if (!containers.length) return;

  let html = "";
  for (const [gid, g] of state.activeGroups) {
    const shown = g.jobs.length >= 2 ? g.jobs.slice(0, 2) : [g.jobs[0], null];
    html += `
      <div class="progress-group" data-group="${esc(gid)}">
        <div class="progress-title">
          <span class="live-dot"></span>
          ${esc(groupLabel(g.type))}
          ${g.jobs[0] ? `<span>· started ${elapsedSince(g.jobs[0].created_at)} ago</span>` : ""}
        </div>
        <div class="progress-grid">${shown.map((j) => skeletonCard(j)).join("")}</div>
      </div>`;
  }
  for (const [, g] of state.finishingGroups) {
    html += `
      <div class="progress-group">
        <div class="progress-title">${esc(groupLabel(g.type))} · finished</div>
        <div class="progress-grid">${g.jobs.slice(0, 2).map((j) => skeletonCard(j)).join("")}</div>
      </div>`;
  }

  for (const c of containers) c.innerHTML = html;
  $$(".nav-btn").forEach((b) => b.classList.toggle("has-activity", state.activeGroups.size > 0));
}

async function pollTick() {
  if (state._polling) return;
  state._polling = true;
  try {
    const active = await api("/api/jobs/active");
    const groups = new Map();
    for (const j of active) {
      if (!groups.has(j.job_group_id)) groups.set(j.job_group_id, { type: j.type, startedAt: j.created_at });
    }

    // groups that vanished -> fetch final state once, hold briefly, then drop
    for (const [gid, g] of state.activeGroups) {
      if (!groups.has(gid)) {
        try {
          const finalJobs = await api(`/api/jobs?group=${encodeURIComponent(gid)}`);
          state.finishingGroups.set(gid, { jobs: finalJobs, type: g.type });
          const failed = finalJobs.some((j) => j.status === "error");
          const okCount = finalJobs.filter((j) => j.status === "done").length;
          if (okCount) toast(`${okCount} ${okCount > 1 ? "variations" : "variation"} ready — added to your library`);
          else if (failed) toast("Generation failed — see the error in your library", "err", 6500);
          await loadSongs();
          for (const s of finalJobs.map((j) => j.song_id)) state.knownNew.add(s);
          if (state.tab === "library") renderLibrary();
        } catch {}
        state.activeGroups.delete(gid);
        setTimeout(() => { state.finishingGroups.delete(gid); renderProgress(); }, 5000);
      }
    }

    // refresh job rows per active group (per-song status)
    for (const [gid, g] of groups) {
      try {
        const jobs = await api(`/api/jobs?group=${encodeURIComponent(gid)}`);
        const prev = state.activeGroups.get(gid);
        state.activeGroups.set(gid, {
          jobs,
          type: jobs[0]?.type || g.type,
          startedAt: prev?.startedAt || g.startedAt,
        });
      } catch {}
    }
    renderProgress();
  } catch {} finally {
    state._polling = false;
  }
}

/* ============================================================
   LIBRARY view
   ============================================================ */
async function loadSongs() {
  state.songs = await api("/api/songs");
}

function coverMarkup(song) {
  const [h1, h2] = hashHues(song.id);
  const ph = `
    <div class="cover-placeholder" style="background:linear-gradient(135deg,hsl(${h1} 70% 24%),hsl(${h2} 75% 18%))">
      <svg class="ph-note"><use href="#i-note-ph"/></svg>
    </div>`;
  const img = song.cover_url
    ? `<img class="cover-img" src="${esc(song.cover_url)}" alt="" loading="lazy" onerror="this.remove()">`
    : "";
  return ph + img;
}

function renderLibrary() {
  const view = $("#view-library");
  if (!state.songs.length) {
    view.innerHTML = `
      <div class="view-head"><h1>Library</h1></div>
      <div class="empty-state">
        <div class="vinyl" aria-hidden="true"></div>
        <div>
          <h2>Create your first song</h2>
          <p>Nothing here yet. Head to Create, describe a sound, and Songsmith will handle the rest.</p>
        </div>
        <button class="btn btn-primary" data-nav-jump="create">${svgUse("i-sparkle")} Start creating</button>
      </div>`;
    return;
  }

  const activeGids = new Set(state.activeGroups.keys());
  const songs = state.songs.filter((s) => !activeGids.has(s.job_group_id));

  view.innerHTML = `
    <div class="view-head"><h1>Library</h1><p>${songs.length} song${songs.length === 1 ? "" : "s"} · newest first</p></div>
    <div id="progress-library"></div>
    <div class="song-grid">
      ${songs.map((s) => {
        const isPlaying = state.playingId === s.id;
        const isNew = state.knownNew.has(s.id);
        return `
        <article class="song-card ${isPlaying ? "playing" : ""} ${s.status === "error" ? "error-card" : ""} ${isNew ? "is-new" : ""}"
                 data-song-card="${esc(s.id)}">
          <div class="card-cover" data-action="open-detail" data-id="${esc(s.id)}" role="button" tabindex="0" aria-label="Open ${esc(s.title || "song")} details">
            ${coverMarkup(s)}
            <div class="play-overlay">
              <button class="play-btn" data-action="play" data-id="${esc(s.id)}" aria-label="${isPlaying ? "Pause" : "Play"}">
                ${svgUse(isPlaying ? "i-pause" : "i-play")}
              </button>
            </div>
            <div class="card-badges">
              ${s.kind === "extended" ? '<span class="badge badge-extended">extended</span>' : ""}
              <span class="badge">${fmtDuration(s.duration_seconds)}</span>
            </div>
          </div>
          <div class="card-body">
            <div class="card-title" data-action="open-detail" data-id="${esc(s.id)}" title="${esc(s.title || s.prompt)}">
              ${esc(s.title || s.prompt?.slice(0, 60) || "Untitled")}
            </div>
            ${s.status === "error" && s.error
              ? `<div class="card-error">${esc(s.error)}</div>`
              : `<div class="card-prompt">${esc(s.prompt || "")}</div>`}
          </div>
          <div class="card-actions">
            <button class="btn btn-ghost btn-sm" data-action="regen" data-id="${esc(s.id)}" title="Regenerate">${svgUse("i-refresh")}<span class="visually-hidden">Regenerate</span></button>
            ${state.config?.supports_extend
              ? `<button class="btn btn-ghost btn-sm" data-action="extend" data-id="${esc(s.id)}" title="Extend">${svgUse("i-extend")}<span class="visually-hidden">Extend</span></button>` : ""}
            <button class="btn btn-ghost btn-sm" data-action="download-wav" data-id="${esc(s.id)}" title="Download WAV">${svgUse("i-download")}<span class="visually-hidden">Download WAV</span></button>
            <a class="btn btn-ghost btn-sm" href="/api/songs/${esc(s.id)}/mp3" download title="Download MP3">${svgUse("i-download")}<span class="visually-hidden">Download MP3</span></a>
            <button class="btn btn-danger btn-sm" data-action="delete" data-id="${esc(s.id)}" title="Delete">Delete</button>
          </div>
        </article>`;
      }).join("")}
    </div>`;
}

async function regenerate(id) {
  try {
    const res = await api(`/api/songs/${id}/regenerate`, { method: "POST" });
    trackGroup(res.job_group_id, "regenerate");
    toast("Regeneration started — 1 new variation");
    setTab("library");
  } catch (err) { toast(`Regenerate failed: ${err.message}`, "err"); }
}

function twoStepDelete(btn) {
  if (btn.dataset.confirming) {
    const id = btn.dataset.id;
    deleteSong(id);
    return;
  }
  btn.dataset.confirming = "1";
  btn.textContent = "Confirm?";
  btn.classList.add("btn-confirm");
  setTimeout(() => {
    if (!btn.isConnected) return;
    delete btn.dataset.confirming;
    btn.textContent = "Delete";
    btn.classList.remove("btn-confirm");
  }, 3200);
}

async function deleteSong(id) {
  try {
    await api(`/api/songs/${id}`, { method: "DELETE" });
    if (state.playingId === id) stopAudio();
    toast("Song deleted");
    await loadSongs();
    renderLibrary();
  } catch (err) { toast(`Delete failed: ${err.message}`, "err"); }
}

async function downloadFile(url, filename) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  } catch {
    window.open(url, "_blank");
  }
}

function songById(id) { return state.songs.find((s) => s.id === id); }

function downloadName(song, ext) {
  const base = (song.title || song.prompt || "song").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 60) || "song";
  return `${base}.${ext}`;
}

/* ============================================================
   detail modal
   ============================================================ */
const WAVE_BARS = 56;

function waveHeights(id) {
  let seed = 0;
  for (const c of id) seed = (seed * 33 + c.charCodeAt(0)) % 9973;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  return Array.from({ length: WAVE_BARS }, (_, i) => {
    const envelope = 0.35 + 0.65 * Math.abs(Math.sin((i / WAVE_BARS) * Math.PI * 3));
    return Math.max(8, Math.round((10 + rnd() * 90) * envelope));
  });
}

function renderLyrics(lyrics) {
  if (!lyrics || !lyrics.trim()) return `<p class="lyrics-empty">No lyrics — instrumental or pending.</p>`;
  return lyrics.split(/\r?\n/).map((line) => {
    const m = line.match(/^\s*\[(.+?)\]\s*$/);
    if (m) return `<span class="section-tag">${esc(m[1])}</span>`;
    if (!line.trim()) return "";
    return `<p>${esc(line)}</p>`;
  }).join("");
}

function openDetail(id) {
  const s = songById(id);
  if (!s) return;
  const playing = state.playingId === s.id;
  const heights = waveHeights(s.id);
  $("#modal-root").innerHTML = `
    <div class="modal-backdrop" data-action="close-modal">
      <div class="modal" role="dialog" aria-modal="true" aria-label="${esc(s.title || "Song details")}">
        <div class="modal-hero">
          ${coverMarkup(s)}
          <button class="modal-close" data-action="close-modal" aria-label="Close">${svgUse("i-x")}</button>
          <div class="modal-hero-fade"></div>
        </div>
        <div class="modal-body">
          <div class="modal-title-row">
            <h2>${esc(s.title || s.prompt?.slice(0, 80) || "Untitled")}</h2>
            ${s.kind === "extended" ? '<span class="badge badge-extended">extended</span>' : ""}
          </div>

          <div class="wave-player">
            <button class="wave-play" data-action="play" data-id="${esc(s.id)}" data-song-id="${esc(s.id)}" aria-label="Play">
              ${svgUse(playing ? "i-pause" : "i-play")}
            </button>
            <div class="waveform" id="waveform" data-song-id="${esc(s.id)}">
              ${heights.map((h) => `<span style="height:${h}%"></span>`).join("")}
            </div>
            <span class="wave-time" id="wave-time">0:00 / ${fmtDuration(s.duration_seconds)}</span>
          </div>

          <div class="meta-row">
            <span>Model <b>${esc(s.model || "—")}</b></span>
            <span>Seed <b>${s.seed ?? "—"}</b></span>
            <span>Duration <b>${fmtDuration(s.duration_seconds)}</b></span>
            <span>Created <b>${fmtDate(s.created_at)}</b></span>
          </div>
          ${s.status === "error" && s.error ? `<div class="card-error">${esc(s.error)}</div>` : ""}

          <div>
            <div class="field-label">Lyrics</div>
            <div class="lyrics-block">${renderLyrics(s.lyrics)}</div>
          </div>

          <div class="modal-actions">
            <button class="btn" data-action="download-wav" data-id="${esc(s.id)}">${svgUse("i-download")} Download WAV</button>
            <button class="btn" data-action="download-flac" data-id="${esc(s.id)}">${svgUse("i-download")} Download FLAC</button>
            <a class="btn" href="/api/songs/${esc(s.id)}/mp3" download title="Download MP3">${svgUse("i-download")} Download MP3</a>
            <button class="btn btn-ghost" data-action="regen" data-id="${esc(s.id)}">${svgUse("i-refresh")} Regenerate</button>
            ${state.config?.supports_extend
              ? `<button class="btn btn-ghost" data-action="extend" data-id="${esc(s.id)}">${svgUse("i-extend")} Extend</button>` : ""}
          </div>
        </div>
      </div>
    </div>`;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  $("#modal-root").innerHTML = "";
  document.body.style.overflow = "";
}

/* audio -> waveform */
state.audio.addEventListener("timeupdate", () => {
  const wf = $("#waveform");
  if (!wf || state.playingId !== wf.dataset.songId) return;
  const dur = state.audio.duration || 1;
  const played = state.audio.currentTime / dur;
  const bars = wf.children;
  const upto = Math.round(played * bars.length);
  for (let i = 0; i < bars.length; i++) bars[i].classList.toggle("played", i < upto);
  const t = $("#wave-time");
  if (t) t.textContent = `${fmtDuration(state.audio.currentTime)} / ${fmtDuration(dur)}`;
});

/* ============================================================
   extend modal
   ============================================================ */
function openExtend(id) {
  const s = songById(id);
  if (!s) return;
  state.extendSongId = id;
  const cur = s.duration_seconds || 60;
  const def = Math.min(240, cur + 30);
  $("#modal-root").innerHTML = `
    <div class="modal-backdrop" data-action="close-modal">
      <div class="modal" role="dialog" aria-modal="true" style="width:min(460px,100%)">
        <div class="modal-body">
          <div class="modal-title-row"><h2>Extend song</h2></div>
          <p style="margin:0;color:var(--text-dim);font-size:var(--fs-sm)">
            Creates a new longer variation of “${esc(s.title || s.prompt?.slice(0, 40) || "Untitled")}”.
          </p>
          <div class="control-block duration-block">
            <span class="field-label">New duration <span class="duration-value" id="extend-value">${def}s</span></span>
            <div class="slider-wrap">
              <input type="range" id="extend-slider" class="slider" min="15" max="240" step="5" value="${def}" style="--fill:${((def - 15) / 225).toFixed(4)}">
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn btn-primary" data-action="extend-confirm">${svgUse("i-extend")} Extend</button>
            <button class="btn btn-ghost" data-action="close-modal">Cancel</button>
          </div>
        </div>
      </div>
    </div>`;
}

async function confirmExtend() {
  const id = state.extendSongId;
  const val = parseInt($("#extend-slider")?.value || "0", 10);
  if (!id || !val) return;
  try {
    const res = await api(`/api/songs/${id}/extend`, {
      method: "POST",
      body: JSON.stringify({ duration_seconds: val }),
    });
    closeModal();
    trackGroup(res.job_group_id, "extend");
    toast("Extension started — a longer variation is queued");
    setTab("library");
  } catch (err) { toast(`Extend failed: ${err.message}`, "err"); }
}

/* ============================================================
   SETTINGS view
   ============================================================ */
async function fetchHealth() {
  state.health = await api("/api/health");
}

function healthRow(name, h) {
  const up = !!h?.up;
  const err = h?.error;
  return `
    <div class="health-row">
      <span class="health-dot ${up ? "up" : "down"}" title="${up ? "healthy" : "unreachable"}"></span>
      <div>
        <div class="health-name">${esc(name)} <span class="health-meta">${up ? "online" : "offline"}</span></div>
        ${err ? `<div class="health-error">${esc(err)}</div>` : ""}
        ${!up && !err ? '<div class="health-error">Unreachable — check the endpoint URL.</div>' : ""}
        ${h?.models?.length ? `<div class="health-meta">${h.models.length} model${h.models.length === 1 ? "" : "s"}: ${esc(h.models.slice(0, 4).join(", "))}${h.models.length > 4 ? "…" : ""}</div>` : ""}
      </div>
    </div>`;
}

function renderSettings() {
  const view = $("#view-settings");
  const c = state.config;
  view.innerHTML = `
    <div class="view-head">
      <h1>Settings</h1>
      <p>Local generation endpoints and model configuration. These are served by the Songsmith backend.</p>
    </div>
    <div class="settings-grid">
      <div class="settings-card">
        <h3>Endpoints</h3>
        <dl class="kv-grid">
          <dt>localai</dt><dd>${esc(c?.endpoints?.localai || "—")}</dd>
          <dt>llm</dt><dd>${esc(c?.endpoints?.llm || "—")}</dd>
        </dl>
      </div>
      <div class="settings-card">
        <h3>Models</h3>
        <dl class="kv-grid">
          <dt>Music</dt><dd>${esc(c?.music_model || "—")}</dd>
          <dt>Cover art</dt><dd>${esc(c?.image_model || "—")}</dd>
          <dt>Lyricist</dt><dd>${esc(c?.llm_model || "—")}</dd>
          <dt>Extend support</dt><dd>${c?.supports_extend ? "yes" : "no"}</dd>
        </dl>
      </div>
      <div class="settings-card">
        <div class="settings-toolbar">
          <button class="btn btn-sm" data-action="refresh-health" ${state._healthBusy ? "disabled" : ""}>
            ${state._healthBusy ? '<span class="spinner"></span> Checking…' : `${svgUse("i-refresh")} Refresh`}
          </button>
        </div>
        ${state.health
          ? healthRow("localai", state.health.localai) + healthRow("llm", state.health.llm)
          : '<div class="health-meta">Loading health status…</div>'}
      </div>
    </div>`;
  renderNavHealth();
}

function renderNavHealth() {
  const el = $("#nav-health");
  if (!el) return;
  const h = state.health;
  if (!h) { el.innerHTML = '<span class="health-dot down"></span> checking'; return; }
  const up = h.localai?.up && h.llm?.up;
  el.innerHTML = `<span class="health-dot ${up ? "up" : "down"}"></span> ${up ? "endpoints healthy" : "endpoint issues"}`;
}

async function refreshHealth(manual = true) {
  state._healthBusy = true;
  if (state.tab === "settings") renderSettings();
  try {
    await fetchHealth();
    if (manual) toast("Health refreshed");
  } catch { if (manual) toast("Could not reach health endpoint", "err"); }
  state._healthBusy = false;
  if (state.tab === "settings") renderSettings();
}

/* ============================================================
   events
   ============================================================ */
document.addEventListener("click", (e) => {
  const navBtn = e.target.closest("[data-nav]");
  if (navBtn) { setTab(navBtn.dataset.nav); return; }
  const jump = e.target.closest("[data-nav-jump]");
  if (jump) { setTab(jump.dataset.navJump); return; }

  const chip = e.target.closest("[data-chip]");
  if (chip) {
    const c = chip.dataset.chip;
    const input = $("#prompt-input");
    if (input) state.form.prompt = input.value;
    if (state.chipsActive.has(c)) state.chipsActive.delete(c);
    else state.chipsActive.add(c);
    // reflect chips into the prompt text
    const base = state.form.prompt.split(/,\s*/).filter((w) => !STYLE_CHIPS.includes(w.trim())).join(", ");
    state.form.prompt = [base, ...state.chipsActive].filter(Boolean).join(", ");
    renderCreate();
    return;
  }

  const mark = e.target.closest("[data-mark]");
  if (mark) { updateDurationUI(parseInt(mark.dataset.mark, 10)); return; }

  const t = e.target.closest("[data-action]");
  if (!t) return;
  const action = t.dataset.action;
  const id = t.dataset.id;

  switch (action) {
    case "toggle-lyrics": {
      const c = $("#lyrics-collapsible");
      state.lyricsOpen = !c.classList.contains("open");
      c.classList.toggle("open", state.lyricsOpen);
      if (state.lyricsOpen) $("#lyrics-input")?.focus();
      break;
    }
    case "write-lyrics": writeLyrics(); break;
    case "generate": generate(); break;
    case "play": {
      const s = songById(id);
      if (s) togglePlay(s);
      break;
    }
    case "open-detail": openDetail(id); break;
    case "close-modal": {
      if (t.classList.contains("modal-backdrop")) {
        if (e.target === t) closeModal(); // direct backdrop click only
      } else {
        closeModal(); // explicit close / cancel buttons
      }
      break;
    }
    case "regen": regenerate(id); break;
    case "extend": openExtend(id); break;
    case "extend-confirm": confirmExtend(); break;
    case "download-wav": {
      const s = songById(id);
      if (s?.audio_url) downloadFile(s.audio_url, downloadName(s, s.audio_url.endsWith(".flac") ? "flac" : "wav"));
      break;
    }
    case "download-flac": {
      const s = songById(id);
      if (s?.audio_url) downloadFile(s.audio_url.replace(/\.wav$/, ".flac"), downloadName(s, "flac"));
      break;
    }
    case "delete": twoStepDelete(t); break;
    case "refresh-health": refreshHealth(true); break;
  }
});

/* waveform seek */
document.addEventListener("click", (e) => {
  const wf = e.target.closest("#waveform");
  if (!wf || !state.audio.src) return;
  const rect = wf.getBoundingClientRect();
  const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
  state.audio.currentTime = pct * (state.audio.duration || 0);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $("#modal-root").children.length) closeModal();
  if (e.key === " " && state.playingId && !/input|textarea/i.test(e.target.tagName)) {
    e.preventDefault();
    const s = songById(state.playingId);
    if (s) togglePlay(s);
  }
});

document.addEventListener("input", (e) => {
  if (e.target.id === "duration-slider") updateDurationUI(parseInt(e.target.value, 10));
  if (e.target.id === "prompt-input") state.form.prompt = e.target.value;
  if (e.target.id === "lyrics-input") state.form.lyrics = e.target.value;
  if (e.target.id === "extend-slider") {
    const v = parseInt(e.target.value, 10);
    $("#extend-value").textContent = `${v}s`;
    e.target.style.setProperty("--fill", String((v - 15) / 225));
  }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "instrumental-toggle") state.form.instrumental = e.target.checked;
});

/* ============================================================
   boot
   ============================================================ */
async function boot() {
  setTab("create");
  const [config, songs, active] = await Promise.allSettled([
    api("/api/config"),
    api("/api/songs"),
    api("/api/jobs/active"),
  ]);
  if (config.status === "fulfilled") state.config = config.value;
  if (songs.status === "fulfilled") state.songs = songs.value;
  if (active.status === "fulfilled") {
    const groups = new Map();
    for (const j of active.value) {
      if (!groups.has(j.job_group_id)) groups.set(j.job_group_id, { type: j.type, startedAt: j.created_at });
    }
    for (const [gid, g] of groups) state.activeGroups.set(gid, { jobs: [], ...g });
    if (groups.size) {
      toast("Generation in progress — restored from the last session");
    }
  }
  renderCreate();
  renderLibrary();
  renderProgress();
  refreshHealth(false);

  await pollTick();
  setInterval(pollTick, 2000);
}

boot();
