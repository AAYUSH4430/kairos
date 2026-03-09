"""
prompt_generator.py — Turns a TrendReport into optimised MusicGen prompts.

Morning drop: Melodic techno, Afterlife/ARTBAT/Monolink style, ~124 BPM, F minor.
Evening drop: Hard rave / peak-time industrial techno, ~134 BPM, A minor.
"""

import random
from dataclasses import dataclass
from trend_scraper import TrendReport


@dataclass
class MusicPrompt:
    drop_type: str        # "morning" or "evening"
    title: str
    bpm: int
    key: str
    style: str
    prompt: str           # the actual text prompt for MusicGen
    negative_prompt: str  # what to avoid


# ── VOCABULARY POOLS ──────────────────────────────────────────────────────────

MORNING_MOODS = [
    "hypnotic", "transcendent", "otherworldly", "meditative", "liminal",
    "drifting", "ethereal", "cosmic", "ritual", "deep",
]

MORNING_ELEMENTS = [
    "rolling four-on-the-floor kick", "deep melodic bassline",
    "shimmering pad washes", "distant whispered vocal buried in reverb",
    "evolving arpeggiated synth", "warm sub-bass pulse",
    "subtle acid line weaving through the mix", "haunting lead melody",
    "cinematic string stabs", "gated reverb percussion",
]

EVENING_MOODS = [
    "relentless", "industrial", "brutal", "primal", "raw",
    "driving", "apocalyptic", "frenetic", "machine-like", "unforgiving",
]

EVENING_ELEMENTS = [
    "punishing kick drum with distorted clap", "distorted acid bass",
    "metallic percussion hits", "dark atmospheric drone",
    "aggressive hi-hat rolls", "industrial noise texture",
    "compressed snare rolls building tension", "filtered white noise sweeps",
    "pitch-shifted vocal stab", "overdriven 303 acid line",
]

REFERENCES_MORNING = [
    "Monolink", "ARTBAT", "Afterlife Records", "Tale Of Us", "Innervisions",
    "Ben Böhmer", "Agents Of Time", "Kiasmos",
]

REFERENCES_EVENING = [
    "Alignment", "Truncate", "Paula Temple", "Surgeon", "Blawan",
    "Skudge", "Industrialyzer", "Rebekah", "Answer Code Request",
]

TITLE_WORDS_MORNING = [
    "Liminal", "Threshold", "Meridian", "Solstice", "Vesper", "Ether",
    "Convergence", "Flux", "Orbit", "Resonance", "Stasis", "Drift",
    "Bloom", "Ascent", "Aether", "Equinox", "Parallax", "Interval",
]

TITLE_WORDS_EVENING = [
    "Collapse", "Fracture", "Void", "Forge", "Grind", "Impact", "Circuit",
    "Breach", "Surge", "Ignition", "Decay", "Pressure", "Ritual", "Axis",
    "Strike", "Torque", "Null", "Cascade", "Vortex", "Fault",
]

TITLE_SUFFIXES = [
    "State", "Protocol", "Sequence", "Signal", "Mode", "Form",
    "Phase", "Vector", "Core", "System", "Gate", "Field",
]


def _pick(*pools) -> list:
    return [random.choice(p) for p in pools]


def _generate_title(morning: bool) -> str:
    words = TITLE_WORDS_MORNING if morning else TITLE_WORDS_EVENING
    w = random.choice(words)
    if random.random() > 0.4:
        return f"{w} {random.choice(TITLE_SUFFIXES)}"
    return w


# ── PROMPT BUILDERS ───────────────────────────────────────────────────────────

def build_morning_prompt(report: TrendReport, track_number: int) -> MusicPrompt:
    bpm = 124
    key = "F minor"
    refs = random.sample(REFERENCES_MORNING, 2)
    moods = random.sample(MORNING_MOODS, 3)
    elements = random.sample(MORNING_ELEMENTS, 4)

    # Fold in reddit/lastfm mood tags if relevant
    extra_moods = [m for m in report.mood_tags if m in {"hypnotic","melodic","emotional","spiritual","ritual","liminal","drone","ambient"}]
    moods = list(dict.fromkeys(extra_moods[:2] + moods))[:4]

    prompt = (
        f"A {bpm} BPM melodic techno track in {key}. "
        f"{moods[0].capitalize()}, {moods[1]}, and {moods[2]} atmosphere. "
        f"Features {elements[0]}, {elements[1]}, {elements[2]}, and {elements[3]}. "
        f"Inspired by {refs[0]} and {refs[1]}. "
        "Slow build over 8 bars. No lyrics except one whispered phrase buried deep in reverb. "
        "Suitable for a Berlin underground after-hours set. "
        "Sacred geometry energy — mathematical, meditative, hypnotic."
    )

    negative = (
        "No commercial pop elements. No happy chord progressions. No major key. "
        "No vocals or singing. No EDM drops. No mainstream festival sounds."
    )

    title = _generate_title(morning=True)

    return MusicPrompt(
        drop_type="morning",
        title=title,
        bpm=bpm,
        key=key,
        style="Melodic Techno",
        prompt=prompt,
        negative_prompt=negative,
    )


def build_evening_prompt(report: TrendReport, track_number: int) -> MusicPrompt:
    bpm = 134
    key = "A minor"
    refs = random.sample(REFERENCES_EVENING, 2)
    moods = random.sample(EVENING_MOODS, 3)
    elements = random.sample(EVENING_ELEMENTS, 4)

    extra_moods = [m for m in report.mood_tags if m in {"industrial","dark","relentless","primal","void","ritual","noise"}]
    moods = list(dict.fromkeys(extra_moods[:2] + moods))[:4]

    prompt = (
        f"A {bpm} BPM peak-time industrial techno track in {key}. "
        f"{moods[0].capitalize()}, {moods[1]}, and {moods[2]} energy. "
        f"Features {elements[0]}, {elements[1]}, {elements[2]}, and {elements[3]}. "
        f"Inspired by {refs[0]} and {refs[1]}. "
        "Hard, pounding, relentless. Built for peak-time warehouse raving. "
        "No breakdowns — pure momentum. Machine precision with human aggression. "
        "Dark Berlin underground energy."
    )

    negative = (
        "No melody. No pleasant harmony. No pop elements. No soft sounds. "
        "No vocals. No uplifting moments."
    )

    title = _generate_title(morning=False)

    return MusicPrompt(
        drop_type="evening",
        title=title,
        bpm=bpm,
        key=key,
        style="Industrial Techno",
        prompt=prompt,
        negative_prompt=negative,
    )


# ── MAIN ENTRY ────────────────────────────────────────────────────────────────

def generate_prompts(report: TrendReport, track_number: int) -> tuple[MusicPrompt, MusicPrompt]:
    """Return (morning_prompt, evening_prompt) based on today's trend report."""
    morning = build_morning_prompt(report, track_number)
    evening = build_evening_prompt(report, track_number)
    return morning, evening


if __name__ == "__main__":
    import json
    from trend_scraper import TrendReport

    dummy = TrendReport(
        date="2026-03-09",
        mood_tags=["hypnotic", "dark", "industrial"],
    )
    m, e = generate_prompts(dummy, track_number=1)
    print("=== MORNING ===")
    print(f"Title: {m.title}")
    print(f"Prompt: {m.prompt}\n")
    print("=== EVENING ===")
    print(f"Title: {e.title}")
    print(f"Prompt: {e.prompt}")
