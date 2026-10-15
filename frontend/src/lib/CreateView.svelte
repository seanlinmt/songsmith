<script>
  import { onMount } from 'svelte';
  import { api } from './api.js';
  import { toast } from './toast.svelte.js';
  import { PRESETS, DURATIONS } from './songs.js';
  import { fmtDur } from './format.js';

  let { health, onStarted } = $props();

  let prompt = $state('');
  let lyricsVal = $state('');
  let lyricsOpen = $state(false);
  let writing = $state(false);
  let selectedTags = $state(new Set());
  let inst = $state(false);
  let durIdx = $state(1);
  let generating = $state(false);

  // feature: optional title
  let title = $state('');

  // feature: prompt enhancer wand
  let enhancing = $state(false);

  // feature: style wand + preview
  let expanding = $state(false);
  let stylePrompt = $state('');
  let stylePromptTagsKey = $state('');

  // feature: unified styles (curated presets + saved, one chip row)
  let stylePresets = $state(normalizeCurated(PRESETS));
  let savedStyles = $state([]);
  let activeStyleKeys = $state(new Set());
  let stylePromptKey = $state('');
  let saveOpen = $state(false);
  let saveName = $state('');
  let savingStyle = $state(false);
  let removingIds = $state(new Set());
  let nameEl;

  let promptEl;

  const fillPct = $derived((Number(durIdx) / (DURATIONS.length - 1)) * 100);
  const tagsKey = $derived([...selectedTags].sort().join('\u0000'));
  const styleStale = $derived(!!stylePrompt && stylePromptTagsKey !== tagsKey);

  function normalizeCurated(list) {
    return (list || []).map((s, i) => {
      if (typeof s === 'string') return { key: 'curated:' + s, name: s, tags: [s], prompt: '' };
      const tags = Array.isArray(s.tags) ? s.tags : s.tag ? [s.tag] : [];
      return {
        key: 'curated:' + (s.name || tags.join(',') || i),
        name: s.name || tags.join(', ') || 'Untitled style',
        tags,
        prompt: s.prompt || '',
      };
    });
  }

  onMount(() => {
    api
      .get('/api/styles')
      .then((d) => {
        savedStyles = Array.isArray(d && d.saved) ? d.saved : [];
        const curated = normalizeCurated(d && d.styles);
        if (curated.length) stylePresets = curated; // else keep static PRESETS fallback
      })
      .catch(() => {
        /* graceful degradation: static PRESETS chips remain */
      });
  });

  $effect(() => {
    if (saveOpen && nameEl) nameEl.focus();
  });

  function toggleStyle(c, key) {
    const k = key || c.key;
    const next = new Set(activeStyleKeys);
    const tags = new Set(selectedTags);
    if (next.has(k)) {
      next.delete(k);
      for (const t of c.tags || []) tags.delete(t);
      if (stylePromptKey === k) {
        stylePrompt = '';
        stylePromptTagsKey = '';
        stylePromptKey = '';
      }
    } else {
      next.add(k);
      for (const t of c.tags || []) tags.add(t);
      if (c.prompt) {
        stylePrompt = String(c.prompt);
        stylePromptTagsKey = [...tags].sort().join('\u0000');
        stylePromptKey = k;
      }
    }
    activeStyleKeys = next;
    selectedTags = tags;
  }

  async function enhancePrompt() {
    if (!prompt.trim()) {
      toast('Write a few words first', 'err');
      if (promptEl) promptEl.focus();
      return;
    }
    enhancing = true;
    try {
      const data = await api.send('/api/enhance-prompt', 'POST', { prompt: prompt.trim(), tags: [...selectedTags] });
      const p = data && (data.prompt || data.description || '');
      if (p) {
        prompt = String(p).slice(0, 2000);
        toast('Prompt enhanced');
      } else toast('No enhanced prompt returned', 'err');
    } catch (err) { toast('Enhance failed: ' + err.message, 'err'); }
    enhancing = false;
  }

  async function writeLyrics() {
    writing = true;
    try {
      const data = await api.send('/api/lyrics', 'POST', {
        prompt: prompt || 'an uplifting synth-pop song',
        tags: [...selectedTags],
      });
      const lyrics = data && (data.lyrics || data.text || '');
      if (lyrics) {
        lyricsVal = String(lyrics).slice(0, 6000);
        if (!lyricsOpen) lyricsOpen = true;
        toast('Lyrics drafted');
      } else toast('No lyrics returned', 'err');
    } catch (err) { toast('Lyrics failed: ' + err.message, 'err'); }
    writing = false;
  }

  async function expandStyle() {
    expanding = true;
    try {
      const data = await api.send('/api/expand-style', 'POST', { prompt: prompt.trim(), tags: [...selectedTags] });
      const s = data && (data.style || data.style_prompt || '');
      if (s) {
        stylePrompt = String(s);
        stylePromptTagsKey = [...selectedTags].sort().join('\u0000');
        stylePromptKey = '';
        toast('Style expanded');
      } else toast('No style returned', 'err');
    } catch (err) { toast('Expand failed: ' + err.message, 'err'); }
    expanding = false;
  }

  async function saveStyle() {
    const name = saveName.trim();
    if (!name) { toast('Give your style a name', 'err'); if (nameEl) nameEl.focus(); return; }
    savingStyle = true;
    try {
      const created = await api.send('/api/styles', 'POST', {
        name,
        tags: [...selectedTags],
        prompt: stylePrompt && !styleStale ? stylePrompt : '',
      });
      if (created && created.id) savedStyles = [...savedStyles, created];
      toast('Style saved');
      saveOpen = false;
      saveName = '';
    } catch (err) { toast('Save failed: ' + err.message, 'err'); }
    savingStyle = false;
  }

  async function removeStyle(s) {
    removingIds = new Set([...removingIds, s.id]);
    try {
      await api.send('/api/styles/' + encodeURIComponent(s.id), 'DELETE');
      savedStyles = savedStyles.filter((x) => x.id !== s.id);
      const k = 'saved:' + s.id;
      if (activeStyleKeys.has(k)) {
        const next = new Set(activeStyleKeys);
        next.delete(k);
        activeStyleKeys = next;
        const tags = new Set(selectedTags);
        for (const t of s.tags || []) tags.delete(t);
        selectedTags = tags;
      }
      if (stylePromptKey === k) {
        stylePrompt = '';
        stylePromptTagsKey = '';
        stylePromptKey = '';
      }
      toast('Style removed');
    } catch (err) { toast('Remove failed: ' + err.message, 'err'); }
    removingIds = new Set([...removingIds].filter((id) => id !== s.id));
  }

  async function generate() {
    const body = {
      prompt: prompt.trim(),
      lyrics: lyricsVal.trim() || null,
      tags: [...selectedTags],
      instrumental: inst,
      duration_seconds: DURATIONS[Number(durIdx)],
      title: title.trim(),
    };
    if (stylePrompt.trim()) body.style_prompt = stylePrompt.trim();
    if (!body.prompt) { toast('Describe your song first', 'err'); if (promptEl) promptEl.focus(); return; }
    generating = true;
    try {
      const res = await api.send('/api/songs', 'POST', body);
      const gid = res && res.job_group_id;
      if (!gid) throw new Error('no job_group_id in response');
      onStarted(gid);
    } catch (err) {
      toast('Generate failed: ' + err.message, 'err');
    }
    generating = false;
  }
