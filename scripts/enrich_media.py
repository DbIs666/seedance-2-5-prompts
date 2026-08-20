#!/usr/bin/env python3
"""Backfill media.thumb_url / media.video_url (and optional engagement) from X posts.

Uses the public fxtwitter API. Does not commit large binaries — only stores URLs.
X CDN video links may expire; thumbnails are usually more durable. Always keep source.url.

Usage:
  python scripts/enrich_media.py              # fill empty media fields
  python scripts/enrich_media.py --force      # refresh all from source.url
  python scripts/enrich_media.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "data" / "prompts"


def log_score(likes: int, reposts: int, views: int) -> float:
    return round(
        3 * math.log10(likes + 1)
        + 4 * math.log10(reposts + 1)
        + 1 * math.log10(views + 1),
        1,
    )


def status_id_from_url(url: str) -> str | None:
    m = re.search(r"(?:x|twitter)\.com/.+/status/(\d+)", url or "")
    return m.group(1) if m else None


def fetch_tweet(status_id: str) -> dict:
    api = f"https://api.fxtwitter.com/status/{status_id}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0 seedance-prompts"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return data.get("tweet") or {}


def pick_media(tweet: dict) -> tuple[str, str, float | None]:
    media = tweet.get("media") or {}
    videos = media.get("videos") or []
    all_items = media.get("all") or []
    candidates = videos or [x for x in all_items if (x or {}).get("type") == "video"] or all_items

    thumb = ""
    video = ""
    duration: float | None = None

    for item in candidates:
        if not isinstance(item, dict):
            continue
        if not thumb:
            thumb = (item.get("thumbnail_url") or item.get("thumbnail") or "").strip()
        if not video:
            # Prefer highest-bitrate mp4 when variants exist
            variants = item.get("variants") or item.get("formats") or []
            mp4s = [
                v
                for v in variants
                if isinstance(v, dict)
                and (
                    str(v.get("content_type", "")).startswith("video/mp4")
                    or str(v.get("container", "")).lower() == "mp4"
                    or str(v.get("url", "")).endswith(".mp4")
                    or ".mp4" in str(v.get("url", ""))
                )
            ]
            if mp4s:
                mp4s.sort(key=lambda v: int(v.get("bitrate") or 0), reverse=True)
                video = (mp4s[0].get("url") or "").strip()
            if not video:
                video = (item.get("url") or "").strip()
        if duration is None and item.get("duration") is not None:
            try:
                duration = float(item["duration"])
            except (TypeError, ValueError):
                duration = None
        if thumb and video:
            break

    # photos as fallback thumb
    if not thumb:
        for item in all_items:
            if isinstance(item, dict) and (item.get("type") == "photo" or item.get("url")):
                thumb = (item.get("thumbnail_url") or item.get("url") or "").strip()
                if thumb:
                    break

    return thumb, video, duration


def enrich_file(path: Path, force: bool, dry_run: bool, refresh_engagement: bool) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    src = data.setdefault("source", {})
    media = data.setdefault("media", {})
    url = (src.get("url") or "").strip()
    sid = status_id_from_url(url)
    if not sid:
        return False

    need_media = force or not (media.get("thumb_url") and media.get("video_url"))
    if not need_media and not refresh_engagement:
        return False

    try:
        tweet = fetch_tweet(sid)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  FAIL {path.name}: {exc}")
        return False
    if not tweet:
        print(f"  FAIL {path.name}: empty tweet")
        return False

    changed = False
    thumb, video, duration = pick_media(tweet)

    if need_media:
        if thumb and (force or not media.get("thumb_url")):
            media["thumb_url"] = thumb
            changed = True
        if video and (force or not media.get("video_url")):
            media["video_url"] = video
            changed = True
        if duration is not None and (force or media.get("duration_sec") in (None, "", 0)):
            media["duration_sec"] = duration
            changed = True

    if refresh_engagement or force:
        for key, tw_key in (("likes", "likes"), ("reposts", "retweets"), ("views", "views")):
            if tweet.get(tw_key) is not None:
                val = int(tweet.get(tw_key) or 0)
                if src.get(key) != val:
                    src[key] = val
                    changed = True
        data["score"] = log_score(
            int(src.get("likes") or 0),
            int(src.get("reposts") or 0),
            int(src.get("views") or 0),
        )

    # Fill author profile if missing
    author = data.setdefault("author", {})
    tw_author = tweet.get("author") or {}
    handle = tw_author.get("screen_name") or ""
    if handle:
        if force or not author.get("x_handle"):
            author["x_handle"] = f"@{handle}"
            changed = True
        if force or not author.get("profile_url"):
            author["profile_url"] = f"https://x.com/{handle}"
            changed = True
        if (force or not author.get("name")) and tw_author.get("name"):
            author["name"] = tw_author["name"]
            changed = True

    if changed and not dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = "DRY" if dry_run else ("OK" if changed else "skip")
    print(
        f"  {status} {data.get('id')} thumb={'yes' if media.get('thumb_url') else 'no'} "
        f"video={'yes' if media.get('video_url') else 'no'}"
    )
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich prompt JSON media from X")
    parser.add_argument("--force", action="store_true", help="Overwrite existing media URLs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--engagement",
        action="store_true",
        help="Also refresh likes/reposts/views/score",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.35,
        help="Delay between API calls (seconds)",
    )
    args = parser.parse_args()

    files = sorted(
        p
        for p in PROMPTS_DIR.rglob("*.json")
        if "examples" not in p.parts and p.name != "schema.json"
    )
    print(f"Scanning {len(files)} prompt files...")
    updated = 0
    for i, path in enumerate(files):
        if enrich_file(path, force=args.force, dry_run=args.dry_run, refresh_engagement=args.engagement):
            updated += 1
        if i + 1 < len(files):
            time.sleep(args.sleep)
    print(f"Done. {'Would update' if args.dry_run else 'Updated'} {updated} file(s).")
    if updated and not args.dry_run:
        print("Run: python scripts/generate_readme.py")


if __name__ == "__main__":
    main()
