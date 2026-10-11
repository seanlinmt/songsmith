# Suno Android APK — Reverse-Engineering Notes

Source: Suno v1.92.0 (`com.suno.android`) XAPK from APKPure, downloaded 2026-10-11.
Method: APK unzipped (split `com.suno.android.apk` + `config.arm64_v8a.apk`); all 5 DEX
files imported into Ghidra (`Dalvik:LE:32:DEX_Android12`) and decompiled with jadx.
The app is Kotlin/Compose; all server-contract logic lives in
`com.suno.android.common_networking.remote.*` and `com.suno.android.common_data.*`.

## Backend topology

| Component | URL |
|---|---|
| API base (staging seen in code) | `https://studio-api-staging.suno.com/api/` |
| Media CDN | `cdn2.suno.ai/`, `cdn1.suno.ai/`, `cdn-e.suno.com/`, `cdn-o.suno.com/`, `b.suno.fm` |
| Captcha | hCaptcha (`js.hcaptcha.com`) |
| Subscriptions | RevenueCat |
| Feature flags | Statsig |
| Analytics/CRM | Datadog, Braze, Singular |

## Core API surface (`GenerateService`)

| Method + path | Body → Response | Purpose |
|---|---|---|
| `POST generate/v2/` | `GenParamsSpec` → `GenerationRequestSchema` | **Main song generation** |
| `POST generate/lyrics/` | `GenLyricsSpec` → `GenLyricsRequestId` | Start lyrics generation (async) |
| `GET generate/lyrics/{request_id}` | → `GenLyricsSchema` | Poll lyrics result |
| `POST generate/upsample/` | `GenUpsampleSpec` → `GenUpsampleSchema` | Upsample audio quality |
| `POST generate/upsample-tags/` | `GenUpsampleTagsSpec` | AI-expands short style tags into rich styles |
| `POST generate/concat/` (+ `/v2/`) | `GenConcatSpec` → `RemoteClip` | Merge/concatenate clips |
| `GET generate/clip/{clip_id}` | → `RemoteClip` | Fetch one song |
| `GET generate/requests/` | paginated | User's generation history |
| `GET generate/get_recommend_styles/` | → `RecommendStylesSchema` | Curated style suggestions |
| `POST gen/prompt_image/` | `PromptImageBody{prompt}` → `{image_url, upload_id}` | **AI cover-art generation from text** |
| `POST gen/{gen_id}/set_metadata/` | `ClipMetadataSpec` | Edit title/tags after generation |
| `POST gen/{gen_id}/set_clip_prompt/` | `UpdatedClipPromptSpec` | Edit prompt after generation |
| `GET gen/{clip_id}/aligned_lyrics/v2` | → `AlignedLyricsSchema` | Word-level lyric timing (karaoke) |
| `POST external/generate/` | `ExternalGenerationSpec{topic, tags, extra}` | Prompt-topic driven generation |
| `POST uploads/image/` + `POST uploads/image/{id}/upload-finish/` | | User-uploaded cover images |
| `POST uploads/audio/` (+ initialize-clip) | | Voice cloning / audio upload |
| `GET/POST prompts/v2` | `SavedStylesService` | Save/reuse user styles |
| `POST lyrics-projects`, `POST lyrics-projects/{id}/flush` | | Multi-step lyric editing projects |
| `POST video/generate/{clip_id}/` | | Video cover generation (hooks pipeline) |

## `GenParamsSpec` — the generation payload (snake_case on the wire)

```
prompt                    # lyrics or custom-mode prompt
gpt_prompt                # "describe the song" prompt (simple mode)
gpt_description_prompt    # human description of intent
tags                      # genre/style string, e.g. "rock, energetic, powerful"
negative_tags             # styles to avoid
attached_lyrics           # pre-existing lyrics attached to the request
attached_styles           # style strings attached (e.g. from a remix)
title                     # song title
task                      # task kind (e.g. "speech", remix task)
mv                        # model version, internal names: chirp-v3, chirp-goose, chirp-hawk
batch_size                # 2 variations per request (Suno default)
make_instrumental         # bool
stream                    # streaming generation
persona_id, persona_voice_ref   # voice/persona reuse
cover_clip_id             # covering another song
continue_clip_id, continue_at   # extend a song from timestamp
infill_start_s, infill_end_s    # partial regeneration window
audio_refs                # GenAudioRefSpec list (reference audio)
user_uploaded_image_ids / user_uploaded_images_b64 / user_uploaded_video_id
artist_clip_id            # artist style reference
override_fields           # list of fields server shouldn't override
generation_type           # TEXT | AUDIO | IMAGE | VIDEO | SIMPLE_REMIX
creation_source           # which UI surface launched it
is_regenerate, is_remix, hybrid_rewrite
project_id, themed_creation_id, token
```