</script>

<header class="view-head">
  <h1 class="display">Create a song</h1>
  <p class="sub">Describe the vibe, pick a style, hit generate. Everything runs on your machine.</p>
</header>

<div class="create-grid">
  <div class="glass card create-card" data-od-id="create-form">
    <div class="section-head">
      <label class="field-label" for="promptInput">Describe your song</label>
      <button class="btn subtle magic-btn" type="button" onclick={enhancePrompt} disabled={enhancing}
        data-od-id="enhance-prompt">
        {#if enhancing}
          <span class="spark" aria-hidden="true">✨</span> Enhancing…
        {:else}
          <span class="spark" aria-hidden="true">✨</span> Enhance prompt
        {/if}
      </button>
    </div>
    <div class="prompt-wrap">
      <textarea id="promptInput" class="prompt-input" rows="4" maxlength="2000" bind:value={prompt} bind:this={promptEl}
        placeholder="A dreamy synth-pop track about driving through neon city rain at 2am, with a soaring chorus and airy female vocals…"
        data-od-id="prompt-input"></textarea>
      <span class="prompt-count" id="promptCount">{prompt.length} / 2000</span>
    </div>

    <div class="lyrics-block" id="lyricsBlock">
      <button class="lyrics-toggle" id="lyricsToggle" aria-expanded={lyricsOpen} data-od-id="lyrics-toggle"
        onclick={() => (lyricsOpen = !lyricsOpen)}>
        <svg class="ico chev" viewBox="0 0 24 24" fill="none"><path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span>Custom lyrics</span>
        <span class="field-hint">optional — leave off to let the model write them</span>
      </button>
      {#if lyricsOpen}
        <div class="lyrics-panel" id="lyricsPanel">
          <div class="lyrics-panel-inner">
            <textarea id="lyricsInput" class="lyrics-input" rows="7" maxlength="6000" bind:value={lyricsVal}
              placeholder="[Verse]&#10;City lights blur past the glass…&#10;&#10;[Chorus]&#10;We run the night, we own the rain…"
              data-od-id="lyrics-input"></textarea>
            <button class="btn subtle magic-btn" id="writeLyricsBtn" type="button" data-od-id="write-lyrics" onclick={writeLyrics} disabled={writing}>
              {#if writing}
                <span class="spark" aria-hidden="true">✨</span> Writing…
              {:else}
                <span class="spark" aria-hidden="true">✨</span> Write lyrics for me
              {/if}
            </button>
            <p class="field-hint" id="lyricsHint">Use [Verse], [Chorus], [Bridge] tags to structure sections.</p>
          </div>
        </div>
      {/if}
    </div>

    <div class="field-row">
      <div class="section-head">
        <span class="field-label" id="styleLabel">Style</span>
        <button class="btn subtle magic-btn" type="button" onclick={expandStyle} disabled={expanding}
          data-od-id="expand-style">
          {#if expanding}
            <span class="spark" aria-hidden="true">✨</span> Expanding…
          {:else}
            <span class="spark" aria-hidden="true">✨</span> Expand style
          {/if}
        </button>
      </div>
      <div class="chip-row" id="styleChips" role="group" aria-labelledby="styleLabel" data-od-id="style-chips">
        {#each stylePresets as c (c.key)}
          <button class="chip" type="button" aria-pressed={activeStyleKeys.has(c.key)}
            onclick={() => toggleStyle(c)}>{c.name}</button>
        {/each}
        {#each savedStyles as s (s.id)}
          <span class="chip saved-chip" class:on={activeStyleKeys.has('saved:' + s.id)}>
            <span class="saved-dot" aria-hidden="true"></span>
            <button class="saved-apply" type="button" onclick={() => toggleStyle(s, 'saved:' + s.id)}>{s.name}</button>
            <button class="saved-remove" type="button" aria-label={'Remove ' + s.name}
              onclick={() => removeStyle(s)} disabled={removingIds.has(s.id)}>×</button>
          </span>
        {/each}
      </div>

      {#if selectedTags.size > 0 || saveOpen}
        <div class="style-save-row">
          <button class="ghost-btn" type="button" onclick={() => (saveOpen = !saveOpen)}
            aria-expanded={saveOpen} data-od-id="save-style-toggle">
            <svg class="ico" viewBox="0 0 24 24" fill="none" style="width:14px;height:14px"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            Save current as style
          </button>
        </div>
      {/if}

      {#if saveOpen}
        <div class="save-panel" data-od-id="save-style-panel">
          <div class="save-panel-inner">
            <label class="field-label" for="styleNameInput">Style name</label>
            <input id="styleNameInput" class="input" type="text" maxlength="60" bind:value={saveName}
              bind:this={nameEl} placeholder="e.g. Late night drive"
              data-od-id="save-style-name" />
            <div class="save-panel-actions">
              <button class="btn primary" type="button" onclick={saveStyle} disabled={savingStyle} data-od-id="save-style-confirm">
                {savingStyle ? 'Saving…' : 'Save style'}
              </button>
              <button class="btn ghost" type="button" onclick={() => (saveOpen = false)}>Cancel</button>
            </div>
            <p class="field-hint">Saves the selected tags{stylePrompt && !styleStale ? ' and the expanded style prompt' : ''}.</p>
          </div>
        </div>
      {/if}

      {#if stylePrompt}
        <div class="style-preview" class:stale={styleStale} data-od-id="style-prompt-preview">
          <span class="style-preview-label">Style prompt</span>
          <p class="style-preview-text">{stylePrompt}</p>
          {#if styleStale}
            <span class="style-preview-stale">tags changed — expand again to refresh</span>
          {/if}
        </div>
      {/if}
    </div>

    <div class="control-row">
      <div class="control-block" data-od-id="instrumental-toggle">
        <span class="field-label" id="instLabel">Instrumental</span>
        <button class="switch" role="switch" aria-checked={inst} aria-labelledby="instLabel" data-od-id="instrumental-switch"
          onclick={() => (inst = !inst)}>
          <span class="knob"></span>
        </button>
      </div>
      <div class="control-block control-block-grow" data-od-id="duration-slider">
        <div class="slider-head">
          <span class="field-label" id="durLabel">Duration</span>
          <span class="duration-readout" id="durationReadout">{fmtDur(DURATIONS[Number(durIdx)])}</span>
        </div>
        <input type="range" id="durationSlider" class="range" min="0" max="4" step="1" bind:value={durIdx}
          style="--fill: {fillPct}%" aria-labelledby="durLabel" />
        <div class="range-marks" id="rangeMarks" aria-hidden="true">
          <span>15s</span><span>30s</span><span>1m</span><span>2m</span><span>4m</span>
        </div>
      </div>
    </div>

    <div class="field-row title-row" data-od-id="title-field">
      <label class="field-label" for="titleInput">Title</label>
      <input id="titleInput" class="input" type="text" maxlength="120" bind:value={title}
        placeholder="Leave blank and we'll name it" data-od-id="title-input" />
    </div>

    <div class="cta-row">
      <button class="btn primary btn-generate" id="generateBtn" data-od-id="generate-cta" onclick={generate} disabled={generating}>
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M9 18V6l10.5-2.5v11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6.5" cy="18" r="3" stroke="currentColor" stroke-width="2"/><circle cx="17" cy="14.5" r="3" stroke="currentColor" stroke-width="2"/></svg>
        <span id="generateLabel">{generating ? 'Starting…' : 'Generate'}</span>
      </button>
      <p class="cta-hint" data-od-id="variations-hint">
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v2m0 14v2m9-9h-2M5 12H3m14.5-6.5-1.4 1.4M7.9 16.1l-1.4 1.4m0-11 1.4 1.4m8.2 8.2 1.4 1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="12" r="3.4" stroke="currentColor" stroke-width="1.8"/></svg>
        1 variation is created per request
      </p>
    </div>
  </div>

  <aside class="create-side">
    <div class="glass card tip-card" data-od-id="tip-card">
      <h3>Pro tips</h3>
      <ul class="tip-list">
        <li><strong>Be specific.</strong> Mood, tempo, instruments and vocal style all land in the model.</li>
        <li><strong>Stack tags.</strong> Chips append to your prompt — combine “lo-fi” with “jazz”.</li>
        <li><strong>Structure lyrics.</strong> [Chorus] tags keep hooks repeating where they should.</li>
      </ul>
    </div>
  </aside>
</div>
