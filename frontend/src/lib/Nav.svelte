<script>
  let { route = 'create', libraryCount = 0, healthState = 'unknown', onRoute, onRefreshHealth, onOpenLogs } = $props();
</script>

<nav class="topnav" data-od-id="topnav" aria-label="Main">
  <a class="brand" href="/" data-od-id="brand" onclick={(e) => { e.preventDefault(); onRoute('create'); }}>
    <span class="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
        <path d="M9 18V5l12-2v13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="6" cy="18" r="3" stroke="currentColor" stroke-width="2"/>
        <circle cx="18" cy="16" r="3" stroke="currentColor" stroke-width="2"/>
      </svg>
    </span>
    <span class="brand-name">Songsmith</span>
    <span class="brand-tag">local studio</span>
  </a>
  <div class="nav-tabs" role="tablist">
    <button class="nav-tab" role="tab" data-route="create" aria-selected={route === 'create'} onclick={() => onRoute('create')}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 5v14m-7-7h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      <span>Create</span>
    </button>
    <button class="nav-tab" role="tab" data-route="library" aria-selected={route === 'library'} onclick={() => onRoute('library')}>
      <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M4 5h2.5v14H4zM9.5 5H12v14H9.5zM15.2 5.4l2.3-.5 3.5 14-2.3.5z" fill="currentColor"/></svg>
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
    <span>Check health</span>
  </button>
  <button class="ghost-btn" title="Server logs" aria-label="Server logs" onclick={() => onOpenLogs?.()}>
    <svg class="ico" viewBox="0 0 24 24" fill="none">
      <rect x="8" y="7" width="8" height="13" rx="4" stroke="currentColor" stroke-width="1.8"/>
      <path d="M12 7V4.5M9.2 5.2 8 3.6m6.8 1.6L16 3.6M8 10.5H4.5m15 0H16M8 15H4.5m15 0H16M8.4 18.8l-1.9 1.4m9.1-1.4 1.9 1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
    </svg>
  </button>
</nav>
