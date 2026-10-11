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


async def _chat(client: httpx.AsyncClient, messages: list[dict],
                temperature: float = 0.9) -> str:
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
    return (data["choices"][0]["message"]["content"] or "").strip()


async def generate_lyrics(prompt: str, tags: list[str] | None = None) -> tuple[str, str | None]:
    """Returns (lyrics, title) — title may be None if the model skipped it."""
    user_content = prompt
    if tags:
        user_content = f"{prompt}\n\nStyle/genre: {', '.join(tags)}"
    try:
        async with httpx.AsyncClient() as client:
            content = await _chat(client, [
                {"role": "system", "content": LYRICS_SYSTEM},
                {"role": "user", "content": user_content},
            ])
            return _split_title(content)
    except httpx.TimeoutException as exc:
        raise RuntimeError("LLM busy: request timed out, try again shortly") from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(f"LLM unreachable at {config.LLM_URL}") from exc


TITLE_SYSTEM = (
    "You name songs. Reply with ONLY a short song title (max 5 words), "
    "no quotes, no punctuation at the end, no explanation."
)


async def generate_title(prompt: str, lyrics: str,
                         tags: list[str] | None = None) -> str | None:
    content = f"Song description: {prompt}\n\nLyrics:\n{lyrics[:2000]}"
    if tags:
        content = f"{content}\n\nStyle/genre: {', '.join(tags)}"
    try:
        async with httpx.AsyncClient() as client:
            return await _chat(client, [
                {"role": "system", "content": TITLE_SYSTEM},
                {"role": "user", "content": content},
            ], temperature=0.7)
    except Exception:
        log.exception("title generation failed")
        return None


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


async def expand_style(prompt: str, tags: list[str]) -> tuple[str, list[str]]:
    """Best-effort: expand tags into a rich style description + negative tags.

    Returns (style_prompt, negative_tags); on any failure falls back to
    (", ".join(tags), []).
    """
    fallback = (", ".join(tags), [])
    try:
        async with httpx.AsyncClient() as client:
            content = await _chat(client, [
                {"role": "system", "content": STYLE_SYSTEM},
                {"role": "user", "content": f"Song description: {prompt}\n\nStyle tags: {', '.join(tags)}"},
            ], temperature=0.5)
        parsed = _parse_style_reply(content)
        if parsed is None:
            return fallback
        return parsed
    except Exception:
        log.exception("style expansion failed")
        return fallback


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
        async with httpx.AsyncClient() as client:
            content = await _chat(client, [
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
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{config.LLM_URL}/v1/models", timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("id", "?") for m in data.get("data", [])]
        return {"up": True, "models": models}
    except Exception as exc:
        return {"up": False, "models": [], "error": str(exc)}