## UI form model (`CreatePromptForm`) — maps onto the above

`prompt, tags, negativeStyle, title, model, isCustom, isInstrumental,
vocalGender, styleInfluenceValue (Double), weirdnessValue (Double),
audioInfluenceValue (Double), varietyValue (Int), generationType,
gptDescriptionPrompt, hybridRewrite, voice (VoicePersona), projectId,
themedCreationId, speech (SpeechPromptForm), source`

Notable sliders: **style influence**, **weirdness**, **audio influence**, **variety**,
plus **vocal gender**. Simple mode = only `gptDescriptionPrompt`; custom mode =
`prompt` (lyrics) + `tags` (style).

## Song entity (`RemoteClip`)

Fields the client renders: `id, title, status, audio_url, image_url,
image_large_url, video_cover_url, preview_url, media_urls[{url, content_type,
delivery, encoding}], lyrics (via metadata), prompt, gpt_prompt, tags,
display_tags, model_name, major_model_version, duration, persona,
play_count, comment_count, upvote_count, created_at, user_id` — metadata
carries `control_sliders` and `cover_clip_id`.

## Lyrics model

- Lyrics are **generated separately from music**: `GenLyricsSpec{prompt, gen_type:
  "full", tags, make_instrumental}` → poll `GET generate/lyrics/{request_id}`.
  The `tags` (genre) are passed into the lyrics request — genre shapes lyrics.
- Lyrics use structure tags like `[verse]`, `[chorus]` inside the text.
- `lyrics-projects` support iterative lyric editing (`flush` = finalize).
- Word-level timing available via `aligned_lyrics/v2` (`Lyrics{Line, Word}`).
- AI lyric rewriting (`ask_suno`: `RemoteRewriteLyricsResponse`,
  `RemoteRewriteStylesBody` rewrites styles too).

## Cover art flow

1. AI cover: `POST gen/prompt_image/` with a text prompt → `{image_url, upload_id}`.
   Covers live on the CDN (`cdn2.suno.ai/…jpeg`); clip exposes `image_url` /
   `image_large_url`.
2. User upload: `uploads/image/` → `upload-finish/`.
3. Video cover: `video/hooks/*` pipeline + `FinishVideoCoverUploadSpec`.
4. Album references: `RemoteClipAlbumRef` list on each clip.

## Model versions

Internal codenames `chirp-v3`, `chirp-goose`, `chirp-hawk`; public
`major_model_version` like `v6`. Billing `Model` entity exposes
`id, name, majorVersion, inputLimits, style, features, isDefaultModel`.

## Mappings → Songsmith improvements

| Suno mechanism | Songsmith change |
|---|---|
| Lyrics generated with genre `tags` passed in | `llm.generate_lyrics` should receive style/genre so lyrics match genre (currently genre-blind) |
| `generate/upsample-tags/` expands short style tags | Add a GLM step that expands user style tags into a rich ACE-Step style description; also produce `negative_tags` |
| `get_recommend_styles/` + saved styles (`prompts/v2`) | Serve a curated style list from `/api/config` and persist user styles in SQLite |
| `gen/prompt_image/` cover from prompt | Build cover prompt from title + genre + lyric summary, not just the raw prompt; store `image_url`/`image_large_url` style fields |
| `batch_size: 2` two variations | Already implemented (2 per job group) — matches Suno |
| Sliders: style influence / weirdness / variety | Expose as songsmith UI knobs; map to ACE-Step seed/CFG/steps where supported |
| `vocal_gender` | Pass through to ACE-Step prompt (e.g. "male vocals" / "female vocals") |
| `continue_clip_id` + `continue_at`, infill window | Matches existing extend feature — align naming and add partial-window regeneration later |
| `aligned_lyrics/v2` word timing | If ACE-Step exposes timestamps, add karaoke-style lyric display; otherwise approximate by line |
| Clip status lifecycle (`status`, streaming) | Keep job-status polling; use Suno's status vocabulary (`submitted/queued/streaming/complete/error`) for client parity |
| Snake_case API contract (`GenParamsSpec`) | Adopt snake_case field names in `/api/songs` payloads for proven-contract parity |
