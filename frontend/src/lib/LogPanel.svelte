<script>
  import { fly } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  let {
    open = false,
    lines = [],
    newCount = 0,
    buffered = 0,
    onClose,
    onSave,
    onAtBottom,
  } = $props();

  /* ---------------- scroll behaviour ---------------- */
  let bodyEl = $state();
  let atBottom = $state(true);

  function isAtBottom() {
    if (!bodyEl) return true;
    return bodyEl.scrollHeight - bodyEl.scrollTop - bodyEl.clientHeight < 32;
  }

  function onScroll() {
    const b = isAtBottom();
    if (b !== atBottom) {
      atBottom = b;
      onAtBottom?.(b);
    }
  }

  function jumpToBottom() {
    if (!bodyEl) return;
    bodyEl.scrollTop = bodyEl.scrollHeight;
    if (!atBottom) {
      atBottom = true;
      onAtBottom?.(true);
    }
  }

  // When the panel opens, pin to the tail once layout has settled.
  $effect(() => {
    if (open) {
      const raf = requestAnimationFrame(() => {
        jumpToBottom();
      });
      return () => cancelAnimationFrame(raf);
    }
  });

  // While pinned to the bottom, keep the newest lines in view.
  $effect(() => {
    if (open && atBottom && bodyEl && lines.length) {
      bodyEl.scrollTop = bodyEl.scrollHeight;
    }
  });

  /* ---------------- line rendering ---------------- */
  function lineClass(l) {
    const lv = String(l.level || '').toUpperCase();
    if (lv.startsWith('ERR') || lv === 'CRITICAL' || lv === 'FATAL') return 'log-line lvl-err';
    if (lv.startsWith('WARN')) return 'log-line lvl-warn';
    if (lv === 'DEBUG') return 'log-line lvl-debug';
    return 'log-line lvl-info';
  }

  const reducedMotion =
    typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const slideDur = reducedMotion ? 0 : 240;
</script>

{#if open}
  <div class="log-panel" role="dialog" aria-label="Server logs" aria-modal="false"
    transition:fly={{ x: 480, duration: slideDur, easing: cubicOut }}>
    <header class="log-head">
      <div class="log-head-titles">
        <h2 class="log-title">Server logs</h2>
        <span class="log-hint mono">since last restart</span>
      </div>
      <span class="log-count mono dim">{lines.length} lines</span>
    </header>

    <div class="log-body-wrap">
      <div class="log-body" bind:this={bodyEl} onscroll={onScroll}>
        {#if lines.length === 0}
          <div class="log-empty">No lines yet — the buffer holds everything since the last restart.</div>
        {:else}
          {#each lines as l (l.seq)}
            <div class={lineClass(l)}>
              <div class="log-line-head">
                <span class="log-ts mono">{l.ts}</span>
                <span class="log-lv mono">{l.level}</span>
                <span class="log-name mono">{l.name}</span>
              </div>
              <div class="log-msg">{l.msg}</div>
            </div>
          {/each}
        {/if}
      </div>
      {#if newCount > 0}
        <button class="log-new-btn" onclick={jumpToBottom} title="Jump to newest lines">
          ↓ {newCount} new line{newCount === 1 ? '' : 's'}
        </button>
      {/if}
    </div>

    <footer class="log-foot">
      <span class="log-buffered mono">buffered: {buffered}</span>
      <div class="log-foot-actions">
        <button class="btn ghost" onclick={() => onClose?.()}>Cancel</button>
        <button class="btn primary" onclick={() => onSave?.()}>Export</button>
      </div>
    </footer>
  </div>
{/if}

<style>
  .log-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(480px, 92vw);
    z-index: 60; /* above topnav (40), below song modal (100) */
    display: flex;
    flex-direction: column;
    background: var(--input-bg);
    border-left: 1px solid var(--border-strong);
    box-shadow: var(--shadow-lg);
  }

  /* ---------- header ---------- */
  .log-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 18px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .log-head-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .log-title {
    margin: 0;
    font: 700 14px/1.2 var(--font-display);
    color: var(--text);
    letter-spacing: 0.01em;
  }
  .log-hint { font-size: 11px; color: var(--text-faint); }
  .log-count { font-size: 11.5px; flex: none; }

  /* ---------- body ---------- */
  .log-body-wrap { position: relative; flex: 1; min-height: 0; }
  .log-body {
    position: absolute;
    inset: 0;
    overflow-y: auto;
    padding: 12px 14px 20px;
    font: 400 11.5px/1.65 var(--mono);
    overscroll-behavior: contain;
  }
  .log-line {
    padding: 1px 0;
    word-break: break-word;
  }
  .log-line:hover { background: rgba(255, 255, 255, 0.025); }
  .log-line-head {
    display: flex;
    gap: 8px;
    align-items: baseline;
  }
  .log-ts { flex: none; color: var(--text-faint); font-variant-numeric: tabular-nums; }
  .log-lv { flex: none; width: 62px; font-weight: 600; }
  .log-name { flex: none; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .log-msg { color: var(--text); min-width: 0; padding-left: 58px; }
  .lvl-err .log-lv { color: var(--err); }
  .lvl-err .log-msg { color: var(--err); }
  .lvl-warn .log-lv { color: var(--warn); }
  .lvl-warn .log-msg { color: var(--warn); }
  .lvl-info .log-lv { color: var(--text-faint); }
  .lvl-info .log-msg { color: var(--text); }
  .lvl-info .log-name { color: var(--text-faint); }
  .lvl-debug .log-lv,
  .lvl-debug .log-msg { color: var(--text-faint); }
  .log-empty {
    padding: 24px 6px;
    font: 400 12px/1.6 var(--font);
    color: var(--text-faint);
  }

  /* ---------- new-lines affordance ---------- */
  .log-new-btn {
    position: absolute;
    right: 16px;
    bottom: 12px;
    padding: 6px 12px;
    border-radius: 999px;
    background: var(--surface-3);
    border: 1px solid var(--accent-border);
    color: var(--accent);
    font: 600 11.5px/1 var(--font);
    cursor: pointer;
    box-shadow: var(--shadow);
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  }
  .log-new-btn:hover {
    background: var(--accent-subtle);
    border-color: var(--accent);
    color: var(--accent-hover);
  }

  /* ---------- footer ---------- */
  .log-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 18px;
    background: var(--surface);
    border-top: 1px solid var(--border);
  }
  .log-buffered { font-size: 11px; color: var(--text-faint); }
  .log-foot-actions { display: flex; gap: 8px; }
  .log-foot-actions .btn { height: 34px; padding: 0 14px; font-size: 12.5px; }
</style>
