"""Cover art generation via LocalAI /v1/images/generations."""
import base64
import logging

import httpx

from . import config

log = logging.getLogger("songsmith.image")

_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


async def generate_cover(out_path, title: str | None = None,
                         tags: list[str] | None = None,
                         lyrics: str | None = None,
                         prompt: str | None = None) -> str:
    """Generate cover art and save to out_path. Returns out_path as str.

    The image prompt is built from the song's title, genre tags, a short
    lyric summary, and the original generation prompt.
    """
    has_title = bool(title)
    image_prompt = (
        f"album cover art for the song '{title}'" if has_title
        else "album cover art"
    )
    if tags:
        image_prompt += f", style: {', '.join(tags)}"
    if lyrics:
        image_prompt += f", mood of lyrics: {lyrics[:160]}..."
    if prompt:
        image_prompt += f", inspired by: {prompt}"
    if has_title:
        image_prompt += (f", the only text in the image is the exact song title "
                         f"'{title}' spelled correctly, no other words, letters, "
                         f"watermarks, or logos, high quality")
    else:
        image_prompt += (", no text, no words, no letters, no watermarks, "
                         "no logos, high quality")
    payload = {
        "model": config.IMAGE_MODEL,
        "prompt": image_prompt,
        "n": 1,
        "size": "512x512",
    }
    if not has_title:
        # No title -> forbid text outright. Only added when absent: the
        # endpoint may reject unknown fields, and there is no retry logic.
        payload["negative_prompt"] = ("text, words, letters, typography, "
                                      "watermarks, logos, gibberish text, "
                                      "misspelled words")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config.LOCALAI_URL}/v1/images/generations",
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or []
        if not items:
            raise ValueError("image API returned no data")
        item = items[0]

        b64 = item.get("b64_json")
        if b64:
            out_path.write_bytes(base64.b64decode(b64))
            return str(out_path)

        url = item.get("url")
        if url:
            # url may be relative to LOCALAI_URL
            if not str(url).startswith(("http://", "https://")):
                url = f"{config.LOCALAI_URL}/{str(url).lstrip('/')}"
            img = await client.get(url, timeout=_TIMEOUT)
            img.raise_for_status()
            out_path.write_bytes(img.content)
            return str(out_path)

        raise ValueError("image API returned neither b64_json nor url")
