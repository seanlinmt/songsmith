<script>
  import { songCoverUrl, songAudioUrl } from './songs.js';
  import { fmtDur, clamp } from './format.js';

  let { song = null, autoplay = false, supportsExtend = false, onRegen, onExtend, onClose } = $props();

  let audioEl = $state(null);
  let waveEl = $state(null);
  let playing = $state(false);
  let bars = $state([]);
  let cur = $state(0);
  let dur = $state(0);
  let timeText = $state('0:00');
  let regenBusy = $state(false);
  let extendBusy = $state(false);

  const COVER_FALLBACK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='360' height='360'%3E%3Crect width='360' height='360' fill='%23191922'/%3E%3C/svg%3E";

  const coverSrc = $derived(song ? songCoverUrl(song) || COVER_FALLBACK : '');
  const audioUrl = $derived(song ? songAudioUrl(song) : '');
  const ext = $derived((audioUrl || '').split('.').pop().toLowerCase());
  const dlWavHref = $derived(ext === 'mp3' ? '' : audioUrl);
  const dlWavHidden = $derived(ext === 'mp3');
  const dlMp3Href = $derived(ext === 'mp3' ? audioUrl : audioUrl.replace(/\.wav$/i, '.mp3'));

  const pills = $derived.by(() => {
    if (!song) return [];
    const p = [];
    if (song.model) p.push(['model', song.model]);
    if (song.seed != null) p.push(['seed', String(song.seed)]);
    if (song.duration_seconds != null) p.push(['duration', fmtDur(song.duration_seconds)]);
    if (song.created_at) p.push(['created', String(song.created_at).slice(0, 10)]);
    return p;
  });

  const lyricLines = $derived.by(() => {
    if (!song || !song.lyrics || !String(song.lyrics).trim()) return null;
    const out = [];
    for (const lnRaw of String(song.lyrics).split(/\r?\n/)) {
      const ln = lnRaw.trim();
      if (!ln) { out.push({ type: 'empty', text: '' }); continue; }
      const m = ln.match(/^\[([^\]]+)\]$/);
      if (m) out.push({ type: 'section', text: m[1] });
      else out.push({ type: 'line', text: ln });
    }
    return out;
  });

  const activeBar = $derived(dur ? Math.floor(clamp(cur / dur, 0, 1) * bars.length) : -1);

  function buildWave() {
    if (!waveEl) return;
    const n = clamp(Math.floor(waveEl.clientWidth / 7), 24, 64);
    const arr = [];
    for (let i = 0; i < n; i++) {
      arr.push(Math.round(8 + Math.abs(Math.sin(i * 0.55)) * 30 + Math.random() * 8));
    }
    bars = arr;
  }

  function paintWave() {
    if (!audioEl) return;
    if (!audioEl.duration || !isFinite(audioEl.duration)) return;
    cur = audioEl.currentTime;
    dur = audioEl.duration;
    timeText = fmtDur(audioEl.currentTime) + ' / ' + fmtDur(audioEl.duration);
  }

  function setPlayIcon(p) {
    playing = p;
  }

  function togglePlay() {
    if (!audioEl || !audioEl.src) return;
    if (audioEl.paused) audioEl.play().then(() => setPlayIcon(true)).catch(() => {});
    else { audioEl.pause(); setPlayIcon(false); }
  }

  async function regenClick() {
    if (!song) return;
    regenBusy = true;
    try { await onRegen(song.id); } catch (_) {}
    regenBusy = false;
    onClose();
  }

  async function extendClick() {
    if (!song) return;
    extendBusy = true;
    try { await onExtend(song.id); } catch (_) {}
    extendBusy = false;
  }

  /* body scroll lock while the modal is open */
  $effect(() => {
    document.body.style.overflow = song ? 'hidden' : '';
  });

  /* (re)load the player whenever a song is opened */
  $effect(() => {
    const s = song;
    if (!s || !audioEl) return;
    const url = songAudioUrl(s);
    audioEl.src = url;
    setPlayIcon(false);
    cur = 0;
    dur = 0;
    timeText = '0:00' + (s.duration_seconds ? ' / ' + fmtDur(s.duration_seconds) : '');
    requestAnimationFrame(() => { buildWave(); });
    if (autoplay && url) {
      audioEl.play().then(() => setPlayIcon(true)).catch(() => {});
    }
  });
