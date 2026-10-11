<script>
  import { api } from './api.js';
  import { toast } from './toast.svelte.js';
  import { PRESETS, DURATIONS } from './songs.js';

  let { health, onStarted } = $props();

  let prompt = $state('');
  let lyricsVal = $state('');
  let lyricsOpen = $state(false);
  let writing = $state(false);
  let selectedTags = $state(new Set());
  let inst = $state(false);
  let durIdx = $state(1);
  let generating = $state(false);

  let promptEl;

  const fillPct = $derived((Number(durIdx) / (DURATIONS.length - 1)) * 100);

  function toggleTag(tag) {
    const on = selectedTags.has(tag);
    if (on) selectedTags.delete(tag);
    else selectedTags.add(tag);
  }

  async function writeLyrics() {
    writing = true;
    try {
      const data = await api.send('/api/lyrics', 'POST', { prompt: prompt || 'an uplifting synth-pop song' });
      const lyrics = data && (data.lyrics || data.text || '');
      if (lyrics) {
        lyricsVal = String(lyrics).slice(0, 6000);
        if (!lyricsOpen) lyricsOpen = true;
        toast('Lyrics drafted');
      } else toast('No lyrics returned', 'err');
    } catch (err) { toast('Lyrics failed: ' + err.message, 'err'); }
    writing = false;
  }

  async function generate() {
    const body = {
      prompt: prompt.trim(),
      lyrics: lyricsVal.trim() || null,
      tags: [...selectedTags],
      instrumental: inst,
      duration_seconds: DURATIONS[Number(durIdx)],
    };
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
    <label class="field-label" for="promptInput">Describe your song</label>
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
            <button class="btn subtle magic-btn" id="writeLyricsBtn" data-od-id="write-lyrics" onclick={writeLyrics} disabled={writing}>
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
      <span class="field-label" id="styleLabel">Style</span>
      <div class="chip-row" id="styleChips" role="group" aria-labelledby="styleLabel" data-od-id="style-chips">
        {#each PRESETS as p (p.tag)}
          <button class="chip" type="button" aria-pressed={selectedTags.has(p.tag)} data-tag={p.tag} onclick={() => toggleTag(p.tag)}>{p.tag}</button>
        {/each}
      </div>
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
          <span class="duration-readout" id="durationReadout">{DURATIONS[Number(durIdx)]}s</span>
        </div>
        <input type="range" id="durationSlider" class="range" min="0" max="3" step="1" bind:value={durIdx}
          style="--fill: {fillPct}%" aria-labelledby="durLabel" />
        <div class="range-marks" id="rangeMarks" aria-hidden="true">
          <span>15s</span><span>30s</span><span>60s</span><span>120s</span>
        </div>
      </div>
    </div>

    <div class="cta-row">
      <button class="btn primary btn-generate" id="generateBtn" data-od-id="generate-cta" onclick={generate} disabled={generating}>
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M9 18V6l10.5-2.5v11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6.5" cy="18" r="3" stroke="currentColor" stroke-width="2"/><circle cx="17" cy="14.5" r="3" stroke="currentColor" stroke-width="2"/></svg>
        <span id="generateLabel">{generating ? 'Starting…' : 'Generate'}</span>
      </button>
      <p class="cta-hint" data-od-id="variations-hint">
        <svg class="ico" viewBox="0 0 24 24" fill="none"><path d="M12 3v2m0 14v2m9-9h-2M5 12H3m14.5-6.5-1.4 1.4M7.9 16.1l-1.4 1.4m0-11 1.4 1.4m8.2 8.2 1.4 1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="12" r="3.4" stroke="currentColor" stroke-width="1.8"/></svg>
        2 variations are created per request
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
    <div class="glass card health-mini" data-od-id="health-mini" id="healthMini">
      <div class="health-mini-row">
        <span class="status-dot" data-state={health.mini.state} id="miniDot"></span>
        <span id="healthMiniText">{health.mini.text}</span>
      </div>
      <p class="field-hint" id="healthMiniErr" hidden={!health.mini.err}>{health.mini.err}</p>
    </div>
  </aside>
</div>
