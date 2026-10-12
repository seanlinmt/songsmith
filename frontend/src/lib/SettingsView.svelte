<script>
  let {
    config = null,
    health = null,
    musicModelLabel = '',
    llmModelLabel = '',
    onRefreshSettings,
    onRefreshHealth,
    onSaveSettings,
  } = $props();

  const endpoints = $derived(config && config.endpoints ? config.endpoints : {});

  let localaiUrl = $state('');
  let llmUrl = $state('');
  let musicModel = $state('');
  let llmModel = $state('');
  let coverModel = $state('');
  let supportsExtend = $state(false);

  // snapshot the values as loaded from config, so "dirty" means actually changed
  let baseline = $state({
    localai_url: '',
    llm_url: '',
    music_model: '',
    llm_model: '',
    image_model: '',
    supports_extend: false,
  });

  // re-sync editable state whenever the config prop changes (e.g. after Refresh)
  $effect(() => {
    const next = {
      localai_url: String(endpoints.localai || config?.localai_url || config?.music_url || ''),
      llm_url: String(endpoints.llm || config?.llm_url || ''),
      music_model: String(config ? config.music_model || config.model || '' : ''),
      llm_model: String(config ? config.llm_model || '' : ''),
      image_model: String(config ? config.image_model || config.cover_model || '' : ''),
      supports_extend: config ? !!config.supports_extend : false,
    };
    localaiUrl = next.localai_url;
    llmUrl = next.llm_url;
    musicModel = next.music_model;
    llmModel = next.llm_model;
    coverModel = next.image_model;
    supportsExtend = next.supports_extend;
    baseline = next;
  });

  const dirty = $derived(
    localaiUrl !== baseline.localai_url ||
    llmUrl !== baseline.llm_url ||
    musicModel !== baseline.music_model ||
    llmModel !== baseline.llm_model ||
    coverModel !== baseline.image_model ||
    supportsExtend !== baseline.supports_extend
  );

  let saving = $state(false);
  let saveErr = $state('');

  async function save() {
    if (!dirty || saving || !onSaveSettings) return;
    const payload = {};
    if (localaiUrl !== baseline.localai_url) payload.localai_url = localaiUrl;
    if (llmUrl !== baseline.llm_url) payload.llm_url = llmUrl;
    if (musicModel !== baseline.music_model) payload.music_model = musicModel;
    if (llmModel !== baseline.llm_model) payload.llm_model = llmModel;
    if (coverModel !== baseline.image_model) payload.image_model = coverModel;
    if (supportsExtend !== baseline.supports_extend) payload.supports_extend = supportsExtend;
    saving = true;
    saveErr = '';
    try {
      await onSaveSettings(payload);
      // config prop updates → effect above re-syncs fields and clears dirty
      if (onRefreshSettings) onRefreshSettings();
      if (onRefreshHealth) onRefreshHealth();
    } catch (err) {
      saveErr = err && err.message ? err.message : 'Save failed';
    } finally {
      saving = false;
    }
  }
</script>

<header class="view-head">
  <h1 class="display">Settings</h1>
  <p class="sub">Endpoints and models can be edited here — changes apply immediately and persist. Health checks run live.</p>
</header>

<div class="settings-grid">
  <div class="glass card settings-card" data-od-id="settings-endpoints">
    <div class="settings-card-head">
      <h3>Endpoints &amp; models</h3>
      <div class="settings-head-actions">
        <button class="btn primary settings-save-btn" id="settingsSave" data-od-id="settings-save" onclick={save} disabled={!dirty || saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button class="ghost-btn" id="settingsRefresh" data-od-id="settings-refresh" onclick={onRefreshSettings}>
          <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Refresh
        </button>
      </div>
    </div>

    <div class="field">
      <label class="field-label" for="cfgLocalai">LocalAI endpoint</label>
      <input class="input" id="cfgLocalai" type="url" placeholder="—" bind:value={localaiUrl} />
    </div>
    <div class="field">
      <label class="field-label" for="cfgLlm">LLM endpoint</label>
      <input class="input" id="cfgLlm" type="url" placeholder="—" bind:value={llmUrl} />
    </div>
    <div class="field-grid">
      <div class="field">
        <label class="field-label" for="cfgMusicModel">Music model</label>
        <input class="input" id="cfgMusicModel" type="text" placeholder="—" bind:value={musicModel} />
      </div>
      <div class="field">
        <label class="field-label" for="cfgLlmModel">LLM model</label>
        <input class="input" id="cfgLlmModel" type="text" placeholder="—" bind:value={llmModel} />
      </div>
    </div>
    <div class="field">
      <label class="field-label" for="cfgCoverModel">Cover art model</label>
      <input class="input" id="cfgCoverModel" type="text" placeholder="—" bind:value={coverModel} />
    </div>

    <p class="health-err" id="settingsSaveErr" data-od-id="settings-save-error" hidden={!saveErr}>{saveErr}</p>
  </div>

  <div class="glass card settings-card" data-od-id="settings-health">
    <div class="settings-card-head">
      <h3>Health</h3>
      <button class="ghost-btn" id="healthRefresh" data-od-id="health-refresh" onclick={onRefreshHealth}>
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Run check
      </button>
    </div>

    <div class="health-row" data-od-id="health-api">
      <span class="status-dot" data-state={health.api.state}></span>
      <div class="health-body">
        <div class="health-name">Songsmith API <span class="mono dim">/api/health</span></div>
        <p class="health-err" hidden={!health.api.err}>{health.api.err}</p>
      </div>
    </div>
    <div class="health-row" data-od-id="health-music">
      <span class="status-dot" data-state={health.music.state}></span>
      <div class="health-body">
        <div class="health-name">Music generation <span class="mono dim">{musicModelLabel}</span></div>
        <p class="health-err" hidden={!health.music.err}>{health.music.err}</p>
      </div>
    </div>
    <div class="health-row" data-od-id="health-llm">
      <span class="status-dot" data-state={health.llm.state}></span>
      <div class="health-body">
        <div class="health-name">LLM <span class="mono dim">{llmModelLabel}</span></div>
        <p class="health-err" hidden={!health.llm.err}>{health.llm.err}</p>
      </div>
    </div>

    <div class="settings-note">
      <label class="field-hint settings-cap-row" for="cfgExtend" data-od-id="settings-extend">
        <input class="settings-cap-check" id="cfgExtend" type="checkbox" bind:checked={supportsExtend} />
        <span class="settings-cap-name">Extend</span>
        <span class="dim">can continue from an existing clip</span>
      </label>
    </div>
  </div>
</div>

<style>
  .settings-head-actions { display: flex; align-items: center; gap: 8px; }
  .settings-save-btn { height: 38px; padding: 0 16px; font-size: 13px; border-radius: 10px; }
  .settings-cap-row { display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
  .settings-cap-check { accent-color: var(--accent, #22d3ee); width: 14px; height: 14px; margin: 0; cursor: pointer; }
  .settings-cap-name { color: var(--text-dim, inherit); }
</style>
