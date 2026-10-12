<script>
  import { songCoverUrl, songAudioUrl } from './songs.js';
  import { fmtDur } from './format.js';

  let { song, supportsExtend = false, onOpen, onPlay, onRegen, onExtend, onDelete, onCoverRegen } = $props();

  let busy = $state('');

  const cover = $derived(songCoverUrl(song));
  const audioUrl = $derived(songAudioUrl(song));
  const tags = $derived(Array.isArray(song.tags) ? song.tags.slice(0, 3) : []);
  const displayName = $derived(song && song.title ? '"' + song.title + '"' : 'this song');

  async function doRegen() {
    busy = 'regen';
    try { await onRegen(song.id); } finally { busy = ''; }
  }

  async function doExtend() {
    busy = 'extend';
    try { await onExtend(song.id); } finally { busy = ''; }
  }

  async function doCover() {
    busy = 'cover';
    try { await onCoverRegen(song.id); } finally { busy = ''; }
  }

  async function doDelete() {
    busy = 'del';
    if (!confirm('Delete ' + displayName + "? This can't be undone.")) { busy = ''; return; }
    try { await onDelete(song.id); } finally { busy = ''; }
  }

  function handleClick(e) {
    const playBtn = e.target.closest('[data-play]');
    if (playBtn) { onPlay(song); return; }
    const actBtn = e.target.closest('[data-act]');
    if (actBtn) {
      const act = actBtn.dataset.act;
      if (act === 'dl') return; // native download link
      if (act === 'regen') return doRegen();
      if (act === 'cover') return doCover();
      if (act === 'extend') return doExtend();
      if (act === 'del') return doDelete();
      return;
    }
    onOpen(song);
  }
</script>

<article class="glass song-card" data-od-id="song-card-{song.id}" tabindex="0" role="button"
  aria-label={'Open ' + (song.title || 'song')} onclick={handleClick}>
  <div class="song-cover">
    {#if cover}
      <img loading="lazy" src={cover} alt="" width="300" height="300"
        onerror={(e) => { e.currentTarget.style.display = 'none'; }} />
    {/if}
    <div class="cover-fallback"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" opacity=".5"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="2.4" fill="currentColor"/></svg></div>
    <span class="song-duration">{fmtDur(song.duration_seconds)}</span>
    <div class="play-overlay">
      <button class="play-btn" data-play={song.id} aria-label={'Play ' + (song.title || 'song')}>
        <svg class="ico play-ico" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg>
      </button>
      {#if onCoverRegen}
        <button class="cover-regen" data-act="cover" data-id={song.id} title="New cover art"
          aria-label={'Regenerate cover art for ' + (song.title || 'song')} disabled={busy === 'cover'}>
          <svg class="ico" viewBox="0 0 24 24" fill="none"
            class:spin={busy === 'cover'}>
            <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      {/if}
    </div>
  </div>
  <div class="song-title-block">
    <div class="song-title">{song.title || 'Untitled'}</div>
    {#if tags.length || song.instrumental}
      <div class="song-tags">
        {#each tags as t}
          <span class="song-tag">{t}</span>
        {/each}
        {#if song.instrumental}
          <span class="song-tag">instrumental</span>
        {/if}
      </div>
    {/if}
  </div>
  <div class="song-actions">
    <button class="song-action" data-act="regen" data-id={song.id} title="Regenerate" disabled={busy === 'regen'}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Regen</span>
    </button>
    {#if supportsExtend}
      <button class="song-action" data-act="extend" data-id={song.id} title="Extend" disabled={busy === 'extend'}>
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <span>Extend</span>
      </button>
    {/if}
    <a class="song-action" data-act="dl" data-id={song.id} href={audioUrl} download title="Download">
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M4 19h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Save</span>
    </a>
    <button class="song-action danger" data-act="del" data-id={song.id} title="Delete" disabled={busy === 'del'}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V5h6v2m-8 0 .7 12a1.5 1.5 0 0 0 1.5 1.4h3.6a1.5 1.5 0 0 0 1.5-1.4L17 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Delete</span>
    </button>
  </div>
</article>
