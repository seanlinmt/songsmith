<script>
  import { onMount } from 'svelte';
  import { api } from './lib/api.js';
  import { toast, toasts } from './lib/toast.svelte.js';
  import { supportsExtend } from './lib/songs.js';
  import Nav from './lib/Nav.svelte';
  import CreateView from './lib/CreateView.svelte';
  import ProgressView from './lib/ProgressView.svelte';
  import LibraryView from './lib/LibraryView.svelte';
  import SettingsView from './lib/SettingsView.svelte';
  import SongModal from './lib/SongModal.svelte';

  /* ---------------- state ---------------- */
  let route = $state('create');
  let config = $state(null);
  let configFailed = $state(false);
  let songs = $state([]);
  let activeGroup = $state(null);   // job_group_id currently being watched
  let activeJobs = $state([]);      // last known job rows for that group
  let pollTimer = null;             // plain (non-reactive) handle

  let health = $state({
    nav: 'unknown',
    api: { state: 'unknown', err: '' },
    music: { state: 'unknown', err: '' },
    image: { state: 'unknown', err: '' },
    llm: { state: 'unknown', err: '' },
  });

  let modalSong = $state(null);
  let modalAutoplay = $state(false);

  const canExtend = $derived(supportsExtend(config));
  const libraryMeta = $derived(
    songs.length
      ? songs.length + ' track' + (songs.length > 1 ? 's' : '') + ' · newest first'
      : 'Your generated tracks, newest first.'
  );

  /* ---------------- routing ---------------- */
  function show(r, opts) {
    if (r === 'progress' && !activeGroup && !opts) r = 'library';
    route = r;
    try { localStorage.setItem('ss_route', r); } catch (_) {}
    window.scrollTo({ top: 0 });
  }

  function handleRoute(r) {
    if (r === 'library') refreshLibrary();
    if (r === 'settings') refreshSettings();
    show(r);
  }

  /* ---------------- create ---------------- */
  function onStarted(gid) {
    activeGroup = gid;
    activeJobs = [];
    show('progress', true);
    startPolling();
  }

  /* ---------------- progress / polling ---------------- */
  function startPolling() {
    stopPolling();
    pollJobs();
    pollTimer = setInterval(pollJobs, 2500);
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  async function pollJobs() {
    const gid = activeGroup;
    if (!gid) { stopPolling(); return; }
    try {
      const data = await api.get('/api/jobs?group=' + encodeURIComponent(gid));
      const rows = Array.isArray(data) ? data : (data && (data.jobs || data.songs || data.items)) || [];
      activeJobs = rows;
      const allDone = rows.length > 0 && rows.every((j) => ['complete', 'completed', 'failed', 'error', 'cancelled'].includes(String(j.status || '').toLowerCase()));
      if (allDone) {
        activeGroup = null;
        activeJobs = [];
        stopPolling();
        await refreshLibrary();
        show('library');
        toast('Your songs are ready');
      }
    } catch (_) { /* transient — keep polling */ }
  }

  function abandonPoll() {
    stopPolling();
    refreshLibrary();
    show('library');
    toast('You can keep browsing — it stays in Library');
  }

  /* ---------------- library ---------------- */
  async function refreshLibrary() {
    try {
      const data = await api.get('/api/songs');
      songs = Array.isArray(data) ? data : (data && (data.songs || data.items)) || [];
    } catch (err) {
      toast("Couldn't load library: " + err.message, 'err');
    }
  }

  async function deleteSong(id) {
    try {
      await api.send('/api/songs/' + encodeURIComponent(id), 'DELETE');
      songs = songs.filter((s) => String(s.id) !== String(id));
      toast('Deleted');
    } catch (err) { toast('Delete failed: ' + err.message, 'err'); }
  }

  async function regenerateSong(id, overrides = {}) {
    try {
      const res = await api.send('/api/songs/' + encodeURIComponent(id) + '/regenerate', 'POST', overrides || {});
      activeGroup = (res && res.job_group_id) || null;
      activeJobs = [];
      show('progress', true);
      startPolling();
      toast('Regenerating');
    } catch (err) { toast('Regenerate failed: ' + err.message, 'err'); }
  }

  async function extendSong(id) {
    try {
      await api.send('/api/songs/' + encodeURIComponent(id) + '/extend', 'POST', {});
      toast('Extending song…');
      setTimeout(refreshLibrary, 1200);
    } catch (err) { toast('Extend failed: ' + err.message, 'err'); }
  }

  async function regenerateCover(id) {
    try {
      await api.send('/api/songs/' + encodeURIComponent(id) + '/cover', 'POST', {});
      await refreshLibrary();
      if (modalSong && String(modalSong.id) === String(id)) {
        const fresh = songs.find((s) => String(s.id) === String(id));
        modalSong = fresh ? { ...fresh } : null;
      }
      toast('New cover painted');
    } catch (err) { toast('Cover failed: ' + err.message, 'err'); }
  }

  /* ---------------- modal ---------------- */
  function openModal(song, autoplay) {
    modalSong = { ...song };
    modalAutoplay = autoplay;
  }

  function closeModal() {
    modalSong = null;
  }

  const variantsForOpenSong = $derived.by(() => {
    if (!modalSong) return [];
    const oid = String(modalSong.id);
    const ogid = modalSong.job_group_id;
    return songs.filter((s) => {
      if (String(s.id) === oid) return false;
      if (s.parent_id != null && String(s.parent_id) === oid) return true;
      if (ogid != null && s.job_group_id != null && String(s.job_group_id) === String(ogid)) return true;
      return false;
    });
  });

  function playVariant(v) {
    openModal(v, true);
  }

  async function deleteVariant(v) {
    try {
      await api.send('/api/songs/' + encodeURIComponent(v.id), 'DELETE');
      songs = songs.filter((s) => String(s.id) !== String(v.id));
      toast('Deleted');
    } catch (err) { toast('Delete failed: ' + err.message, 'err'); }
  }

  /* ---------------- settings / health ---------------- */
  function applyHealth(h) {
    health.api = { state: 'ok', err: '' };
    health.nav = 'ok';

    let anyDown = false;
    // /api/health returns {localai: {up}, image: {up}, llm: {up}}
    const services = h || {};
    const music = services.localai || null;
    const image = services.image || null;
    const llm = services.llm || null;
    if (music && typeof music === 'object') {
      const ok = music.up === true;
      anyDown = anyDown || !ok;
      health.music = { state: ok ? 'ok' : 'error', err: ok ? '' : music.error || 'unreachable' };
    } else health.music = { state: 'ok', err: '' };
    if (image && typeof image === 'object') {
      const ok = image.up === true;
      anyDown = anyDown || !ok;
      health.image = { state: ok ? 'ok' : 'error', err: ok ? '' : image.error || 'unreachable' };
    } else health.image = { state: 'ok', err: '' };
    if (llm && typeof llm === 'object') {
      const ok = llm.up === true;
      anyDown = anyDown || !ok;
      health.llm = { state: ok ? 'ok' : 'error', err: ok ? '' : llm.error || 'unreachable' };
    } else health.llm = { state: 'ok', err: '' };
    if (anyDown) health.nav = 'error';
  }

  async function refreshHealth(notify) {
    health.api = { state: 'busy', err: '' };
    health.music = { state: 'busy', err: '' };
    health.image = { state: 'busy', err: '' };
    health.llm = { state: 'busy', err: '' };
    try {
      const h = await api.get('/api/health');
      applyHealth(h);
      if (notify) toast('Health check complete');
    } catch (err) {
      health.api = { state: 'error', err: err.message };
      health.music = { state: 'error', err: 'unreachable — API offline' };
      health.image = { state: 'error', err: 'unreachable — API offline' };
      health.llm = { state: 'error', err: 'unreachable — API offline' };
      health.nav = 'error';
      if (notify) toast('Health check failed', 'err');
    }
  }

  // Cheap liveness probe — poll every 15s so the nav dot stays current
  // without user action. A separate from the full (model-listing) check.
  let healthTimer = null;
  async function pollHealth() {
    try {
      const h = await api.get('/api/health');
      applyHealth(h);
    } catch (_) {
      health.api = { state: 'error', err: 'unreachable' };
      health.music = { state: 'error', err: 'unreachable — API offline' };
      health.image = { state: 'error', err: 'unreachable — API offline' };
      health.llm = { state: 'error', err: 'unreachable — API offline' };
      health.nav = 'error';
    }
  }
  function startHealthPolling() {
    if (healthTimer) return;
    healthTimer = setInterval(pollHealth, 15000);
  }
  function stopHealthPolling() {
    if (healthTimer) { clearInterval(healthTimer); healthTimer = null; }
  }

  async function refreshSettings() {
    try {
      const cfg = await api.get('/api/config');
      config = cfg || {};
      configFailed = false;
    } catch (err) {
      configFailed = true;
      if (route === 'settings') toast('Config unavailable: ' + err.message, 'err');
    }
    refreshHealth(false);
  }

  async function saveSettings(payload) {
    const cfg = await api.send('/api/config', 'PATCH', payload);
    config = cfg || {};
    configFailed = false;
  }

  /* ---------------- active job recovery ---------------- */
  async function recoverActive() {
    try {
      const data = await api.get('/api/jobs/active');
      const rows = Array.isArray(data) ? data : (data && (data.jobs || data.items)) || [];
      if (rows.length) {
        activeJobs = rows;
        activeGroup = (rows[0] && (rows[0].job_group_id || rows[0].group_id)) || activeGroup;
        if (activeGroup) {
          show('progress');
          startPolling();
          return true;
        }
      }
    } catch (_) { /* fine */ }
    return false;
  }

  /* ---------------- boot ---------------- */
  async function boot() {
    let r = 'create';
    try { r = localStorage.getItem('ss_route') || 'create'; } catch (_) {}
    show(r === 'progress' ? 'create' : r);

    // config + health fire-and-forget
    refreshSettings();
    // library
    await refreshLibrary();
    // recover in-flight jobs
    const recovered = await recoverActive();
    if (recovered) return;
    if (['create', 'library', 'settings'].includes(route)) refreshHealth(false);
  }

  onMount(() => {
    boot();
    startHealthPolling();

    const onKey = (e) => { if (e.key === 'Escape' && modalSong) closeModal(); };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      stopHealthPolling();
    };
  });
