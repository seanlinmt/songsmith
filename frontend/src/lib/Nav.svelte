<script>
  let { route = 'create', libraryCount = 0, healthState = 'unknown', onRoute, onRefreshHealth } = $props();
</script>

<nav class="topnav glass" data-od-id="topnav" aria-label="Main">
  <a class="brand" href="#" data-od-id="brand" onclick={(e) => { e.preventDefault(); onRoute('create'); }}>
    <span class="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 64 64" width="26" height="26" fill="none">
        <defs><linearGradient id="bm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent-2)"/></linearGradient></defs>
        <path d="M40 12v24.8a8.8 8.8 0 1 0 3.4 6.95V22.6h8.6V14.7H49V12z" fill="url(#bm)"/>
      </svg>
    </span>
    <span class="brand-name">Songsmith</span>
    <span class="brand-tag">local studio</span>
  </a>
  <div class="nav-tabs" role="tablist">
    <button class="nav-tab" role="tab" data-route="create" aria-selected={route === 'create'} onclick={() => onRoute('create')}>
      <svg class="ico" viewBox="0 0 24 24"><path d="M12 5v14m-7-7h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>
      <span>Create</span>
    </button>
    <button class="nav-tab" role="tab" data-route="library" aria-selected={route === 'library'} onclick={() => onRoute('library')}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M4 4h2.5v16H4zM9 4h2.5v16H9zM15.2 5.1l2.3-.6 4 15-2.3.6z" fill="currentColor"/></svg>
      <span>Library</span>
      {#if libraryCount > 0}
        <span class="nav-badge">{libraryCount}</span>
      {/if}
    </button>
    <button class="nav-tab" role="tab" data-route="settings" aria-selected={route === 'settings'} onclick={() => onRoute('settings')}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" stroke-width="1.8"/><path d="m19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3.05V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.51 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c.24.55.76.94 1.36 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1Z" stroke="currentColor" stroke-width="1.6"/></svg>
      <span>Settings</span>
      <span class="status-dot dot-inline" data-state={healthState} title="API health"></span>
    </button>
  </div>
  <button class="ghost-btn" title="Check API health" onclick={() => onRefreshHealth()}>
    <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </button>
</nav>
