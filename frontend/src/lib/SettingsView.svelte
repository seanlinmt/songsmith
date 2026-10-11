<script>
  let {
    config = null,
    health = null,
    capExtend = '—',
    capStereo = '—',
    musicModelLabel = '',
    llmModelLabel = '',
    onRefreshSettings,
    onRefreshHealth,
  } = $props();

  const localaiUrl = $derived(config ? config.localai_url || config.music_url || config.localai_endpoint || '' : '');
  const llmUrl = $derived(config ? config.llm_url || config.llm_endpoint || '' : '');
  const musicModel = $derived(config ? config.music_model || config.model || '' : '');
  const llmModel = $derived(config ? config.llm_model || '' : '');
  const coverModel = $derived(config ? config.cover_model || '' : '');
</script>

<header class="view-head">
  <h1 class="display">Settings</h1>
  <p class="sub">Endpoints are read from the server config. Health checks run live.</p>
</header>

<div class="settings-grid">
  <div class="glass card settings-card" data-od-id="settings-endpoints">
    <div class="settings-card-head">
      <h3>Endpoints &amp; models</h3>
      <button class="ghost-btn" id="settingsRefresh" data-od-id="settings-refresh" onclick={onRefreshSettings}>
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Refresh
      </button>
    </div>

    <div class="field">
      <label class="field-label" for="cfgLocalai">LocalAI endpoint</label>
      <input class="input" id="cfgLocalai" type="url" readonly placeholder="—" value={String(localaiUrl)} />
    </div>
    <div class="field">
      <label class="field-label" for="cfgLlm">LLM endpoint</label>
      <input class="input" id="cfgLlm" type="url" readonly placeholder="—" value={String(llmUrl)} />
    </div>
    <div class="field-grid">
      <div class="field">
        <label class="field-label" for="cfgMusicModel">Music model</label>
        <input class="input" id="cfgMusicModel" type="text" readonly placeholder="—" value={String(musicModel)} />
      </div>
      <div class="field">
        <label class="field-label" for="cfgLlmModel">LLM model</label>
        <input class="input" id="cfgLlmModel" type="text" readonly placeholder="—" value={String(llmModel)} />
      </div>
    </div>
    <div class="field">
      <label class="field-label" for="cfgCoverModel">Cover art model</label>
      <input class="input" id="cfgCoverModel" type="text" readonly placeholder="—" value={String(coverModel)} />
    </div>
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
      <p class="field-hint">Capabilities: extend <span class="mono">{capExtend}</span> · stereo <span class="mono">{capStereo}</span></p>
    </div>
  </div>
</div>