</script>

<div class="bg-orbs" aria-hidden="true">
  <div class="orb orb-a"></div>
  <div class="orb orb-b"></div>
</div>
<div class="noise" aria-hidden="true"></div>

<!-- ============ NAV ============ -->
<Nav route={route} libraryCount={songs.length} healthState={health.nav} onRoute={handleRoute} onRefreshHealth={() => refreshHealth(true)} />

<main class="shell" id="shell">
  <!-- ============ CREATE ============ -->
  <section class="view" id="viewCreate" data-view="create" hidden={route !== 'create'}>
    <CreateView health={health} onStarted={onStarted} />
  </section>

  <!-- ============ PROGRESS ============ -->
  <section class="view" id="viewProgress" data-view="progress" hidden={route !== 'progress'}>
    <ProgressView jobs={activeJobs} activeGroup={activeGroup} onAbandon={abandonPoll} />
  </section>

  <!-- ============ LIBRARY ============ -->
  <section class="view" id="viewLibrary" data-view="library" hidden={route !== 'library'}>
    <LibraryView
      songs={songs}
      meta={libraryMeta}
      supportsExtend={canExtend}
      onOpen={(s) => openModal(s, false)}
      onPlay={(s) => openModal(s, true)}
      onRegen={regenerateSong}
      onExtend={extendSong}
      onDelete={deleteSong}
      onCoverRegen={regenerateCover}
      onRefresh={refreshLibrary}
      onGoCreate={() => show('create')}
    />
  </section>

  <!-- ============ SETTINGS ============ -->
  <section class="view" id="viewSettings" data-view="settings" hidden={route !== 'settings'}>
    <SettingsView
      config={config}
      health={health}
      onRefreshSettings={refreshSettings}
      onRefreshHealth={() => refreshHealth(true)}
      onSaveSettings={saveSettings}
    />
  </section>
</main>

<!-- ============ SONG DETAIL MODAL ============ -->
<SongModal
  song={modalSong}
  autoplay={modalAutoplay}
  supportsExtend={canExtend}
  variants={variantsForOpenSong}
  onRegen={regenerateSong}
  onExtend={extendSong}
  onCoverRegen={regenerateCover}
  onClose={closeModal}
  onPlayVariant={playVariant}
  onDeleteVariant={deleteVariant}
/>

<!-- ============ TOASTS ============ -->
<div class="toast-root" id="toastRoot" aria-live="polite">
  {#each toasts as t (t.id)}
    <div class="toast {t.type}" class:leaving={t.leaving}>{@html t.svg}<span>{t.msg}</span></div>
  {/each}
</div>
