/* ============================================================
   Songsmith — app.js
   Vanilla JS SPA. Served from server/static/, talks to the
   FastAPI backend on the same origin.
   ============================================================ */
(function () {
  "use strict";

  /* ---------------- helpers ---------------- */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtDur = (s) => {
    const n = Math.max(0, Math.round(Number(s) || 0));
    return Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");
  };
  const fmtBytes = (b) => {
    if (b == null || isNaN(b)) return "";
    if (b > 1048576) return (b / 1048576).toFixed(1) + " MB";
    if (b > 1024) return Math.round(b / 1024) + " KB";
    return b + " B";
  };
  const fileUrl = (p) => {
    if (!p) return "";
    return "/" + String(p).replace(/^\.?\//, "").replace(/^\/+/, "");
  };
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  const api = {
    async json(res) {
      const text = await res.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { /* non-JSON */ }
      if (!res.ok) {
        const detail = data && (data.detail || data.error || data.message);
        throw new Error(detail ? (typeof detail === "string" ? detail : JSON.stringify(detail)) : "HTTP " + res.status);
      }
      return data;
    },
    get(path) { return fetch(path).then((r) => this.json(r)); },
    send(path, method, body) {
      return fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      }).then((r) => this.json(r));
    },
  };

  /* ---------------- toast ---------------- */
  const TICK_OK = '<svg class="tico" viewBox="0 0 24 24" fill="none"><path d="m5 13 4 4L19 7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const TICK_ERR = '<svg class="tico" viewBox="0 0 24 24" fill="none"><path d="M12 8v5m0 3.5v.01" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.8"/></svg>';

  function toast(msg, type, ms) {
    const t = el("div", "toast " + (type || "ok"));
    t.innerHTML = (type === "err" ? TICK_ERR : TICK_OK) + "<span>" + esc(msg) + "</span>";
    $("#toastRoot").appendChild(t);
    setTimeout(() => {
      t.classList.add("leaving");
      setTimeout(() => t.remove(), 260);
    }, ms || 3400);
  }

  /* ---------------- state ---------------- */
  const state = {
    route: "create",
    config: null,
    songs: [],
    activeGroup: null,   // job_group_id currently being watched
    activeJobs: [],      // last known job rows for that group
    pollTimer: null,
    activeJobCount: 0,
  };

  const supportsExtend = () => !!(state.config && state.config.supports_extend);

  /* ---------------- routing ---------------- */
  const VIEWS = { create: "#viewCreate", progress: "#viewProgress", library: "#viewLibrary", settings: "#viewSettings" };
  const TABS = { create: "#tabCreate", library: "#tabLibrary", settings: "#tabSettings" };

  function show(route, opts) {
    if (route === "progress" && !state.activeGroup && !opts) route = "library";
    state.route = route;
    Object.entries(VIEWS).forEach(([k, sel]) => { $(sel).hidden = k !== route; });
    Object.entries(TABS).forEach(([k, sel]) => {
      const b = $(sel);
      if (b) b.setAttribute("aria-selected", k === route ? "true" : "false");
    });
    try { localStorage.setItem("ss_route", route); } catch (_) {}
    window.scrollTo({ top: 0 });
  }

  $("#tabCreate").addEventListener("click", () => show("create"));
  $("#tabLibrary").addEventListener("click", () => { refreshLibrary(); show("library"); });
  $("#tabSettings").addEventListener("click", () => { refreshSettings(); show("settings"); });
  $("#brandLink").addEventListener("click", (e) => { e.preventDefault(); show("create"); });
  $("#emptyCreateBtn").addEventListener("click", () => show("create"));
  $("#libraryRefresh").addEventListener("click", () => refreshLibrary());
  $("#healthRefreshTop").addEventListener("click", () => refreshHealth(true));

  /* ---------------- create screen ---------------- */
  const PRESETS = [
    { tag: "synth-pop" }, { tag: "lo-fi" }, { tag: "funk rock" }, { tag: "dream pop" },
    { tag: "synthwave" }, { tag: "jazz" }, { tag: "orchestral" }, { tag: "trap" },
    { tag: "acoustic folk" }, { tag: "city pop" },
  ];
  const DURATIONS = [15, 30, 60, 120];
  const chipRow = $("#styleChips");
  const selectedTags = new Set();

  PRESETS.forEach((p) => {
    const b = el("button", "chip");
    b.type = "button";
    b.textContent = p.tag;
    b.setAttribute("aria-pressed", "false");
    b.dataset.tag = p.tag;
    b.addEventListener("click", () => {
      const on = b.getAttribute("aria-pressed") === "true";
      b.setAttribute("aria-pressed", on ? "false" : "true");
      if (on) selectedTags.delete(p.tag);
      else selectedTags.add(p.tag);
    });
    chipRow.appendChild(b);
  });

  const promptInput = $("#promptInput");
  promptInput.addEventListener("input", () => { $("#promptCount").textContent = promptInput.value.length + " / 2000"; });

  const lyricsToggle = $("#lyricsToggle");
  const lyricsPanel = $("#lyricsPanel");
  lyricsToggle.addEventListener("click", () => {
    const open = lyricsToggle.getAttribute("aria-expanded") === "true";
    lyricsToggle.setAttribute("aria-expanded", String(!open));
    lyricsPanel.hidden = open;
  });

  $("#writeLyricsBtn").addEventListener("click", async () => {
    const btn = $("#writeLyricsBtn");
    const label = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spark" aria-hidden="true">✨</span> Writing…';
    try {
      const data = await api.send("/api/lyrics", "POST", { prompt: promptInput.value || "an uplifting synth-pop song" });
      const lyrics = data && (data.lyrics || data.text || "");
      if (lyrics) {
        $("#lyricsInput").value = String(lyrics).slice(0, 6000);
        if (lyricsPanel.hidden) lyricsToggle.click();
        toast("Lyrics drafted");
      } else toast("No lyrics returned", "err");
    } catch (err) { toast("Lyrics failed: " + err.message, "err"); }
    btn.disabled = false;
    btn.innerHTML = label;
  });

  const instToggle = $("#instrumentalToggle");
  instToggle.addEventListener("click", () => {
    instToggle.setAttribute("aria-checked", instToggle.getAttribute("aria-checked") === "true" ? "false" : "true");
  });

  const durSlider = $("#durationSlider");
  function paintRange() {
    const pct = (durSlider.value / (DURATIONS.length - 1)) * 100;
    durSlider.style.setProperty("--fill", pct + "%");
    $("#durationReadout").textContent = DURATIONS[durSlider.value] + "s";
  }
  durSlider.addEventListener("input", paintRange);
  paintRange();

  function collectCreate() {
    return {
      prompt: promptInput.value.trim(),
      lyrics: $("#lyricsInput").value.trim() || null,
      tags: Array.from(selectedTags),
      instrumental: instToggle.getAttribute("aria-checked") === "true",
      duration_seconds: DURATIONS[Number(durSlider.value)],
    };
  }

  $("#generateBtn").addEventListener("click", async () => {
    const body = collectCreate();
    if (!body.prompt) { toast("Describe your song first", "err"); promptInput.focus(); return; }
    const btn = $("#generateBtn");
    btn.disabled = true;
    $("#generateLabel").textContent = "Starting…";
    try {
      const res = await api.send("/api/songs", "POST", body);
      const gid = res && res.job_group_id;
      if (!gid) throw new Error("no job_group_id in response");
      state.activeGroup = gid;
      state.activeJobs = [];
      renderProgress();
      show("progress", true);
      startPolling();
    } catch (err) {
      toast("Generate failed: " + err.message, "err");
    }
    btn.disabled = false;
    $("#generateLabel").textContent = "Generate";
  });

  /* ---------------- progress screen ---------------- */
  const STAGES = [
    { key: "writing lyrics", label: "Writing lyrics" },
    { key: "naming song", label: "Naming your song" },
    { key: "generating music", label: "Generating music" },
    { key: "generating cover art", label: "Painting cover art" },
  ];
  const JOB_STAGES = ["queued", "writing_lyrics", "naming_song", "generating_music", "generating_cover", "complete"];
  function stageFromJob(job) {
    const s = String((job && (job.stage || job.status)) || "queued").toLowerCase().replace(/[\s-]+/g, "_");
    const i = JOB_STAGES.indexOf(s);
    if (i < 0) return 1;
    return i;
  }

  const miniWave = (n, dur) => {
    let h = "";
    for (let i = 0; i < n; i++) {
      const d = (0.7 + Math.random() * 0.65).toFixed(2);
      h += '<i style="height:' + Math.round(10 + Math.random() * 34) + 'px;animation-delay:' + (Math.random() * -1.1).toFixed(2) + 's;animation-duration:' + d + 's"></i>';
    }
    return '<div class="wave-mini">' + h + "</div>";
  };

  function renderProgress() {
    const grid = $("#progressGrid");
    grid.innerHTML = "";
    let jobs = state.activeJobs && state.activeJobs.length ? state.activeJobs.slice(0, 2) : null;
    if (!jobs) {
      jobs = [0, 1].map(() => ({ id: null, stage: "queued" }));
      if (!state.activeGroup) return;
    }
    jobs.forEach((job, idx) => {
      const done = job && (String(job.status || "").toLowerCase() === "complete" || String(job.status || "").toLowerCase() === "completed");
      const failed = job && ["failed", "error", "cancelled"].includes(String(job.status || "").toLowerCase());
      const stageIdx = clamp(stageFromJob(job), 0, STAGES.length - 1);
      const card = el("div", "glass card skeleton-card");
      card.dataset.odId = "progress-card-" + (idx + 1);
      let statusLabel, subLabel, pct;
      if (done) {
        statusLabel = "Complete";
        subLabel = "Saved to Library";
        pct = 100;
      } else if (failed) {
        statusLabel = "Failed";
        subLabel = job.error || job.message || "Something went wrong";
        pct = 100;
      } else {
        statusLabel = STAGES[stageIdx].label;
        subLabel = "variation " + (idx + 1) + " · step " + (stageIdx + 1) + " / " + STAGES.length;
        pct = Math.round(((stageIdx + 0.35) / STAGES.length) * 100);
      }
      card.innerHTML =
        '<div class="skeleton-cover">' + miniWave(14) + "</div>" +
        '<div class="skeleton-body">' +
          (done ? "" : '<div class="skeleton-line" style="width:72%"></div><div class="skeleton-line" style="width:46%; margin-bottom:16px"></div>') +
          '<div class="progress-card-status"><span class="status-dot" data-state="' + (failed ? "error" : done ? "ok" : "busy") + '"></span>' +
          '<div><div class="progress-status-text">' + esc(statusLabel) + "</div>" +
          '<div class="progress-sub">' + esc(subLabel) + "</div></div></div>" +
          '<div class="progress-track"><div class="progress-bar" style="width:' + pct + '%"></div></div>' +
        "</div>";
      grid.appendChild(card);
    });
  }

  $("#cancelPollBtn").addEventListener("click", () => {
    stopPolling();
    refreshLibrary();
    show("library");
    toast("You can keep browsing — it stays in Library");
  });

  function startPolling() {
    stopPolling();
    pollJobs();
    state.pollTimer = setInterval(pollJobs, 2500);
  }
  function stopPolling() {
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  }

  async function pollJobs() {
    const gid = state.activeGroup;
    if (!gid) { stopPolling(); return; }
    try {
      const data = await api.get("/api/jobs?group=" + encodeURIComponent(gid));
      const rows = Array.isArray(data) ? data : (data && (data.jobs || data.songs || data.items)) || [];
      state.activeJobs = rows;
      renderProgress();
      const allDone = rows.length > 0 && rows.every((j) => ["complete", "completed", "failed", "error", "cancelled"].includes(String(j.status || "").toLowerCase()));
      if (allDone) {
        state.activeGroup = null;
        state.activeJobs = [];
        stopPolling();
        await refreshLibrary();
        show("library");
        toast("Your songs are ready");
      }
    } catch (_) { /* transient — keep polling */ }
  }

  /* ---------------- library ---------------- */
  const ACT_ICONS = {
    regen: '<svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    extend: '<svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    dl: '<svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M4 19h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    del: '<svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V5h6v2m-8 0 .7 12a1.5 1.5 0 0 0 1.5 1.4h3.6a1.5 1.5 0 0 0 1.5-1.4L17 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function songCoverUrl(s) {
    if (s.cover_url) return fileUrl(s.cover_url);
    if (s.cover_path) return fileUrl(s.cover_path);
    if (s.id) return "/files/covers/" + s.id + ".png";
    return "";
  }
  function songAudioUrl(s) {
    if (s.audio_url) return fileUrl(s.audio_url);
    if (s.audio_path) return fileUrl(s.audio_path);
    if (s.id) return "/files/audio/" + s.id + ".wav";
    return "";
  }

  function renderLibrary() {
    const grid = $("#songGrid");
    const empty = $("#libraryEmpty");
    const list = state.songs;
    $("#libraryCount").textContent = list.length;
    $("#libraryCount").hidden = list.length === 0;
    $("#libraryMeta").textContent = list.length
      ? list.length + " track" + (list.length > 1 ? "s" : "") + " · newest first"
      : "Your generated tracks, newest first.";
    empty.hidden = list.length > 0;
    grid.innerHTML = "";
    list.forEach((s) => {
      const id = s.id;
      const cover = songCoverUrl(s);
      const card = el("article", "glass song-card");
      card.dataset.odId = "song-card-" + id;
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", "Open " + (s.title || "song"));

      const coverDiv = el("div", "song-cover");
      coverDiv.innerHTML =
        (cover
          ? '<img loading="lazy" src="' + esc(cover) + '" alt="" width="300" height="300" onerror="this.style.display=\'none\'">'
          : "") +
        '<div class="cover-fallback"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" opacity=".5"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="2.4" fill="currentColor"/></svg></div>' +
        '<span class="song-duration">' + esc(fmtDur(s.duration_seconds)) + "</span>" +
        '<div class="play-overlay"><button class="play-btn" data-play="' + esc(id) + '" aria-label="Play ' + esc(s.title || "song") + '">' +
          '<svg class="ico play-ico" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg></button></div>';

      const titleBlock = el("div", "song-title-block");
      const tags = Array.isArray(s.tags) ? s.tags.slice(0, 3) : [];
      titleBlock.innerHTML =
        '<div class="song-title">' + esc(s.title || "Untitled") + "</div>" +
        (tags.length || s.instrumental ? '<div class="song-tags">' + tags.map((t) => '<span class="song-tag">' + esc(t) + "</span>").join("") + (s.instrumental ? '<span class="song-tag">instrumental</span>' : "") + "</div>" : "");

      const actions = el("div", "song-actions");
      actions.innerHTML =
        '<button class="song-action" data-act="regen" data-id="' + esc(id) + '" title="Regenerate">' + ACT_ICONS.regen + "<span>Regen</span></button>" +
        (supportsExtend() ? '<button class="song-action" data-act="extend" data-id="' + esc(id) + '" title="Extend">' + ACT_ICONS.extend + "<span>Extend</span></button>" : "") +
        '<a class="song-action" data-act="dl" data-id="' + esc(id) + '" href="' + esc(songAudioUrl(s)) + '" download title="Download">' + ACT_ICONS.dl + "<span>Save</span></a>" +
        '<button class="song-action danger" data-act="del" data-id="' + esc(id) + '" title="Delete">' + ACT_ICONS.del + "<span>Delete</span></button>";

      card.appendChild(coverDiv);
      card.appendChild(titleBlock);
      card.appendChild(actions);
      grid.appendChild(card);
    });
  }

  async function refreshLibrary() {
    try {
      const data = await api.get("/api/songs");
      state.songs = Array.isArray(data) ? data : (data && (data.songs || data.items)) || [];
      renderLibrary();
    } catch (err) {
      toast("Couldn't load library: " + err.message, "err");
    }
  }

  $("#songGrid").addEventListener("click", async (e) => {
    const playBtn = e.target.closest("[data-play]");
    const actBtn = e.target.closest("[data-act]");
    if (playBtn) {
      const s = state.songs.find((x) => String(x.id) === playBtn.dataset.play);
      if (s) openModal(s, true);
      return;
    }
    if (actBtn) {
      const id = actBtn.dataset.id;
      if (actBtn.dataset.act === "dl") return; // native download link
      if (actBtn.dataset.act === "regen") return regenerateSong(id, actBtn);
      if (actBtn.dataset.act === "extend") return extendSong(id, actBtn);
      if (actBtn.dataset.act === "del") return deleteSong(id, actBtn);
      return;
    }
    const card = e.target.closest(".song-card");
    if (card) {
      const s = state.songs.find((x) => String(x.id) === String(card.dataset.odId).replace("song-card-", ""));
      if (s) openModal(s, false);
    }
  });

  async function deleteSong(id, btn) {
    if (btn) { btn.disabled = true; }
    const song = state.songs.find((s) => String(s.id) === String(id));
    const name = song && song.title ? '"' + song.title + '"' : "this song";
    if (!confirm("Delete " + name + "? This can't be undone.")) { if (btn) btn.disabled = false; return; }
    try {
      await api.send("/api/songs/" + encodeURIComponent(id), "DELETE");
      state.songs = state.songs.filter((s) => String(s.id) !== String(id));
      renderLibrary();
      toast("Deleted");
    } catch (err) { toast("Delete failed: " + err.message, "err"); }
    if (btn) btn.disabled = false;
  }

  async function regenerateSong(id, btn) {
    if (btn) btn.disabled = true;
    try {
      const res = await api.send("/api/songs/" + encodeURIComponent(id) + "/regenerate", "POST", {});
      state.activeGroup = (res && res.job_group_id) || null;
      state.activeJobs = [];
      renderProgress();
      show("progress", true);
      startPolling();
      toast("Regenerating — 2 new variations");
    } catch (err) { toast("Regenerate failed: " + err.message, "err"); }
    if (btn) btn.disabled = false;
  }

  async function extendSong(id, btn) {
    if (btn) btn.disabled = true;
    try {
      await api.send("/api/songs/" + encodeURIComponent(id) + "/extend", "POST", {});
      toast("Extending song…");
      setTimeout(refreshLibrary, 1200);
    } catch (err) { toast("Extend failed: " + err.message, "err"); }
    if (btn) btn.disabled = false;
  }

  /* ---------------- modal / player ---------------- */
  const modal = $("#songModal");
  const audio = $("#modalAudio");
  const waveEl = $("#modalWave");
  let waveBars = [];
  let lastSongId = null;

  function buildWave() {
    waveEl.innerHTML = "";
    waveBars = [];
    const n = Math.max(24, Math.min(64, Math.floor(waveEl.clientWidth / 7)));
    for (let i = 0; i < n; i++) {
      const b = document.createElement("i");
      b.style.height = Math.round(8 + Math.abs(Math.sin(i * 0.55)) * 30 + Math.random() * 8) + "px";
      waveEl.appendChild(b);
      waveBars.push(b);
    }
  }

  function paintWave() {
    if (!audio.duration || !isFinite(audio.duration)) return;
    const frac = clamp(audio.currentTime / audio.duration, 0, 1);
    const active = Math.floor(frac * waveBars.length);
    waveBars.forEach((b, i) => b.classList.toggle("played", i <= active));
    $("#modalTime").textContent = fmtDur(audio.currentTime) + " / " + fmtDur(audio.duration);
  }

  function setPlayIcon(playing) {
    $("#modalPlay .play-ico").style.display = playing ? "none" : "";
    $("#modalPlay .pause-ico").style.display = playing ? "" : "none";
    $("#modalPlay").setAttribute("aria-label", playing ? "Pause" : "Play");
  }

  function lyricsHtml(raw) {
    if (!raw || !String(raw).trim()) return '<p class="field-hint">No lyrics for this track.</p>';
    const lines = String(raw).split(/\r?\n/);
    let out = "";
    for (const lnRaw of lines) {
      const ln = lnRaw.trim();
      if (!ln) { out += '<div class="lyrics-line empty"></div>'; continue; }
      const m = ln.match(/^\[([^\]]+)\]$/);
      if (m) out += '<div class="lyrics-section">' + esc(m[1]) + "</div>";
      else out += '<div class="lyrics-line">' + esc(ln) + "</div>";
    }
    return out;
  }

  function openModal(song, autoplay) {
    lastSongId = song.id;
    const cover = songCoverUrl(song);
    const audioUrl = songAudioUrl(song);
    $("#modalCover").src = cover || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='360' height='360'%3E%3Crect width='360' height='360' fill='%23191922'/%3E%3C/svg%3E";
    $("#modalTitle").textContent = song.title || "Untitled";
    $("#modalPrompt").textContent = song.prompt || "";
    $("#modalPrompt").hidden = !song.prompt;

    // meta pills
    const meta = $("#modalMeta");
    meta.innerHTML = "";
    const pills = [];
    if (song.model) pills.push(["model", song.model]);
    if (song.seed != null) pills.push(["seed", String(song.seed)]);
    if (song.duration_seconds != null) pills.push(["duration", fmtDur(song.duration_seconds)]);
    if (song.created_at) pills.push(["created", String(song.created_at).slice(0, 10)]);
    pills.forEach(([k, v]) => {
      meta.insertAdjacentHTML("beforeend", '<span class="meta-pill">' + esc(k) + ' <b>' + esc(v) + "</b></span>");
    });

    $("#modalLyrics").innerHTML = lyricsHtml(song.lyrics);

    const ext = (audioUrl || "").split(".").pop().toLowerCase();
    $("#dlWav").href = ext === "mp3" ? "" : audioUrl;
    $("#dlWav").hidden = ext === "mp3";
    $("#dlMp3").href = ext === "mp3" ? audioUrl : audioUrl.replace(/\.wav$/i, ".mp3");
    $("#modalExtend").hidden = !supportsExtend();
    $("#modalExtend").disabled = !supportsExtend();

    audio.src = audioUrl;
    setPlayIcon(false);
    $("#modalTime").textContent = "0:00" + (song.duration_seconds ? " / " + fmtDur(song.duration_seconds) : "");

    modal.hidden = false;
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => { buildWave(); if (waveBars.length) paintWave(); });
    if (autoplay && audioUrl) {
      audio.play().then(() => setPlayIcon(true)).catch(() => {});
    }
  }

  function closeModal() {
    audio.pause();
    modal.hidden = true;
    document.body.style.overflow = "";
  }

  $("#modalClose").addEventListener("click", closeModal);
  $("#modalBackdrop").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) closeModal(); });

  $("#modalPlay").addEventListener("click", () => {
    if (!audio.src) return;
    if (audio.paused) audio.play().then(() => setPlayIcon(true)).catch(() => {});
    else { audio.pause(); setPlayIcon(false); }
  });
  audio.addEventListener("timeupdate", paintWave);
  audio.addEventListener("play", () => setPlayIcon(true));
  audio.addEventListener("pause", () => setPlayIcon(false));
  audio.addEventListener("ended", () => { setPlayIcon(false); paintWave(); });

  $("#modalRegen").addEventListener("click", async () => {
    if (!lastSongId) return;
    const btn = $("#modalRegen");
    btn.disabled = true;
    await regenerateSong(lastSongId, null).catch(() => {});
    btn.disabled = false;
    closeModal();
  });
  $("#modalExtend").addEventListener("click", async () => {
    if (!lastSongId) return;
    const btn = $("#modalExtend");
    btn.disabled = true;
    await extendSong(lastSongId, null).catch(() => {});
    btn.disabled = false;
  });

  /* ---------------- settings ---------------- */
  function setDot(dotEl, txtEl, stateName, errText) {
    dotEl.dataset.state = stateName;
    if (txtEl) {
      txtEl.hidden = !errText;
      txtEl.textContent = errText || "";
    }
  }

  async function refreshHealth(notify) {
    ["#healthDotApi", "#healthDotMusic", "#healthDotLlm", "#miniDot"].forEach((s) => { const d = $(s); if (d) d.dataset.state = "busy"; });
    $("#healthMiniText").textContent = "Checking…";
    $("#healthMiniErr").hidden = true;
    try {
      const h = await api.get("/api/health");
      applyHealth(h);
      if (notify) toast("Health check complete");
    } catch (err) {
      setDot($("#healthDotApi"), $("#healthErrApi"), "error", err.message);
      setDot($("#healthDotMusic"), $("#healthErrMusic"), "error", "unreachable — API offline");
      setDot($("#healthDotLlm"), $("#healthErrLlm"), "error", "unreachable — API offline");
      setDot($("#miniDot"), null, "error", "");
      $("#healthMiniText").textContent = "API unreachable";
      $("#healthMiniErr").hidden = false;
      $("#healthMiniErr").textContent = err.message;
      $("#navHealthDot").dataset.state = "error";
      if (notify) toast("Health check failed", "err");
    }
  }

  function applyHealth(h) {
    const apiState = h && (h.status || h.state) ? "ok" : "ok";
    setDot($("#healthDotApi"), $("#healthErrApi"), "ok", "");
    $("#navHealthDot").dataset.state = "ok";
    $("#miniDot").dataset.state = "ok";
    $("#healthMiniText").textContent = "API online";

    let anyDown = false;
    const services = (h && (h.services || h.components)) || {};
    const music = services.music || services.localai || services.music_model || null;
    const llm = services.llm || services.llm_model || null;
    if (music && typeof music === "object") {
      const ok = music.ok !== false && music.status !== "down" && music.status !== "error";
      anyDown = anyDown || !ok;
      setDot($("#healthDotMusic"), $("#healthErrMusic"), ok ? "ok" : "error", ok ? "" : music.error || music.detail || music.message || "unreachable");
    } else setDot($("#healthDotMusic"), $("#healthErrMusic"), "ok", "");
    if (llm && typeof llm === "object") {
      const ok = llm.ok !== false && llm.status !== "down" && llm.status !== "error";
      anyDown = anyDown || !ok;
      setDot($("#healthDotLlm"), $("#healthErrLlm"), ok ? "ok" : "error", ok ? "" : llm.error || llm.detail || llm.message || "unreachable");
    } else setDot($("#healthDotLlm"), $("#healthErrLlm"), "ok", "");
    if (anyDown) $("#navHealthDot").dataset.state = "error";
    void apiState;
  }

  function applyConfig(cfg) {
    state.config = cfg || {};
    const c = state.config;
    const set = (sel, v) => { const n = $(sel); if (n) n.value = v == null ? "" : String(v); };
    set("#cfgLocalai", c.localai_url || c.music_url || c.localai_endpoint);
    set("#cfgLlm", c.llm_url || c.llm_endpoint);
    set("#cfgMusicModel", c.music_model || c.model);
    set("#cfgLlmModel", c.llm_model);
    set("#cfgCoverModel", c.cover_model);
    $("#healthMusicModel").textContent = c.music_model || "";
    $("#healthLlmModel").textContent = c.llm_model || "";
    $("#capExtend").textContent = supportsExtend() ? "yes" : "no";
    $("#capStereo").textContent = c.supports_stereo === false ? "no" : c.supports_stereo ? "yes" : "—";
    renderLibrary(); // re-render to update Extend visibility
  }

  async function refreshSettings() {
    try {
      const cfg = await api.get("/api/config");
      applyConfig(cfg);
    } catch (err) {
      $("#capExtend").textContent = "unknown";
      if (state.route === "settings") toast("Config unavailable: " + err.message, "err");
    }
    refreshHealth(false);
  }

  $("#settingsRefresh").addEventListener("click", () => refreshSettings());
  $("#healthRefresh").addEventListener("click", () => refreshHealth(true));

  /* ---------------- active job recovery ---------------- */
  async function recoverActive() {
    try {
      const data = await api.get("/api/jobs/active");
      const rows = Array.isArray(data) ? data : (data && (data.jobs || data.items)) || [];
      if (rows.length) {
        state.activeJobs = rows;
        state.activeGroup = (rows[0] && (rows[0].job_group_id || rows[0].group_id)) || state.activeGroup;
        if (state.activeGroup) {
          renderProgress();
          show("progress");
          startPolling();
          return true;
        }
      }
    } catch (_) { /* fine */ }
    return false;
  }

  /* ---------------- boot ---------------- */
  async function boot() {
    let route = "create";
    try { route = localStorage.getItem("ss_route") || "create"; } catch (_) {}
    show(route === "progress" ? "create" : route);

    // config + health fire-and-forget
    refreshSettings();
    // library
    await refreshLibrary();
    // recover in-flight jobs
    const recovered = await recoverActive();
    if (recovered) return;
    if (["create", "library", "settings"].includes(state.route)) refreshHealth(false);
  }

  boot();
})();
