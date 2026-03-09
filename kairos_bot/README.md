# KΛIROS Bot — Setup Guide

AI-powered techno music label automation. Generates 2 tracks/day, updates the website.

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install requests beautifulsoup4 python-dotenv
```

### 2. Install audiocraft (MusicGen)

Requires Python 3.9+ and a CUDA-capable GPU for reasonable speed.

```bash
pip install audiocraft
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

> **CPU only?** It works but is very slow (~10–30 min per clip). Set `MUSICGEN_MODEL=facebook/musicgen-small` to speed it up.

### 3. Install ffmpeg (for MP3 conversion)

Download from https://ffmpeg.org/download.html and add to PATH.

### 4. Configure environment

```bash
cd kairos_bot
cp .env.example .env
# Edit .env — add LASTFM_API_KEY if you want artist trend data
```

### 5. Test the pipeline (no audio generation)

```bash
python kairos_bot.py --drop morning --dry-run
```

### 6. Run a real drop

```bash
python kairos_bot.py --drop morning   # 6AM melodic techno
python kairos_bot.py --drop evening   # 8PM industrial techno
```

Audio files are saved to `output/`. Upload to SoundCloud manually, then the site updates automatically.

---

## Scheduling (Windows Task Scheduler)

1. Open Task Scheduler → Create Basic Task
2. Name: `KAIROS Morning Drop`
3. Trigger: Daily at 6:00 AM
4. Action: Start program
   - Program: `python`
   - Arguments: `C:\Users\aayus\kairos\kairos_bot\kairos_bot.py --drop morning`
   - Start in: `C:\Users\aayus\kairos\kairos_bot`
5. Repeat for Evening at 8:00 PM with `--drop evening`

---

## Deploying to Netlify

1. Push `kairos.html` to a GitHub repo
2. Connect repo to Netlify (free tier)
3. Set publish directory to `/` and build command to empty
4. Auto-deploy triggers on every push

The bot updates `kairos.html` locally. After each drop, push to GitHub and Netlify redeploys automatically.

---

## File Structure

```
kairos/
├── kairos.html              ← website (auto-updated by bot)
├── tracks.json              ← track manifest (auto-generated)
├── kairos_profile.png       ← SoundCloud profile picture
└── kairos_bot/
    ├── kairos_bot.py        ← main orchestrator
    ├── trend_scraper.py     ← Beatport + Reddit + Last.fm
    ├── prompt_generator.py  ← trends → music prompts
    ├── music_generator.py   ← MusicGen audio generation
    ├── site_updater.py      ← inserts new tracks into HTML
    ├── requirements.txt
    ├── .env.example
    ├── .env                 ← your secrets (not committed)
    ├── trends_cache.json    ← today's trend cache (auto-generated)
    ├── kairos.log           ← run log (auto-generated)
    └── output/              ← generated audio files
```

---

## Music Style Reference

| Drop    | BPM | Key     | Style                      | Refs                        |
|---------|-----|---------|----------------------------|-----------------------------|
| Morning | 124 | F minor | Melodic techno, hypnotic   | Monolink, ARTBAT, Tale Of Us|
| Evening | 134 | A minor | Industrial peak-time hard  | Alignment, Paula Temple     |

---

## Phase Roadmap

- **Phase 1 (Weeks 1–8):** Build audience — daily drops, SoundCloud, Instagram Reels
- **Phase 2:** Amuse distribution → Spotify/Apple Music, YouTube monetization
- **Phase 3:** Licensing packs on Beatstars, brand deals
- **Target:** ₹50,000+/month by Month 6
