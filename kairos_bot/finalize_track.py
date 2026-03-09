"""
finalize_track.py — After downloading audio from Colab, run this to update the site.

Usage:
    python finalize_track.py --wav output/transmission_002_morning.wav --url https://soundcloud.com/...
    python finalize_track.py --wav output/transmission_002_morning.wav   (URL optional, add later)

Steps:
    1. Converts WAV to MP3 (if ffmpeg available)
    2. Inserts track into kairos.html
    3. Updates tracks.json manifest
    4. Prints next steps (upload to SoundCloud, deploy to Netlify)
"""

import argparse
import json
import datetime
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False))],
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Finalize a KAIROS track after Colab generation")
    parser.add_argument("--wav", required=True, help="Path to the downloaded WAV file")
    parser.add_argument("--url", default="", help="SoundCloud/Udio URL (can add later)")
    parser.add_argument("--drop", choices=["morning", "evening"], help="Override drop type detection")
    args = parser.parse_args()

    wav_path = Path(args.wav)
    if not wav_path.exists():
        log.error("File not found: %s", wav_path)
        sys.exit(1)

    # Load today's prompts
    prompts_path = Path(__file__).parent / "prompts_today.json"
    if not prompts_path.exists():
        log.error("Run export_prompts.py first to generate prompts_today.json")
        sys.exit(1)

    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))

    # Detect drop type from filename or flag
    drop_type = args.drop
    if not drop_type:
        name = wav_path.name.lower()
        if "morning" in name:
            drop_type = "morning"
        elif "evening" in name:
            drop_type = "evening"
        else:
            log.error("Cannot detect drop type from filename. Use --drop morning or --drop evening")
            sys.exit(1)

    prompt_data = next((p for p in prompts if p["drop_type"] == drop_type), None)
    if not prompt_data:
        log.error("No %s prompt found in prompts_today.json", drop_type)
        sys.exit(1)

    log.info("Finalizing: '%s' [%s drop]", prompt_data["title"], drop_type)

    # Convert to MP3 if ffmpeg available
    audio_path = wav_path
    try:
        import os
        mp3_path = wav_path.with_suffix(".mp3")
        ret = os.system(f'ffmpeg -y -i "{wav_path}" -codec:a libmp3lame -qscale:a 2 "{mp3_path}" -loglevel quiet')
        if ret == 0:
            audio_path = mp3_path
            log.info("Converted to MP3: %s", mp3_path)
        else:
            log.warning("ffmpeg not found — keeping WAV")
    except Exception:
        pass

    # Build MusicPrompt object for site_updater
    from prompt_generator import MusicPrompt
    prompt = MusicPrompt(
        drop_type=drop_type,
        title=prompt_data["title"],
        bpm=prompt_data["bpm"],
        key=prompt_data["key"],
        style=prompt_data["style"],
        prompt=prompt_data["prompt"],
        negative_prompt=prompt_data["negative_prompt"],
    )

    # Use provided URL or placeholder
    audio_url = args.url if args.url else f"[UPLOAD {audio_path.name} TO SOUNDCLOUD]"

    from site_updater import add_track_to_site
    success = add_track_to_site(prompt, audio_url=audio_url, track_number=prompt_data["track_number"])

    if success:
        print()
        print("=" * 60)
        print(f"  TRANSMISSION {prompt_data['track_number']:03d} — '{prompt_data['title']}' FINALIZED")
        print("=" * 60)
        print()
        print("  NEXT STEPS:")
        print(f"  1. Upload {audio_path.name} to SoundCloud")
        print("  2. Copy the SoundCloud URL")
        print("  3. Update tracks.json with the real URL (optional)")
        print("  4. Commit kairos.html + tracks.json to GitHub")
        print("  5. Netlify auto-deploys in ~30 seconds")
        print()
        if not args.url:
            print("  TIP: Re-run with --url https://soundcloud.com/... to embed the real link")
        print("=" * 60)
    else:
        log.error("Site update failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
