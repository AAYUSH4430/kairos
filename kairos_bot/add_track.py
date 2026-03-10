"""
add_track.py — Add today's tracks to the site and push to GitHub.

Usage:
    python add_track.py --morning https://soundcloud.com/kairos-transmissions/track-name
    python add_track.py --evening https://soundcloud.com/kairos-transmissions/track-name
    python add_track.py --morning <url> --evening <url>   (both at once)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)

SITE_PATH     = Path(__file__).parent.parent / "index.html"
MANIFEST_PATH = Path(__file__).parent.parent / "tracks.json"
PROMPTS_PATH  = Path(__file__).parent / "prompts_today.json"


def load_prompts() -> list[dict]:
    if not PROMPTS_PATH.exists():
        print("ERROR: prompts_today.json not found. Run export_prompts.py first.")
        sys.exit(1)
    return json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))


def next_track_number() -> int:
    if MANIFEST_PATH.exists():
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return max((int(t["id"]) for t in data), default=1) + 1
    return 4  # already have 001-003


def sc_iframe_id(track_number: int) -> str:
    return f"sc-{track_number}"


def build_sc_iframe(track_number: int, sc_url: str) -> str:
    return (
        f'  <iframe id="sc-{track_number}" scrolling="no" frameborder="no" allow="autoplay"\n'
        f'    src="https://w.soundcloud.com/player/?url={sc_url}'
        f'&auto_play=false&buying=false&liking=false&download=false'
        f'&sharing=false&show_artwork=false&show_comments=false'
        f'&show_playcount=false&show_user=false&hide_related=true'
        f'&visual=false&callback=true"></iframe>\n'
    )


def build_track_card(prompt: dict, track_number: int) -> str:
    num_str   = str(track_number).zfill(2)
    id_str    = str(track_number).zfill(3)
    subtitle  = "MORNING TRANSMISSION — 06:00 UTC" if prompt["drop_type"] == "morning" else "EVENING TRANSMISSION — 20:00 UTC"
    key_str   = prompt["key"].replace("minor", "MIN").replace("major", "MAJ")
    lore      = (
        "KΛIROS synthesized this frequency from today's melodic underground signal. Hypnotic four-on-the-floor architecture."
        if prompt["drop_type"] == "morning" else
        "Peak-hour payload. Synthesized from industrial data streams. Maximum dancefloor pressure."
    )

    return f"""
    <!-- TRACK {num_str} -->
    <div class="track-card">
      <div class="track-number">{num_str}</div>
      <div class="track-time"><div class="track-time-dot"></div> {subtitle}</div>
      <div class="track-name">{prompt["title"].upper()}</div>
      <div class="track-lore">"{lore}"</div>
      <div class="track-meta">
        <span>{prompt["bpm"]} BPM</span>
        <span>KEY: {key_str}</span>
        <span>{prompt["style"].upper()}</span>
      </div>
      <div class="visualizer-wrap">
        <div class="radial-viz"><canvas id="viz-{track_number}" width="110" height="110"></canvas></div>
        <div class="viz-info">
          <div class="viz-freq-row" id="freq-{track_number}"></div>
          <div class="viz-duration">{prompt["bpm"]} BPM — {key_str} — TRANSMISSION {id_str}</div>
        </div>
      </div>
      <div class="custom-player" id="player-{track_number}" style="margin-top:16px">
        <div class="player-left">
          <button class="player-play-btn" id="playBtn-{track_number}" onclick="activatePlayer('{track_number}')">
            <span class="player-play-icon">▶</span>
          </button>
        </div>
        <div class="player-middle">
          <div class="player-title">{prompt["title"].upper()} — TRANSMISSION {id_str}</div>
          <div class="player-bar-wrap">
            <div class="player-bar" id="bar-{track_number}"><div class="player-bar-pulse" id="pulse-{track_number}"></div></div>
          </div>
          <div class="player-times">
            <span id="time-{track_number}">0:00</span>
          </div>
        </div>
      </div>
    </div>"""


def update_site(prompt: dict, track_number: int, sc_url: str) -> bool:
    html = SITE_PATH.read_text(encoding="utf-8")

    # 1. Add hidden SC iframe
    iframe = build_sc_iframe(track_number, sc_url)
    html, n = re.subn(
        r'(<!-- Hidden SC iframes.*?-->[\s\S]*?)(</div>\s*\n<!-- SOUNDCLOUD)',
        lambda m: m.group(1) + iframe + m.group(2),
        html, count=1
    )
    if n == 0:
        # Fallback: insert before closing hidden div
        html = html.replace(
            '</div>\n\n<!-- SOUNDCLOUD WIDGET',
            f'{iframe}</div>\n\n<!-- SOUNDCLOUD WIDGET'
        )

    # 2. Add track card at TOP of tracks-grid (newest first)
    card = build_track_card(prompt, track_number)
    html, n = re.subn(
        r'(<div class="tracks-grid">)',
        r'\1' + card,
        html, count=1
    )
    if n == 0:
        print("ERROR: Could not find .tracks-grid in index.html")
        return False

    # 3. Register new viz in JS tracks object
    new_entry = (
        f"    '{track_number}':        "
        f"{{ bars: 56, speed: 0.016, color: '#c0152a', playing: false, phase: {track_number * 0.8:.1f} }},\n"
    )
    html = re.sub(r"(const tracks = \{)", r"\1\n" + new_entry, html, count=1)

    # 4. Register new SC widget in initWidget loop
    html = html.replace(
        "['featured', '2', '3'].forEach(initWidget);",
        f"['featured', '2', '3', '{track_number}'].forEach(initWidget);"
    )
    html = html.replace(
        "['featured', '2', '3'].forEach(id => {",
        f"['featured', '2', '3', '{track_number}'].forEach(id => {{"
    )

    SITE_PATH.write_text(html, encoding="utf-8")
    return True


def update_manifest(prompt: dict, track_number: int, sc_url: str) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else []
    manifest.append({
        "id":        str(track_number).zfill(3),
        "title":     prompt["title"],
        "drop_type": prompt["drop_type"],
        "bpm":       prompt["bpm"],
        "key":       prompt["key"],
        "style":     prompt["style"],
        "url":       sc_url,
        "date":      datetime.date.today().isoformat(),
    })
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def git_push(titles: list[str]) -> None:
    repo = Path(__file__).parent.parent
    names = " + ".join(titles)
    subprocess.run(["git", "add", "index.html", "tracks.json"], cwd=repo)
    subprocess.run([
        "git", "commit", "-m",
        f"Add {names} to site\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    ], cwd=repo)
    subprocess.run(["git", "push", "origin", "main"], cwd=repo)
    print(f"\n✅ Live at https://aayush4430.github.io/kairos/")


def main():
    parser = argparse.ArgumentParser(description="Add today's tracks to KAIROS site")
    parser.add_argument("--morning", metavar="SOUNDCLOUD_URL", help="SoundCloud URL for morning track")
    parser.add_argument("--evening", metavar="SOUNDCLOUD_URL", help="SoundCloud URL for evening track")
    args = parser.parse_args()

    if not args.morning and not args.evening:
        parser.print_help()
        sys.exit(1)

    prompts = load_prompts()
    prompt_map = {p["drop_type"]: p for p in prompts}
    track_number = next_track_number()
    titles = []

    for drop, url in [("morning", args.morning), ("evening", args.evening)]:
        if not url:
            continue
        if drop not in prompt_map:
            print(f"WARNING: No {drop} prompt found in prompts_today.json — skipping.")
            continue

        prompt = prompt_map[drop]
        print(f"\n→ Adding {drop} track: '{prompt['title']}' [{url}]")

        if update_site(prompt, track_number, url):
            update_manifest(prompt, track_number, url)
            titles.append(f"Transmission {str(track_number).zfill(3)} {prompt['title']}")
            print(f"  ✅ Track {str(track_number).zfill(3)} added to site")
            track_number += 1
        else:
            print(f"  ❌ Failed to update site for {drop} track")

    if titles:
        print("\n→ Pushing to GitHub...")
        git_push(titles)
    else:
        print("\nNothing to push.")


if __name__ == "__main__":
    main()
