<script>
  import SongCard from './SongCard.svelte';

  let {
    songs = [],
    meta = '',
    supportsExtend = false,
    onOpen,
    onPlay,
    onRegen,
    onExtend,
    onDelete,
    onCoverRegen,
    onRefresh,
    onGoCreate,
  } = $props();
</script>

<header class="view-head head-row">
  <div>
    <h1 class="display">Library</h1>
    <p class="sub"><span id="libraryMeta">{meta}</span></p>
  </div>
  <button class="ghost-btn" id="libraryRefresh" title="Refresh" onclick={onRefresh}>
    <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    Refresh
  </button>
</header>

<div class="song-grid" id="songGrid" data-od-id="song-grid">
  {#each songs as s (s.id)}
    <SongCard
      song={s}
      supportsExtend={supportsExtend}
      onOpen={onOpen}
      onPlay={onPlay}
      onRegen={onRegen}
      onExtend={onExtend}
      onDelete={onDelete}
      onCoverRegen={onCoverRegen}
    />
  {/each}
</div>

{#if songs.length === 0}
  <div class="empty-state glass" id="libraryEmpty" data-od-id="library-empty">
    <div class="vinyl" aria-hidden="true">
      <svg viewBox="0 0 120 120" width="120" height="120">
        <defs>
          <linearGradient id="vg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent-2)"/></linearGradient>
        </defs>
        <circle cx="60" cy="60" r="56" fill="var(--surface-2)" stroke="rgba(255,255,255,.14)"/>
        <circle cx="60" cy="60" r="46" fill="none" stroke="rgba(255,255,255,.08)"/>
        <circle cx="60" cy="60" r="38" fill="none" stroke="rgba(255,255,255,.07)"/>
        <circle cx="60" cy="60" r="30" fill="none" stroke="rgba(255,255,255,.06)"/>
        <circle cx="60" cy="60" r="18" fill="url(#vg)" opacity=".9"/>
        <circle cx="60" cy="60" r="4.5" fill="var(--bg)"/>
      </svg>
    </div>
    <h2>Create your first song</h2>
    <p>Your library is empty. Describe a vibe in Create and Songsmith will spin up a song for you.</p>
    <button class="btn primary" id="emptyCreateBtn" onclick={onGoCreate}>Go to Create</button>
  </div>
{/if}
