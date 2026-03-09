"""
site_updater.py — Inserts a new track entry into kairos.html after generation.

Finds the TRACKS array in the HTML file and prepends a new entry.
Also keeps a local tracks.json manifest for reference.
"""

import json
import logging
import re
import datetime
from pathlib import Path
from prompt_generator import MusicPrompt

log = logging.getLogger(__name__)

SITE_PATH = Path(__file__).parent.parent / "index.html"
MANIFEST_PATH = Path(__file__).parent.parent / "tracks.json"


def _load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def _save_manifest(tracks: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(tracks, indent=2, ensure_ascii=False), encoding="utf-8")


def _next_transmission_id(tracks: list[dict]) -> int:
    if not tracks:
        return 2  # 001 is the seed track
    return max(int(t["id"]) for t in tracks) + 1


def add_track_to_site(
    prompt: MusicPrompt,
    audio_url: str,          # SoundCloud / Udio URL, or local path
    track_number: int,
) -> bool:
    """
    Inserts a new track object into the TRACKS array in kairos.html.
    Returns True on success.
    """
    if not SITE_PATH.exists():
        log.error("Site file not found: %s", SITE_PATH)
        return False

    html = SITE_PATH.read_text(encoding="utf-8")

    id_str = str(track_number).zfill(3)
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    subtitle = "MORNING DROP" if prompt.drop_type == "morning" else "EVENING DROP"

    new_entry = (
        f"  {{\n"
        f"    id: '{id_str}',\n"
        f"    title: '{prompt.title}',\n"
        f"    subtitle: '{subtitle}',\n"
        f"    bpm: '{prompt.bpm}',\n"
        f"    key: '{prompt.key.replace('minor','MIN').replace('major','MAJ')}',\n"
        f"    style: '{prompt.style.upper()}',\n"
        f"    url: '{audio_url}',\n"
        f"    audio: null,\n"
        f"    date: '{date_str}'\n"
        f"  }}"
    )

    # Insert after "const TRACKS = ["
    pattern = r"(const TRACKS = \[)"
    replacement = r"\1\n" + new_entry + ","
    new_html, count = re.subn(pattern, replacement, html, count=1)

    if count == 0:
        log.error("Could not find TRACKS array in %s", SITE_PATH)
        return False

    SITE_PATH.write_text(new_html, encoding="utf-8")
    log.info("Inserted track %s '%s' into site.", id_str, prompt.title)

    # Update manifest
    manifest = _load_manifest()
    manifest.append({
        "id": id_str,
        "title": prompt.title,
        "subtitle": subtitle,
        "bpm": prompt.bpm,
        "key": prompt.key,
        "style": prompt.style,
        "url": audio_url,
        "date": date_str,
        "drop_type": prompt.drop_type,
    })
    _save_manifest(manifest)
    log.info("Manifest updated (%d total tracks).", len(manifest))

    return True


def update_stat_counter(html: str, count: int) -> str:
    """Update the transmission count stat in the HTML."""
    padded = str(count).zfill(3)
    return re.sub(
        r'(<span class="stat-value" id="stat-transmissions">)\d+(<\/span>)',
        rf'\g<1>{padded}\2',
        html,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from prompt_generator import MusicPrompt

    dummy = MusicPrompt(
        drop_type="morning",
        title="Test Signal",
        bpm=124,
        key="F minor",
        style="Melodic Techno",
        prompt="test",
        negative_prompt="test",
    )
    add_track_to_site(dummy, audio_url="https://soundcloud.com/example", track_number=2)
    print("Done.")