</script>

<div class="modal-root" id="songModal" hidden={!song} data-od-id="song-modal">
  <div class="modal-backdrop" id="modalBackdrop" onclick={onClose}></div>
  <div class="modal glass-strong" role="dialog" aria-modal="true" aria-labelledby="modalTitle" data-od-id="song-modal-panel">
    <button class="icon-btn modal-close" id="modalClose" aria-label="Close" onclick={onClose}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
    <div class="modal-grid">
      <div class="modal-media">
        <img id="modalCover" class="modal-cover" alt="Song cover art" width="360" height="360" src={coverSrc} />
      </div>
      <div class="modal-body">
        <h2 class="modal-title" id="modalTitle">{song ? song.title || 'Untitled' : '—'}</h2>
        <p class="modal-prompt" id="modalPrompt" hidden={!song || !song.prompt}>{song ? song.prompt || '' : ''}</p>

        <div class="player glass" data-od-id="waveform-player">
          <button class="play-btn" id="modalPlay" aria-label={playing ? 'Pause' : 'Play'} onclick={togglePlay}>
            <svg class="ico play-ico" viewBox="0 0 24 24" fill="currentColor" style={playing ? 'display:none' : ''}><path d="M8 5.5v13l11-6.5z"/></svg>
            <svg class="ico pause-ico" viewBox="0 0 24 24" fill="currentColor" style={playing ? '' : 'display:none'}><path d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg>
          </button>
          <div class="wave" id="modalWave" aria-hidden="true" bind:this={waveEl}>
            {#each bars as h, i}
              <i class:played={i <= activeBar} style={'height:' + h + 'px'}></i>
            {/each}
          </div>
          <span class="player-time mono" id="modalTime">{timeText}</span>
        </div>
        <audio id="modalAudio" preload="metadata" bind:this={audioEl}
          ontimeupdate={paintWave}
          onplay={() => setPlayIcon(true)}
          onpause={() => setPlayIcon(false)}
          onended={() => { setPlayIcon(false); paintWave(); }}
        ></audio>

        <div class="meta-row" id="modalMeta" data-od-id="modal-meta">
          {#each pills as [k, v]}
            <span class="meta-pill">{k} <b>{v}</b></span>
          {/each}
        </div>

        <div class="lyrics-scroll glass" id="modalLyrics" tabindex="0" data-od-id="modal-lyrics">
          {#if !lyricLines}
            <p class="field-hint">No lyrics for this track.</p>
          {:else}
            {#each lyricLines as l}
              {#if l.type === 'section'}
                <div class="lyrics-section">{l.text}</div>
              {:else if l.type === 'empty'}
                <div class="lyrics-line empty"></div>
              {:else}
                <div class="lyrics-line">{l.text}</div>
              {/if}
            {/each}
          {/if}
        </div>

        <div class="modal-actions" data-od-id="modal-downloads">
          <a class="btn subtle" id="dlWav" href={dlWavHref} download hidden={dlWavHidden}>
            <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M4 19h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Download WAV
          </a>
          <a class="btn subtle" id="dlMp3" href={dlMp3Href} download>
            <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M4 19h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Download MP3
          </a>
          <button class="btn primary" id="modalRegen" data-od-id="modal-regen" onclick={regenClick} disabled={regenBusy}>Regenerate</button>
          <button class="btn subtle" id="modalExtend" data-od-id="modal-extend" onclick={extendClick} disabled={extendBusy || !supportsExtend} hidden={!supportsExtend}>Extend</button>
        </div>
      </div>
    </div>
  </div>
</div>
