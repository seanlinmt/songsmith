<script>
  import { STAGES, stageFromJob } from './songs.js';
  import { clamp } from './format.js';

  let { jobs = [], activeGroup = null, onAbandon } = $props();

  const cards = $derived.by(() => {
    let list = jobs && jobs.length ? jobs.slice() : null;
    if (!list) {
      list = [0].map(() => ({ id: null, stage: 'queued' }));
      if (!activeGroup) return [];
    }
    return list.map((job, idx) => {
      const done = job && (String(job.status || '').toLowerCase() === 'complete' || String(job.status || '').toLowerCase() === 'completed');
      const failed = job && ['failed', 'error', 'cancelled'].includes(String(job.status || '').toLowerCase());
      const stageIdx = clamp(stageFromJob(job), 0, STAGES.length - 1);
      let statusLabel, subLabel, pct;
      if (done) {
        statusLabel = 'Complete';
        subLabel = 'Saved to Library';
        pct = 100;
      } else if (failed) {
        statusLabel = 'Failed';
        subLabel = job.error || job.message || 'Something went wrong';
        pct = 100;
      } else {
        statusLabel = STAGES[stageIdx].label;
        subLabel = 'variation ' + (idx + 1) + ' · step ' + (stageIdx + 1) + ' / ' + STAGES.length;
        pct = Math.round(((stageIdx + 0.35) / STAGES.length) * 100);
      }
      return { job, idx, done, failed, statusLabel, subLabel, pct };
    });
  });

  /* random mini-waveform bars — regenerated once per render (like the vanilla innerHTML reset) */
  function miniWaveBars() {
    const arr = [];
    for (let i = 0; i < 14; i++) {
      arr.push({
        h: Math.round(10 + Math.random() * 34),
        delay: (Math.random() * -1.1).toFixed(2),
        dur: (0.7 + Math.random() * 0.65).toFixed(2),
      });
    }
    return arr;
  }

  const waveBars = $derived(cards.map(() => miniWaveBars()));
</script>

<header class="view-head">
  <h1 class="display">Cooking your song</h1>
  <p class="sub">{cards.length === 1 ? 'One variation is on the way — hang tight.' : cards.length + ' variations are on the way — hang tight.'}</p>
</header>
<div class="progress-grid" id="progressGrid" data-od-id="progress-grid">
  {#each cards as c, idx (c.job && c.job.id != null ? c.job.id : 'ph-' + idx)}
    <div class="studio-panel card skeleton-card" data-od-id={'progress-card-' + (idx + 1)}>
      <div class="skeleton-cover">
        <div class="wave-mini">
          {#each waveBars[idx] as b}
            <i style={'height:' + b.h + 'px;animation-delay:' + b.delay + 's;animation-duration:' + b.dur + 's'}></i>
          {/each}
        </div>
      </div>
      <div class="skeleton-body">
        {#if !c.done}
          <div class="skeleton-line" style="width:72%"></div>
          <div class="skeleton-line" style="width:46%; margin-bottom:16px"></div>
        {/if}
        <div class="progress-card-status">
          <span class="status-dot" data-state={c.failed ? 'error' : c.done ? 'ok' : 'busy'}></span>
          <div>
            <div class="progress-status-text">{c.statusLabel}</div>
            <div class="progress-sub">{c.subLabel}</div>
          </div>
        </div>
        <div class="progress-track"><div class="progress-bar" style={'width:' + c.pct + '%'}></div></div>
      </div>
    </div>
  {/each}
</div>
<div class="progress-foot">
  <button class="ghost-btn" id="cancelPollBtn" onclick={onAbandon}>Keep this tab, check Library later</button>
</div>
