"""GLM lyric/title/tag generation via an OpenAI-compatible chat API.

Verified (docs/api-notes.md): /v1/chat/completions with GLM-5.3-Flash-EXL3 is
sub-second decode but can queue ~50s under load — keep timeouts >= 120s.
"""
import logging

import httpx

from . import config

log = logging.getLogger("songsmith.llm")

# Shared server: queue waits vary 50s -> several minutes under load. Be generous.
_TIMEOUT = httpx.Timeout(900.0, connect=10.0)

LYRICS_SYSTEM = (
    "You are a professional songwriter. First line of your reply must be "
    "`Title: <short song title>` (max 5 words, no quotes). Then write the "
    "complete song lyrics for the user's description. Use only structural "
    "section tags on their own lines like [Verse], [Chorus], [Bridge], "
    "[Outro] followed by the lyric lines. Do not add commentary, "
    "explanations, or anything besides the title line and tagged sections."
)


def _split_title(content: str) -> tuple[str, str | None]:
    if content.lower().startswith("title:"):
        first, _, rest = content.partition("\n")
        title = first.split(":", 1)[1].strip().strip('"')
        return rest.strip(), title or None
    return content, None


def _llm_headers() -> dict:
    return {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}


async def _chat(client: httpx.AsyncClient, messages: list[dict],
                temperature: float = 0.9) -> tuple[str, int | None]:
    """Returns (content, total_tokens) — total_tokens is None when the API
    omits usage data."""
    resp = await client.post(
        f"{config.LLM_URL}/v1/chat/completions",
        json={
            "model": config.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage") or {}
    total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    return (data["choices"][0]["message"]["content"] or "").strip(), total_tokens


def _lyrics_length_hint(duration_seconds: int) -> str:
    """Human hint telling the LLM how many lyric lines fit the runtime.

    Rule of thumb: one sung line ≈ 4-5 s of music.
    """
    lines = max(4, round(duration_seconds / 4.5))
    minutes = duration_seconds / 60
    return (
        f"The song must run about {duration_seconds} seconds "
        f"(~{minutes:.0f} minutes), so write roughly {lines} lyric lines "
        "of actual sung text (section tags don't count), ending with a "
        "repeated final chorus to fill the runtime."
    )


async def generate_lyrics(prompt: str, tags: list[str] | None = None,
                          duration_seconds: int | None = None) -> tuple[str, str | None, int | None]:
    """Returns (lyrics, title, usage) — title/usage may be None if the model
    skipped the title or the API omitted usage."""
    user_content = prompt
    if duration_seconds:
        user_content = f"{user_content}\n\n{_lyrics_length_hint(duration_seconds)}"
    if tags:
        user_content = f"{user_content}\n\nStyle/genre: {', '.join(tags)}"
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            content, usage = await _chat(client, [
                {"role": "system", "content": LYRICS_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            lyrics, title = _split_title(content)
            return lyrics, title, usage
    except httpx.TimeoutException as exc:
        raise RuntimeError("LLM busy: request timed out, try again shortly") from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(f"LLM unreachable at {config.LLM_URL}") from exc


TITLE_SYSTEM = (
    "You name songs. Reply with ONLY a short song title (max 5 words), "
    "no quotes, no punctuation at the end, no explanation."
)


async def generate_title(prompt: str, lyrics: str,
                         tags: list[str] | None = None) -> tuple[str | None, int | None]:
    """Returns (title, usage) — both None if generation failed."""
    content = f"Song description: {prompt}\n\nLyrics:\n{lyrics[:2000]}"
    if tags:
        content = f"{content}\n\nStyle/genre: {', '.join(tags)}"
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            return await _chat(client, [
                {"role": "system", "content": TITLE_SYSTEM},
                {"role": "user", "content": content},
            ], temperature=0.7)
    except Exception:
        log.exception("title generation failed")
        return None, None


ENHANCE_SYSTEM = (
    "You rewrite short song descriptions into vivid scene-setting descriptions "
    "for a text-to-music model. Write 2-4 sentences describing the song's "
    "mood, genre, instrumentation, tempo, and production style. This is a "
    "description, NOT lyrics: no titles, no quoted text, no section tags, no "
    "explanation. Reply with ONLY the description."
)


async def enhance_description(prompt: str,
                              tags: list[str] | None = None) -> tuple[str | None, int | None]:
    """Expand a short user description into a rich prompt for the music model."""
    user_content = prompt
    if tags:
        user_content = f"{prompt}\n\nStyle/genre: {', '.join(tags)}"
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            content, usage = await _chat(client, [
                {"role": "system", "content": ENHANCE_SYSTEM},
                {"role": "user", "content": user_content},
            ], temperature=0.7)
        return " ".join(content.strip().strip('"').split()) or None, usage
    except httpx.TimeoutException as exc:
        raise RuntimeError("LLM busy: request timed out, try again shortly") from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(f"LLM unreachable at {config.LLM_URL}") from exc


STYLE_SYSTEM = (
    "You expand short music style tags into a rich description for a "
    "text-to-music model, and pick clashing styles to avoid. Reply in EXACTLY "
    "this format, nothing else:\n"
    "Style: <one vivid style description, max 40 words, for a text-to-music "
    "model>\n"
    "Avoid: <comma-separated list of 2-5 styles/moods that would clash>"
)


def _parse_style_reply(content: str) -> tuple[str, list[str]] | None:
    """Case-insensitive parse of the `Style:` / `Avoid:` reply format."""
    style = avoid = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("style:") and not style:
            style = line.split(":", 1)[1].strip().strip('"')
        elif low.startswith("avoid:") and not avoid:
            avoid = line.split(":", 1)[1].strip()
    if not style:
        return None
    neg = [t.strip() for t in avoid.split(",") if t.strip()] if avoid else []
    return style, neg


async def expand_style(prompt: str, tags: list[str]) -> tuple[str, list[str], int | None]:
    """Best-effort: expand tags into a rich style description + negative tags.

    Returns (style_prompt, negative_tags, usage); on any failure falls back to
    (", ".join(tags), [], None). usage is None when the API omitted it.
    """
    fallback = (", ".join(tags), [])
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            content, usage = await _chat(client, [
                {"role": "system", "content": STYLE_SYSTEM},
                {"role": "user", "content": f"Song description: {prompt}\n\nStyle tags: {', '.join(tags)}"},
            ], temperature=0.5)
        parsed = _parse_style_reply(content)
        if parsed is None:
            style, neg = fallback
        else:
            style, neg = parsed
        return style, neg, usage
    except Exception:
        log.exception("style expansion failed")
        return fallback[0], fallback[1], None


COVER_SCENE_SYSTEM = (
    "You describe a single striking photograph for a song's album cover. "
    "Reply with ONLY a vivid visual scene description (max 40 words): subject, "
    "setting, mood, lighting. No song lyrics, no quoted text, no titles, no "
    "camera jargon, no explanation."
)


async def describe_cover_scene(lyrics: str | None, prompt: str | None,
                               tags: list[str] | None = None) -> str | None:
    """Best-effort: condense lyrics/description into a visual scene for the
    image model. Returns None on any failure."""
    if not (lyrics or prompt):
        return None
    parts = []
    if prompt:
        parts.append(f"Song description: {prompt}")
    if lyrics:
        parts.append(f"Lyrics:\n{lyrics[:2000]}")
    if tags:
        parts.append(f"Style: {', '.join(tags)}")
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            content, _usage = await _chat(client, [
                {"role": "system", "content": COVER_SCENE_SYSTEM},
                {"role": "user", "content": "\n\n".join(parts)},
            ], temperature=0.6)
        scene = " ".join(content.strip().strip('"').split())
        return scene or None
    except Exception:
        log.exception("cover scene description failed")
        return None


async def check_health() -> dict:
    try:
        async with httpx.AsyncClient(headers=_llm_headers()) as client:
            resp = await client.get(f"{config.LLM_URL}/v1/models", timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("id", "?") for m in data.get("data", [])]
        return {"up": True, "models": models}
    except Exception as exc:
        return {"up": False, "models": [], "error": str(exc)}
