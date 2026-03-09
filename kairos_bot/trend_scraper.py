"""
trend_scraper.py — Scrapes Beatport, Reddit, Last.fm for daily techno trends.
Returns a structured TrendReport used by prompt_generator.py.
"""

import os
import re
import time
import json
import logging
import datetime
import requests
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")  # optional — set in .env


@dataclass
class TrendReport:
    date: str = ""
    beatport_tracks: list[dict] = field(default_factory=list)   # [{title, artist, bpm, key, label}]
    reddit_keywords: list[str] = field(default_factory=list)
    lastfm_artists: list[str] = field(default_factory=list)
    dominant_bpm: Optional[int] = None
    dominant_key: Optional[str] = None
    mood_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


# ── BEATPORT ─────────────────────────────────────────────────────────────────

def _extract_tracks_from_json(data: dict) -> list[dict]:
    """Recursively search for track lists anywhere in Beatport's Next.js JSON blob."""
    tracks = []

    def _walk(obj):
        if len(tracks) >= 10:
            return
        if isinstance(obj, dict):
            # Look for objects that look like a track (have 'name' and 'bpm')
            if "bpm" in obj and "name" in obj and isinstance(obj.get("bpm"), (int, float)):
                tracks.append({
                    "title":  obj.get("name", ""),
                    "artist": ", ".join(
                        a["name"] for a in obj.get("artists", []) if isinstance(a, dict)
                    ),
                    "bpm":    obj.get("bpm"),
                    "key":    (obj.get("key") or {}).get("name", "") if isinstance(obj.get("key"), dict) else str(obj.get("key", "")),
                    "label":  (obj.get("release") or {}).get("label", {}).get("name", "")
                              if isinstance(obj.get("release"), dict) else "",
                })
                return
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return tracks


def scrape_beatport(genre_slug: str = "techno-peak-time-driving") -> list[dict]:
    """Scrape top tracks from a Beatport genre chart via their embedded Next.js JSON."""
    url = f"https://www.beatport.com/genre/{genre_slug}/6/top-100"
    tracks = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            data = json.loads(script.string)
            tracks = _extract_tracks_from_json(data)

        if not tracks:
            log.warning("Beatport: 0 tracks parsed — falling back to curated defaults.")
            # Curated fallback so prompt generation still works meaningfully
            tracks = [
                {"title": "Unknown Horizon",  "artist": "Alignment",      "bpm": 136, "key": "A minor", "label": "Mord"},
                {"title": "Dark Matter",       "artist": "Rebekah",        "bpm": 134, "key": "D minor", "label": "Decoy"},
                {"title": "Signal Loss",       "artist": "Paula Temple",   "bpm": 133, "key": "E minor", "label": "Houndstooth"},
                {"title": "Meridian",          "artist": "ARTBAT",         "bpm": 124, "key": "F minor", "label": "Afterlife"},
                {"title": "Liminal",           "artist": "Tale Of Us",     "bpm": 122, "key": "G minor", "label": "Afterlife"},
            ]
    except Exception as exc:
        log.error("Beatport scrape failed: %s", exc)

    return tracks


# ── REDDIT ────────────────────────────────────────────────────────────────────

REDDIT_SUBS = ["DJs", "TechnoProduction", "electronicmusic", "EDM"]

REDDIT_HEADERS = {
    "User-Agent": "kairos-bot/1.0 (music trend scraper; contact kairos.transmissions@gmail.com)",
    "Accept": "application/json",
}

def scrape_reddit(limit: int = 25) -> list[str]:
    """Pull hot post titles from techno/rave subreddits and extract keywords."""
    keywords = []
    for sub in REDDIT_SUBS:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
            if resp.status_code == 403:
                log.warning("Reddit r/%s: 403 Forbidden — skipping.", sub)
                continue
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])
            for post in posts:
                title = post.get("data", {}).get("title", "")
                # simple keyword extraction: words >4 chars, not stopwords
                words = re.findall(r"[A-Za-z]{4,}", title)
                keywords.extend(w.lower() for w in words)
            time.sleep(0.5)  # polite delay
        except Exception as exc:
            log.warning("Reddit r/%s failed: %s", sub, exc)

    # Deduplicate, keep most frequent
    from collections import Counter
    counts = Counter(keywords)
    STOPWORDS = {"that","this","with","from","have","just","your","they","been","will","what","when","into","also","about","more","some","then","than","like","been","were"}
    top = [w for w, _ in counts.most_common(40) if w not in STOPWORDS]
    return top[:20]


# ── LAST.FM ───────────────────────────────────────────────────────────────────

LASTFM_TAGS = ["techno", "melodic techno", "industrial techno", "dark techno"]

def scrape_lastfm(tag: str = "techno", limit: int = 10) -> list[str]:
    """Return top artists for a Last.fm tag. Falls back gracefully if no API key."""
    if not LASTFM_API_KEY:
        log.info("No LASTFM_API_KEY set — skipping Last.fm scrape.")
        return []
    try:
        url = "https://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "tag.gettopartists",
            "tag": tag,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": limit,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        artists = resp.json().get("topartists", {}).get("artist", [])
        return [a["name"] for a in artists]
    except Exception as exc:
        log.error("Last.fm scrape failed: %s", exc)
        return []


# ── BPM + KEY INFERENCE ───────────────────────────────────────────────────────

def infer_dominant(tracks: list[dict]) -> tuple[Optional[int], Optional[str]]:
    """Find the most common BPM and key from scraped tracks."""
    from collections import Counter
    bpms = [t["bpm"] for t in tracks if t.get("bpm")]
    keys = [t["key"] for t in tracks if t.get("key")]
    dominant_bpm = Counter(bpms).most_common(1)[0][0] if bpms else None
    dominant_key = Counter(keys).most_common(1)[0][0] if keys else None
    return dominant_bpm, dominant_key


# ── MAIN ENTRY ────────────────────────────────────────────────────────────────

def gather_trends(save_path: str = "trends_cache.json") -> TrendReport:
    log.info("Starting trend scrape...")
    report = TrendReport(date=datetime.date.today().isoformat())

    report.beatport_tracks = scrape_beatport()
    log.info("  Beatport: %d tracks", len(report.beatport_tracks))

    report.reddit_keywords = scrape_reddit()
    log.info("  Reddit keywords: %s", report.reddit_keywords[:8])

    report.lastfm_artists = scrape_lastfm("melodic techno") + scrape_lastfm("industrial techno", limit=5)
    log.info("  Last.fm artists: %s", report.lastfm_artists[:5])

    report.dominant_bpm, report.dominant_key = infer_dominant(report.beatport_tracks)

    # Mood tags from reddit keywords + last.fm
    mood_vocab = {
        "dark","hypnotic","industrial","acid","warehouse","berlin","underground",
        "rave","peak","driving","melodic","emotional","spiritual","ritual","drone",
        "minimal","relentless","trance","ambient","noise","void","liminal","primal",
    }
    report.mood_tags = [w for w in report.reddit_keywords if w in mood_vocab][:6]

    # Cache to disk
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    log.info("Trends saved to %s", save_path)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = gather_trends()
    print(json.dumps(r.to_dict(), indent=2))
