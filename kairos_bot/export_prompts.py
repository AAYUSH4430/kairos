"""
export_prompts.py — Generate today's prompts and print them ready to paste into Colab.

Usage:
    python export_prompts.py
    python export_prompts.py --drop morning
    python export_prompts.py --drop evening
"""

import argparse
import json
import os
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
load_dotenv(Path(__file__).parent / ".env")

from trend_scraper import gather_trends, TrendReport
from prompt_generator import generate_prompts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", choices=["morning", "evening", "both"], default="both")
    args = parser.parse_args()

    trends_cache = Path(__file__).parent / "trends_cache.json"
    if trends_cache.exists():
        mtime = datetime.date.fromtimestamp(trends_cache.stat().st_mtime)
        if mtime == datetime.date.today():
            raw = json.loads(trends_cache.read_text(encoding="utf-8"))
            report = TrendReport(**{k: v for k, v in raw.items() if k in TrendReport.__dataclass_fields__})
        else:
            report = gather_trends(str(trends_cache))
    else:
        report = gather_trends(str(trends_cache))

    manifest = Path(__file__).parent.parent / "tracks.json"
    existing = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    next_id = max((int(t["id"]) for t in existing), default=1) + 1

    morning, evening = generate_prompts(report, next_id)

    drops = []
    if args.drop in ("morning", "both"):
        drops.append(morning)
    if args.drop in ("evening", "both"):
        drops.append(evening)

    output = []
    for p in drops:
        output.append({
            "drop_type": p.drop_type,
            "title": p.title,
            "bpm": p.bpm,
            "key": p.key,
            "style": p.style,
            "prompt": p.prompt,
            "negative_prompt": p.negative_prompt,
            "track_number": next_id if p.drop_type == "morning" else next_id + 1,
        })

    out_path = Path(__file__).parent / "prompts_today.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("  KAIROS — TODAY'S PROMPTS")
    print("=" * 60)
    for p in output:
        print(f"\n  [{p['drop_type'].upper()} DROP]  Track #{p['track_number']:03d}")
        print(f"  Title : {p['title']}")
        print(f"  Style : {p['bpm']} BPM · {p['key']} · {p['style']}")
        print(f"\n  PROMPT:\n  {p['prompt']}")
        print()

    print(f"  Saved to: {out_path}")
    print("  Copy the prompt into the Colab notebook to generate audio.")
    print("=" * 60 + "\n")

    # Send email if credentials are configured
    email_user = os.getenv("GMAIL_USER")
    email_pass = os.getenv("GMAIL_APP_PASSWORD")
    if email_user and email_pass:
        _send_email(email_user, email_pass, output)
    else:
        print("  (Email not configured — set GMAIL_USER and GMAIL_APP_PASSWORD in .env to enable)")


def _send_email(gmail_user: str, app_password: str, prompts: list) -> None:
    import smtplib
    from email.mime.text import MIMEText

    lines = ["KΛIROS — Today's Prompts\n"]
    for p in prompts:
        lines.append(f"[{p['drop_type'].upper()} DROP] — {p['title']}")
        lines.append(f"  {p['bpm']} BPM · {p['key']} · {p['style']}\n")
        lines.append(f"PROMPT:\n{p['prompt']}\n")
        lines.append("-" * 50)

    body = "\n".join(lines)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"KΛIROS Prompts Ready — {datetime.date.today()}"
    msg["From"]    = gmail_user
    msg["To"]      = gmail_user

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, app_password)
            smtp.send_message(msg)
        print(f"  Email sent to {gmail_user}")
    except Exception as e:
        print(f"  Email failed: {e}")


if __name__ == "__main__":
    main()
