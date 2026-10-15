"""Playwright UI test suite for Songsmith."""
import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("SONGSMITH_URL", "http://127.0.0.1:8788")
SCREENSHOT_DIR = Path("/Users/sean/.gemini/antigravity-ide/brain/b73c4048-6080-416b-be9f-203ca938ed04/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        yield context
        browser.close()


@pytest.fixture
def page(browser_context):
    pg = browser_context.new_page()
    pg.goto(BASE_URL, wait_until="networkidle")
    yield pg
    pg.close()


def test_app_shell_and_branding(page):
    """Verify title, branding, top navigation, and default view."""
    assert "Songsmith" in page.title()

    brand_name = page.locator(".brand-name")
    expect(brand_name).to_be_visible()
    assert brand_name.text_content().strip() == "Songsmith"

    brand_tag = page.locator(".brand-tag")
    expect(brand_tag).to_be_visible()
    assert "local studio" in brand_tag.text_content().lower()

    # Nav tabs
    tabs = page.locator(".nav-tab")
    assert tabs.count() == 3
    tab_names = [t.locator("span").first.text_content().strip() for t in tabs.all()]
    assert "Create" in tab_names
    assert "Library" in tab_names
    assert "Settings" in tab_names

    # Default view should be Create
    create_tab = page.locator('.nav-tab[data-route="create"]')
    expect(create_tab).to_have_attribute("aria-selected", "true")

    create_view = page.locator("#viewCreate")
    expect(create_view).to_be_visible()
    expect(page.locator("#viewLibrary")).to_be_hidden()
    expect(page.locator("#viewSettings")).to_be_hidden()

    page.screenshot(path=str(SCREENSHOT_DIR / "01_create_view.png"))


def test_navigation_flow(page):
    """Verify switching between Create, Library, and Settings views."""
    # Navigate to Library
    page.click('.nav-tab[data-route="library"]')
    expect(page.locator('.nav-tab[data-route="library"]')).to_have_attribute("aria-selected", "true")
    expect(page.locator("#viewLibrary")).to_be_visible()
    expect(page.locator("#viewCreate")).to_be_hidden()
    expect(page.locator("#viewSettings")).to_be_hidden()
    page.screenshot(path=str(SCREENSHOT_DIR / "02_library_view.png"))

    # Navigate to Settings
    page.click('.nav-tab[data-route="settings"]')
    expect(page.locator('.nav-tab[data-route="settings"]')).to_have_attribute("aria-selected", "true")
    expect(page.locator("#viewSettings")).to_be_visible()
    expect(page.locator("#viewLibrary")).to_be_hidden()
    expect(page.locator("#viewCreate")).to_be_hidden()
    page.screenshot(path=str(SCREENSHOT_DIR / "03_settings_view.png"))

    # Click Brand logo to return to Create
    page.click('a[data-od-id="brand"]')
    expect(page.locator('.nav-tab[data-route="create"]')).to_have_attribute("aria-selected", "true")
    expect(page.locator("#viewCreate")).to_be_visible()
    expect(page.locator("#viewSettings")).to_be_hidden()


def test_create_view_controls(page):
    """Verify input fields, character counter, style chips, duration, and validations."""
    prompt_input = page.locator("#promptInput")
    prompt_count = page.locator("#promptCount")
    expect(prompt_input).to_be_visible()
    expect(prompt_count).to_have_text("0 / 2000")

    # Typing updates counter
    test_text = "Upbeat neon synthwave with driving basslines"
    prompt_input.fill(test_text)
    expect(prompt_count).to_have_text(f"{len(test_text)} / 2000")

    # Custom lyrics accordion toggle
    lyrics_toggle = page.locator("#lyricsToggle")
    lyrics_panel = page.locator("#lyricsPanel")
    expect(lyrics_panel).to_have_count(0)

    lyrics_toggle.click()
    expect(page.locator("#lyricsPanel")).to_be_visible()
    lyrics_input = page.locator("#lyricsInput")
    expect(lyrics_input).to_be_visible()
    lyrics_input.fill("[Verse]\nNeon lights in the rain\n[Chorus]\nRunning away")

    # Style chips
    style_chips = page.locator("#styleChips .chip")
    assert style_chips.count() > 0
    first_chip = style_chips.first
    chip_tag = first_chip.get_attribute("data-tag")
    expect(first_chip).to_have_attribute("aria-pressed", "false")

    first_chip.click()
    expect(first_chip).to_have_attribute("aria-pressed", "true")

    first_chip.click()
    expect(first_chip).to_have_attribute("aria-pressed", "false")

    # Instrumental toggle
    inst_switch = page.locator('button[data-od-id="instrumental-switch"]')
    expect(inst_switch).to_have_attribute("aria-checked", "false")
    inst_switch.click()
    expect(inst_switch).to_have_attribute("aria-checked", "true")
    inst_switch.click()
    expect(inst_switch).to_have_attribute("aria-checked", "false")

    # Duration slider
    dur_slider = page.locator("#durationSlider")
    dur_readout = page.locator("#durationReadout")
    expect(dur_readout).to_have_text("0:30")

    dur_slider.fill("0")
    expect(dur_readout).to_have_text("0:15")
    dur_slider.fill("2")
    expect(dur_readout).to_have_text("1:00")

    # Empty prompt validation error
    prompt_input.fill("")
    page.click("#generateBtn")

    # Toast should appear
    toast = page.locator(".toast.err")
    expect(toast).to_be_visible()
    expect(toast).to_contain_text("Describe your song first")
    expect(prompt_input).to_be_focused()
    page.screenshot(path=str(SCREENSHOT_DIR / "04_create_validation_toast.png"))


def test_library_and_song_cards(page):
    """Verify Library displays songs and metadata."""
    page.click('.nav-tab[data-route="library"]')
    expect(page.locator("#viewLibrary")).to_be_visible()

    cards = page.locator(".song-card")
    count = cards.count()
    if count > 0:
        first_card = cards.first
        expect(first_card.locator(".song-title")).to_be_visible()
        expect(first_card.locator(".song-duration")).to_be_visible()
        expect(first_card.locator(".play-btn")).to_be_visible()
        expect(first_card.locator('.song-action[data-act="regen"]')).to_be_visible()
    else:
        expect(page.locator("#libraryEmpty")).to_be_visible()
        expect(page.locator("#emptyCreateBtn")).to_be_visible()


def test_song_modal(page):
    """Verify clicking a song opens the SongModal dialog, player, lyrics, and closes on ESC."""
    page.click('.nav-tab[data-route="library"]')
    cards = page.locator(".song-card")
    if cards.count() == 0:
        pytest.skip("No songs in library to test modal")

    first_card = cards.first
    card_title = first_card.locator(".song-title").text_content().strip()

    # Click card to open modal
    first_card.click()

    modal = page.locator("#songModal")
    expect(modal).to_be_visible()

    modal_title = page.locator("#modalTitle")
    expect(modal_title).to_have_text(card_title)

    # Player controls
    expect(page.locator("#modalPlay")).to_be_visible()
    expect(page.locator("#modalWave")).to_be_visible()
    expect(page.locator("#modalTime")).to_be_visible()
    expect(page.locator("#modalMeta")).to_be_visible()
    expect(page.locator("#modalLyrics")).to_be_visible()
    expect(page.locator("#dlMp3")).to_be_visible()

    page.screenshot(path=str(SCREENSHOT_DIR / "05_song_modal.png"))

    # Close with ESC key
    page.keyboard.press("Escape")
    expect(modal).to_be_hidden()


def test_settings_view_and_dirty_tracking(page):
    """Verify settings form inputs, live values, and dirty state tracking."""
    page.click('.nav-tab[data-route="settings"]')
    expect(page.locator("#viewSettings")).to_be_visible()

    localai_input = page.locator("#cfgLocalai")
    llm_input = page.locator("#cfgLlm")
    music_model_input = page.locator("#cfgMusicModel")
    llm_model_input = page.locator("#cfgLlmModel")
    save_btn = page.locator("#settingsSave")

    expect(localai_input).to_be_visible()
    expect(llm_input).to_be_visible()
    expect(music_model_input).to_be_visible()
    expect(llm_model_input).to_be_visible()

    # Save button should be disabled initially (not dirty)
    expect(save_btn).to_be_disabled()

    # Modify an input
    orig_val = music_model_input.input_value()
    music_model_input.fill(orig_val + "-test")

    # Save button becomes enabled
    expect(save_btn).to_be_enabled()

    # Revert value
    music_model_input.fill(orig_val)
    expect(save_btn).to_be_disabled()

    # Health status dots: one per endpoint field label + the API row
    expect(page.locator('[data-od-id="health-api"] .status-dot')).to_be_visible()
    expect(page.locator('#cfgLocalai').locator('xpath=preceding-sibling::*[1]')).to_be_visible()  # label with dot
    music_dot = page.locator('label[for="cfgLocalai"] .status-dot')
    image_dot = page.locator('label[for="cfgImageUrl"] .status-dot')
    llm_dot = page.locator('label[for="cfgLlm"] .status-dot')
    expect(music_dot).to_be_visible()
    expect(image_dot).to_be_visible()
    expect(llm_dot).to_be_visible()

    page.screenshot(path=str(SCREENSHOT_DIR / "06_settings_health.png"))


def test_responsive_mobile_layout(browser_context):
    """Verify the UI adapts to mobile viewports without horizontal overflow."""
    mobile_page = browser_context.new_page()
    mobile_page.set_viewport_size({"width": 375, "height": 667})
    mobile_page.goto(BASE_URL, wait_until="networkidle")

    # Navigate explicitly to create view
    mobile_page.click('.nav-tab[data-route="create"]')
    expect(mobile_page.locator("#viewCreate")).to_be_visible()
    expect(mobile_page.locator(".topnav")).to_be_visible()
    expect(mobile_page.locator("#promptInput")).to_be_visible()
    expect(mobile_page.locator("#generateBtn")).to_be_visible()

    # Check horizontal scroll / overflow
    has_overflow = mobile_page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not has_overflow, "Page has unexpected horizontal overflow on mobile viewport"

    mobile_page.screenshot(path=str(SCREENSHOT_DIR / "07_mobile_layout.png"))
    mobile_page.close()
