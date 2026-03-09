"""
music_generator.py — Generates audio using MusicGen via HuggingFace transformers.

Models (smallest to largest):
    facebook/musicgen-small   ~300M — fastest (~5 min CPU)
    facebook/musicgen-medium  ~1.5B — balanced
    facebook/musicgen-large   ~3.3B — best quality

CPU only: small model is recommended (~5-8 min per 30s clip).
"""

import os
import logging
import datetime
import numpy as np
import scipy.io.wavfile
from pathlib import Path
from prompt_generator import MusicPrompt

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("KAIROS_OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLIP_DURATION  = int(os.getenv("MUSICGEN_DURATION", "30"))
MODEL_NAME     = os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small")

_model     = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor

    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    log.info("Loading MusicGen model: %s  (first run downloads ~500MB)", MODEL_NAME)
    _processor = AutoProcessor.from_pretrained(MODEL_NAME)
    _model     = MusicgenForConditionalGeneration.from_pretrained(MODEL_NAME)
    log.info("Model loaded.")
    return _model, _processor


def generate_audio(prompt: MusicPrompt, track_number: int) -> Path:
    """Generate audio and save to OUTPUT_DIR. Returns path to saved .wav file."""
    model, processor = _load_model()

    log.info("Generating '%s' [%s drop · %s BPM · %s]", prompt.title, prompt.drop_type, prompt.bpm, prompt.key)
    log.info("Prompt: %s", prompt.prompt[:100] + "...")

    # Tokens per second is ~50 for MusicGen; CLIP_DURATION * 50 = max_new_tokens
    max_tokens = CLIP_DURATION * 50

    inputs = processor(text=[prompt.prompt], padding=True, return_tensors="pt")

    log.info("Running generation — this takes ~5-10 min on CPU, grab a coffee...")
    audio_values = model.generate(**inputs, max_new_tokens=max_tokens)

    # audio_values shape: [batch, channels, samples]
    sample_rate = model.config.audio_encoder.sampling_rate
    audio_np    = audio_values[0, 0].numpy()  # mono, first batch

    # Normalise to int16
    audio_int16 = np.int16(audio_np / np.max(np.abs(audio_np)) * 32767)

    date_str = datetime.date.today().strftime("%Y%m%d")
    safe_title = prompt.title.lower().replace(" ", "_")
    filename = f"transmission_{track_number:03d}_{date_str}_{prompt.drop_type}_{safe_title}.wav"
    out_path = OUTPUT_DIR / filename

    scipy.io.wavfile.write(str(out_path), sample_rate, audio_int16)
    log.info("Saved: %s", out_path)
    return out_path


def convert_to_mp3(wav_path: Path) -> Path:
    mp3_path = wav_path.with_suffix(".mp3")
    ret = os.system(f'ffmpeg -y -i "{wav_path}" -codec:a libmp3lame -qscale:a 2 "{mp3_path}" -loglevel quiet')
    if ret == 0:
        log.info("Converted to MP3: %s", mp3_path)
        return mp3_path
    log.warning("ffmpeg not found — keeping WAV")
    return wav_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s")

    import sys
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)

    from trend_scraper import TrendReport
    from prompt_generator import generate_prompts

    report = TrendReport(date=datetime.date.today().isoformat(), mood_tags=["hypnotic", "dark"])
    morning, _ = generate_prompts(report, track_number=2)

    wav = generate_audio(morning, track_number=2)
    out = convert_to_mp3(wav)
    print(f"\nDone: {out}")
