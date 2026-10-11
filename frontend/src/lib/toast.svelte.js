/* Toast state for Songsmith (Svelte 5 runes module — .svelte.js extension required). */

export const TICK_OK = '<svg class="tico" viewBox="0 0 24 24" fill="none"><path d="m5 13 4 4L19 7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
export const TICK_ERR = '<svg class="tico" viewBox="0 0 24 24" fill="none"><path d="M12 8v5m0 3.5v.01" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.8"/></svg>';

export const toasts = $state([]);

let uid = 0;

export function toast(msg, type, ms) {
  const id = ++uid;
  toasts.push({
    id,
    msg,
    type: type || "ok",
    svg: type === "err" ? TICK_ERR : TICK_OK,
    leaving: false,
  });
  setTimeout(() => {
    const t = toasts.find((x) => x.id === id);
    if (t) t.leaving = true;
    setTimeout(() => {
      const i = toasts.findIndex((x) => x.id === id);
      if (i >= 0) toasts.splice(i, 1);
    }, 260);
  }, ms || 3400);
}
