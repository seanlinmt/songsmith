"""Unit tests for lyrics duration-aware prompt sizing (TDD, no server needed)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import llm


def test_generate_lyrics_prompt_includes_target_duration():
    """The user message must mention the target runtime so the model sizes lyrics."""
    captured = {}

    async def fake_chat(client, messages, temperature=0.9):
        captured["messages"] = messages
        return ("Title: Test\n[Verse]\nline", None)

    import httpx

    orig = llm._chat
    llm._chat = fake_chat
    try:
        asyncio.run(llm.generate_lyrics("a song about rain", duration_seconds=240))
    finally:
        llm._chat = orig

    user_msg = captured["messages"][-1]["content"]
    assert "240" in user_msg or "4 minutes" in user_msg, user_msg


def test_generate_lyrics_without_duration_unchanged():
    """No duration passed -> prompt has no duration instructions."""
    captured = {}

    async def fake_chat(client, messages, temperature=0.9):
        captured["messages"] = messages
        return ("Title: Test\n[Verse]\nline", None)

    orig = llm._chat
    llm._chat = fake_chat
    try:
        asyncio.run(llm.generate_lyrics("a song about rain"))
    finally:
        llm._chat = orig

    user_msg = captured["messages"][-1]["content"]
    assert "minutes" not in user_msg.lower()
    assert "seconds" not in user_msg.lower()


def test_generate_lyrics_keeps_tags_line():
    """Tags still appended when duration is given."""
    captured = {}

    async def fake_chat(client, messages, temperature=0.9):
        captured["messages"] = messages
        return ("Title: Test\n[Verse]\nline", None)

    orig = llm._chat
    llm._chat = fake_chat
    try:
        asyncio.run(llm.generate_lyrics("rain", tags=["rock"], duration_seconds=60))
    finally:
        llm._chat = orig

    user_msg = captured["messages"][-1]["content"]
    assert "Style/genre: rock" in user_msg
