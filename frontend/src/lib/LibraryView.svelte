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
  <div class="empty-state studio-panel" id="libraryEmpty" data-od-id="library-empty">
    <div class="vinyl" aria-hidden="true">
      <svg viewBox="0 0 80 80" width="72" height="72" fill="none">
        <circle cx="40" cy="40" r="36" fill="var(--surface-2)" stroke="var(--border-strong)" stroke-width="1.5"/>
        <circle cx="40" cy="40" r="26" stroke="var(--border)" stroke-width="1"/>
        <circle cx="40" cy="40" r="18" stroke="var(--border)" stroke-width="1"/>
        <circle cx="40" cy="40" r="10" fill="var(--accent)"/>
        <circle cx="40" cy="40" r="3" fill="var(--bg)"/>
      </svg>
    </div>
    <h2>Create your first song</h2>
    <p>Your library is empty. Describe a vibe in Create and Songsmith will render a track locally.</p>
    <button class="btn primary" id="emptyCreateBtn" onclick={onGoCreate}>Go to Create</button>
  </div>
{/if}
