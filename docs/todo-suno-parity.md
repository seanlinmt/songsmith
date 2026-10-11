# Songsmith — TODO: Suno-parity gaps

Derived from `docs/suno-apk-analysis.md` (Suno v1.92.0 APK reverse engineering).
Ordered by impact; each item names the Suno mechanism it mirrors.

## High impact

- [x] **Pass genre/style into lyrics generation** — Suno sends `tags` in
  `GenLyricsSpec`, so lyrics match the genre. Songsmith's `llm.generate_lyrics`
  is currently genre-blind. Thread the song's style string into the lyrics
  prompt, and instruct the GLM to emit `[verse]` / `[chorus]` structure tags
  (Suno lyrics carry these; ACE-Step consumes them).
- [x] **Style tag expansion step** — mirror Suno's `generate/upsample-tags/`:
  a GLM call that expands short user style tags ("rock, energetic") into a rich
  ACE-Step style description, plus generates `negative_tags` (styles to avoid).
  Run it before `music.generate` and cache the expanded form on the song row.
- [x] **Richer cover-art prompt** — Suno builds covers from a dedicated prompt
  (`gen/prompt_image/`), not the raw generation prompt. Build the cover prompt
  from title + genre + lyric summary, and store `image_url`/`image_large_url`-style
  fields so the UI can serve multiple sizes later.
- [x] **Adopt Suno's snake_case API contract** — rename `/api/songs` payload
  fields to the proven `GenParamsSpec` wire names (`prompt`, `tags`,
  `negative_tags`, `make_instrumental`, `batch_size`, `title`) for contract
  parity and easier future proxying.

## Medium impact

- [x] **Curated style list + saved styles** — Suno exposes
  `generate/get_recommend_styles/` (curated suggestions) and `prompts/v2`
  (persisted user styles). Add a static recommended-styles list to
  `/api/config`, and a `styles` table in SQLite so users can save/reuse styles.
- [x] **Generation-control knobs** — Suno's `CreatePromptForm` exposes style
  influence, weirdness, audio influence, variety, and vocal gender. Map these
  to ACE-Step parameters where supported (seed, CFG/guidance, steps) and expose
  vocal gender in the prompt (e.g. "male vocals"/"female vocals").
- [x] **Align extend with Suno's continue semantics** — Suno uses
  `continue_clip_id` + `continue_at` and infill windows
  (`infill_start_s`/`infill_end_s`) for partial regeneration. Keep the existing
  extend endpoint but adopt the naming and plan partial-window regeneration.
- [x] **Status vocabulary parity** — use Suno's clip status lifecycle
  (`submitted` → `queued` → `streaming` → `complete` / `error`) in job/queue
  events so client polling mirrors Suno's.

## Low impact / later

- [x] **Word-level lyric timing** — Suno serves `aligned_lyrics/v2`
  (per-word timestamps). If ACE-Step can emit timestamps, add karaoke-style
  display; otherwise approximate per-line timing.
- [x] **Iterative lyric projects** — mirror `lyrics-projects` +
  `flush`: allow editing lyrics and re-flushing to the music model without
  regenerating from scratch.
- [ ] **Multi-size media handling** — Suno clips carry `media_urls[{url,
  content_type, delivery, encoding}]`; if songsmith later serves multiple
  formats, adopt the same media-url list shape.
- [ ] **Upsample pass** — Suno's `generate/upsample/` raises final audio
  quality; consider a post-processing stage for ACE-Step output if quality
  becomes a complaint.
