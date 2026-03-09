"""
site_updater.py — Inserts a new track card into index.html after generation.

Injects an HTML card into the .tracks-grid div and updates tracks.json manifest.
"""

import json
import logging
import re
import datetime
from pathlib import Path
from prompt_generator import MusicPrompt

log = logging.getLogger(__name__)

SITE_PATH     = Path(__file__).parent.parent / "index.html"
MANIFEST_PATH = Path(__file__).parent.parent / "tracks.json"


def _load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def _save_manifest(tracks: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(tracks, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_card(prompt: MusicPrompt, track_number: int, audio_url: str, date_str: str) -> str:
    id_str   = str(track_number).zfill(2)
    subtitle = "MORNING TRANSMISSION — 06:00 UTC" if prompt.drop_type == "morning" else "EVENING TRANSMISSION — 20:00 UTC"
    key_str  = prompt.key.replace("minor", "MIN").replace("major", "MAJ")
    listen   = f'<a href="{audio_url}" target="_blank" class="play-btn" style="text-decoration:none">LISTEN ↗</a>' if audio_url and not audio_url.startswith("[") else ''

    lore_map = {
        "morning": f"KΛIROS synthesized this frequency from today's melodic underground signal. Hypnotic four-on-the-floor architecture.",
        "evening": f"Peak-hour payload. Synthesized from industrial data streams. Maximum dancefloor pressure.",
    }

    return f"""
    <!-- TRACK {id_str} -->
    <div class="track-card">
      <div class="track-number">{id_str}</div>
      <div class="track-time"><div class="track-time-dot"></div> {subtitle}</div>
      <div class="track-name">{prompt.title.upper()}</div>
      <div class="track-lore">"{lore_map[prompt.drop_type]}"</div>
      <div class="track-meta">
        <span>{prompt.bpm} BPM</span>
        <span>{key_str}</span>
        <span>{prompt.style.upper()}</span>
      </div>
      <div class="visualizer-wrap">
        <div class="radial-viz"><canvas id="viz-{track_number}" width="110" height="110"></canvas></div>
        <div class="viz-info">
          <div class="viz-freq-row" id="freq-{track_number}"></div>
          <div class="viz-duration">{prompt.bpm} BPM — {key_str} — TRANSMISSION {str(track_number).zfill(3)}</div>
        </div>
      </div>
      {listen if listen else f'<button class="play-btn" onclick="togglePlay(\'{track_number}\')"><span class="play-icon"></span> PLAY</button>'}
    </div>"""


def _register_viz(html: str, track_number: int) -> str:
    """Add the new viz entry to the tracks JS object."""
    new_entry = (
        f"    '{track_number}':        "
        f"{{ bars: 56, speed: 0.016, color: '#c0152a', playing: false, phase: {track_number * 0.8:.1f} }},\n"
    )
    return re.sub(
        r"(const tracks = \{)",
        r"\1\n" + new_entry,
        html, count=1
    )


def add_track_to_site(
    prompt: MusicPrompt,
    audio_url: str,
    track_number: int,
) -> bool:
    if not SITE_PATH.exists():
        log.error("Site file not found: %s", SITE_PATH)
        return False

    html     = SITE_PATH.read_text(encoding="utf-8")
    id_str   = str(track_number).zfill(3)
    date_str = datetime.date.today().strftime("%Y-%m-%d")

    # 1. Inject card HTML after the opening of .tracks-grid
    card = _build_card(prompt, track_number, audio_url, date_str)
    new_html, count = re.subn(
        r'(<div class="tracks-grid">)',
        r'\1' + card,
        html, count=1
    )
    if count == 0:
        log.error("Could not find .tracks-grid in %s", SITE_PATH)
        return False

    # 2. Register the new viz in the JS tracks object
    new_html = _register_viz(new_html, track_number)

    SITE_PATH.write_text(new_html, encoding="utf-8")
    log.info("Inserted track %s '%s' into site.", id_str, prompt.title)

    # 3. Update manifest
    subtitle = "MORNING DROP" if prompt.drop_type == "morning" else "EVENING DROP"
    manifest = _load_manifest()
    manifest.append({
        "id":       id_str,
        "title":    prompt.title,
        "subtitle": subtitle,
        "bpm":      prompt.bpm,
        "key":      prompt.key,
        "style":    prompt.style,
        "url":      audio_url,
        "date":     date_str,
        "drop_type": prompt.drop_type,
    })
    _save_manifest(manifest)
    log.info("Manifest updated (%d total tracks).", len(manifest))

    return True


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)

    from prompt_generator import MusicPrompt
    dummy = MusicPrompt(
        drop_type="morning", title="Test Signal", bpm=124, key="F minor",
        style="Melodic Techno", prompt="test", negative_prompt="test",
    )
    add_track_to_site(dummy, audio_url="https://soundcloud.com/example", track_number=2)
    print("Done.")
