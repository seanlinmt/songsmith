<script>
  let {
    config = null,
    health = null,
    theme = 'system',
    onSetTheme,
    onRefreshSettings,
    onRefreshHealth,
    onSaveSettings,
  } = $props();

  const endpoints = $derived(config && config.endpoints ? config.endpoints : {});
  const apiKeys = $derived(config && config.api_keys ? config.api_keys : {});

  let musicUrl = $state('');
  let imageUrl = $state('');
  let llmUrl = $state('');
  let musicModel = $state('');
  let llmModel = $state('');
  let coverModel = $state('');
  let musicKey = $state('');
  let imageKey = $state('');
  let llmKey = $state('');

  // snapshot the values as loaded from config, so "dirty" means actually changed
  let baseline = $state({
    music_url: '',
    image_url: '',
    llm_url: '',
    music_model: '',
    llm_model: '',
    image_model: '',
    music_api_key: '',
    image_api_key: '',
    llm_api_key: '',
  });

  // re-sync editable state whenever the config prop changes (e.g. after Refresh)
  $effect(() => {
    const next = {
      // legacy configs only had `endpoints.localai`; music/image fall back to it
      music_url: String(endpoints.music || endpoints.localai || config?.music_url || config?.localai_url || ''),
      image_url: String(endpoints.image || endpoints.localai || config?.image_url || config?.localai_url || ''),
      llm_url: String(endpoints.llm || config?.llm_url || ''),
      music_model: String(config ? config.music_model || config.model || '' : ''),
      llm_model: String(config ? config.llm_model || '' : ''),
      image_model: String(config ? config.image_model || config.cover_model || '' : ''),
      music_api_key: String(apiKeys.music || ''),
      image_api_key: String(apiKeys.image || ''),
      llm_api_key: String(apiKeys.llm || ''),
    };
    musicUrl = next.music_url;
    imageUrl = next.image_url;
    llmUrl = next.llm_url;
    musicModel = next.music_model;
    llmModel = next.llm_model;
    coverModel = next.image_model;
    musicKey = next.music_api_key;
    imageKey = next.image_api_key;
    llmKey = next.llm_api_key;
    baseline = next;  });

  const dirty = $derived(
    musicUrl !== baseline.music_url ||
    imageUrl !== baseline.image_url ||
    llmUrl !== baseline.llm_url ||
    musicModel !== baseline.music_model ||
    llmModel !== baseline.llm_model ||
    coverModel !== baseline.image_model ||
    musicKey !== baseline.music_api_key ||
    imageKey !== baseline.image_api_key ||
    llmKey !== baseline.llm_api_key
  );

  let saving = $state(false);
  let saveErr = $state('');

  async function save() {
    if (!dirty || saving || !onSaveSettings) return;
    const payload = {};
    if (musicUrl !== baseline.music_url) payload.music_url = musicUrl;
    if (imageUrl !== baseline.image_url) payload.image_url = imageUrl;
    if (llmUrl !== baseline.llm_url) payload.llm_url = llmUrl;
    if (musicModel !== baseline.music_model) payload.music_model = musicModel;
    if (llmModel !== baseline.llm_model) payload.llm_model = llmModel;
    if (coverModel !== baseline.image_model) payload.image_model = coverModel;
    if (musicKey !== baseline.music_api_key) payload.music_api_key = musicKey;
    if (imageKey !== baseline.image_api_key) payload.image_api_key = imageKey;
    if (llmKey !== baseline.llm_api_key) payload.llm_api_key = llmKey;
    if (musicModel !== baseline.music_model) payload.music_model = musicModel;
    if (llmModel !== baseline.llm_model) payload.llm_model = llmModel;
    if (coverModel !== baseline.image_model) payload.image_model = coverModel;
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
  <p class="sub">Endpoints and models can be edited here — changes apply immediately and persist. Health is polled automatically every 15 seconds.</p>
</header>

<div class="settings-grid">
  <div class="studio-panel card settings-card appearance-card" data-od-id="settings-appearance">
    <div class="settings-card-head">
      <h3>Appearance</h3>
    </div>
    <div class="field">
      <span class="field-label" id="themeSegLabel">Theme</span>
      <div class="seg" role="radiogroup" aria-labelledby="themeSegLabel" data-od-id="theme-seg">
        <label class="seg-opt" class:active={theme === 'light'}>
          <input type="radio" name="ss-theme" value="light" checked={theme === 'light'} onchange={() => onSetTheme?.('light')} />
          <svg class="ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.5v2m0 15v2M4.8 4.8l1.4 1.4m11.6 11.6 1.4 1.4M2.5 12h2m15 0h2M4.8 19.2l1.4-1.4M17.8 6.2l1.4-1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          Light
        </label>
        <label class="seg-opt" class:active={theme === 'dark'}>
          <input type="radio" name="ss-theme" value="dark" checked={theme === 'dark'} onchange={() => onSetTheme?.('dark')} />
          <svg class="ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          Dark
        </label>
        <label class="seg-opt" class:active={theme === 'system'}>
          <input type="radio" name="ss-theme" value="system" checked={theme === 'system'} onchange={() => onSetTheme?.('system')} />
          <svg class="ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M8.5 20h7M12 16v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          System
        </label>
      </div>
      <span class="field-width-hint">System follows your OS light/dark preference and updates live.</span>
    </div>
  </div>

  <div class="studio-panel card settings-card" data-od-id="settings-endpoints">
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

    <div class="service-group">
      <div class="service-group-title">Audio synthesis service</div>
      <div class="field-grid cols3">
        <div class="field field-endpoint">
          <label class="field-label" for="cfgLocalai"><span class="status-dot dot-inline" data-state={health?.music?.state || 'unknown'}></span> Music endpoint <span class="mono dim">/v1/sound-generation</span></label>
          <input class="input mono" id="cfgLocalai" type="url" placeholder="http://127.0.0.1:7777" bind:value={musicUrl} />
          <span class="field-width-hint">Base URL (host + port)</span>
        </div>
        <div class="field field-model">
          <label class="field-label" for="cfgMusicModel">Music model</label>
          <input class="input mono" id="cfgMusicModel" type="text" placeholder="ace-step-turbo" bind:value={musicModel} />
          <span class="field-width-hint">Model ID</span>
        </div>
        <div class="field field-key">
          <label class="field-label" for="cfgMusicKey">API key</label>
          <input class="input mono input-key" id="cfgMusicKey" type="text" placeholder="optional" autocomplete="off" bind:value={musicKey} />
          <span class="field-width-hint">Bearer token (if required)</span>
        </div>
      </div>
    </div>

    <div class="service-group">
      <div class="service-group-title">Artwork generation service</div>
      <div class="field-grid cols3">
        <div class="field field-endpoint">
          <label class="field-label" for="cfgImageUrl"><span class="status-dot dot-inline" data-state={health?.image?.state || 'unknown'}></span> Cover art endpoint <span class="mono dim">/v1/images/generations</span></label>
          <input class="input mono" id="cfgImageUrl" type="url" placeholder="http://127.0.0.1:7777" bind:value={imageUrl} />
          <span class="field-width-hint">Base URL (host + port)</span>
        </div>
        <div class="field field-model">
          <label class="field-label" for="cfgCoverModel">Cover art model</label>
          <input class="input mono" id="cfgCoverModel" type="text" placeholder="flux-schnell" bind:value={coverModel} />
          <span class="field-width-hint">Model ID</span>
        </div>
        <div class="field field-key">
          <label class="field-label" for="cfgImageKey">API key</label>
          <input class="input mono input-key" id="cfgImageKey" type="text" placeholder="optional" autocomplete="off" bind:value={imageKey} />
          <span class="field-width-hint">Bearer token (if required)</span>
        </div>
      </div>
    </div>

    <div class="service-group">
      <div class="service-group-title">Language model service (lyrics &amp; prompt assist)</div>
      <div class="field-grid cols3">
        <div class="field field-endpoint">
          <label class="field-label" for="cfgLlm"><span class="status-dot dot-inline" data-state={health?.llm?.state || 'unknown'}></span> Lyrics endpoint <span class="mono dim">/v1/chat/completions</span></label>
          <input class="input mono" id="cfgLlm" type="url" placeholder="http://127.0.0.1:11434/v1" bind:value={llmUrl} />
          <span class="field-width-hint">OpenAI-compatible URL</span>
        </div>
        <div class="field field-model">
          <label class="field-label" for="cfgLlmModel">Lyrics model</label>
          <input class="input mono" id="cfgLlmModel" type="text" placeholder="qwen2.5-7b-instruct" bind:value={llmModel} />
          <span class="field-width-hint">Model ID</span>
        </div>
        <div class="field field-key">
          <label class="field-label" for="cfgLlmKey">API key</label>
          <input class="input mono input-key" id="cfgLlmKey" type="text" placeholder="optional" autocomplete="off" bind:value={llmKey} />
          <span class="field-width-hint">Bearer token (if required)</span>
        </div>
      </div>
    </div>

    <div class="health-row" data-od-id="health-api">
      <span class="status-dot" data-state={health?.api?.state || 'unknown'}></span>
      <div class="health-body">
        <div class="health-name">Songsmith API <span class="mono dim">/api/health</span></div>
        <p class="health-err" hidden={!health?.api?.err}>{health?.api?.err}</p>
      </div>
    </div>
    <p class="health-err" id="settingsSaveErr" data-od-id="settings-save-error" hidden={!saveErr}>{saveErr}</p>
  </div>
</div>

<style>
  .settings-head-actions { display: flex; align-items: center; gap: 8px; }
  .settings-save-btn { height: 36px; padding: 0 16px; font-size: 13px; border-radius: var(--radius-sm); }
  .field-grid.cols3 { grid-template-columns: minmax(260px, 1.85fr) minmax(130px, 0.85fr) minmax(170px, 1.2fr); }
  @media (max-width: 820px) {
    .field-grid.cols3 { grid-template-columns: 1fr; }
  }

  .appearance-card .field { display: flex; flex-direction: column; gap: 8px; }

  /* segmented 3-way theme switch — hardware toggle feel */
  .seg {
    display: inline-flex;
    align-self: flex-start;
    gap: 2px;
    padding: 3px;
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .seg-opt {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 30px;
    padding: 0 14px;
    border-radius: var(--radius-sm);
    font: 600 12.5px/1 var(--font);
    color: var(--text-dim);
    cursor: pointer;
    user-select: none;
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
  }
  .seg-opt:hover { color: var(--text); background: var(--surface-2); }
  .seg-opt.active {
    background: var(--surface-3);
    color: var(--text);
    box-shadow: inset 0 0 0 1px var(--border-strong);
  }
  .seg-opt input {
    position: absolute;
    opacity: 0;
    width: 1px;
    height: 1px;
    pointer-events: none;
  }
  .seg-opt:has(input:focus-visible) {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>
