"""
kairos_bot.py — Main orchestrator for KΛIROS AI music label.

Schedule (run this script twice daily via cron/Task Scheduler):
    6:00 AM  → morning drop (melodic techno, 124 BPM, F minor)
    8:00 PM  → evening drop (industrial techno, 134 BPM, A minor)

Usage:
    python kairos_bot.py --drop morning
    python kairos_bot.py --drop evening
    python kairos_bot.py --drop morning --dry-run   (skip generation, test pipeline)
    python kairos_bot.py --list                     (show track manifest)
"""

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

# ── ENV SETUP ─────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)),
        logging.FileHandler(Path(__file__).parent / "kairos.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).parent.parent / "tracks.json"


def _next_track_number() -> int:
    if MANIFEST_PATH.exists():
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return max((int(t["id"]) for t in data), default=1) + 1
    return 2  # seed track is 001


def run_drop(drop_type: str, dry_run: bool = False) -> None:
    log.info("=" * 60)
    log.info("KΛIROS — %s DROP — %s", drop_type.upper(), datetime.date.today())
    log.info("=" * 60)

    # 1. Scrape trends
    from trend_scraper import gather_trends
    trends_cache = Path(__file__).parent / "trends_cache.json"

    # Re-use today's cache if it exists (avoid hammering scrapers twice a day)
    if trends_cache.exists():
        mtime = datetime.date.fromtimestamp(trends_cache.stat().st_mtime)
        if mtime == datetime.date.today():
            log.info("Using cached trends from today.")
            import dataclasses
            from trend_scraper import TrendReport
            raw = json.loads(trends_cache.read_text(encoding="utf-8"))
            report = TrendReport(**{k: v for k, v in raw.items() if k in TrendReport.__dataclass_fields__})
        else:
            report = gather_trends(str(trends_cache))
    else:
        report = gather_trends(str(trends_cache))

    log.info("Trend mood tags: %s", report.mood_tags)

    # 2. Generate prompt
    from prompt_generator import generate_prompts
    track_number = _next_track_number()
    morning_p, evening_p = generate_prompts(report, track_number)
    prompt = morning_p if drop_type == "morning" else evening_p

    log.info("Track #%03d: '%s' [%s BPM, %s]", track_number, prompt.title, prompt.bpm, prompt.key)
    log.info("Prompt preview: %s", prompt.prompt[:100])

    if dry_run:
        log.info("[DRY RUN] Skipping audio generation and site update.")
        log.info("[DRY RUN] Full prompt:\n%s", prompt.prompt)
        return

    # 3. Generate audio
    from music_generator import generate_audio, convert_to_mp3
    wav_path = generate_audio(prompt, track_number)
    audio_path = convert_to_mp3(wav_path)

    log.info("Audio saved: %s", audio_path)

    # 4. Upload placeholder URL (manual step until SoundCloud API is wired)
    #    For now we just use the local file path. Replace with actual URL after upload.
    audio_url = os.getenv("SOUNDCLOUD_BASE_URL", "") + str(audio_path.name)
    log.warning(
        "MANUAL STEP: Upload '%s' to SoundCloud/Udio and update the URL in tracks.json if needed.",
        audio_path.name,
    )

    # 5. Update site
    from site_updater import add_track_to_site
    success = add_track_to_site(prompt, audio_url=audio_url, track_number=track_number)

    if success:
        log.info("Site updated. Deploy kairos.html to Netlify.")
    else:
        log.error("Site update failed.")

    log.info("=" * 60)
    log.info("TRANSMISSION %03d COMPLETE — '%s'", track_number, prompt.title)
    log.info("=" * 60)


def list_tracks() -> None:
    if not MANIFEST_PATH.exists():
        print("No tracks yet.")
        return
    tracks = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"\n{'ID':<6} {'DROP':<10} {'TITLE':<25} {'BPM':<6} {'KEY':<12} {'DATE'}")
    print("-" * 70)
    for t in sorted(tracks, key=lambda x: x["id"]):
        print(f"{t['id']:<6} {t.get('drop_type','?'):<10} {t['title']:<25} {t['bpm']:<6} {t['key']:<12} {t.get('date','')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="KΛIROS AI Music Bot")
    parser.add_argument("--drop", choices=["morning", "evening"], help="Which drop to generate")
    parser.add_argument("--dry-run", action="store_true", help="Test pipeline without generating audio")
    parser.add_argument("--list", action="store_true", help="List all generated tracks")
    args = parser.parse_args()

    if args.list:
        list_tracks()
        return

    if not args.drop:
        # Auto-detect based on current hour
        hour = datetime.datetime.now().hour
        args.drop = "morning" if hour < 14 else "evening"
        log.info("Auto-detected drop type: %s (hour=%d)", args.drop, hour)

    run_drop(args.drop, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
