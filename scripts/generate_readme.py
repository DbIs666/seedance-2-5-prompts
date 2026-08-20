#!/usr/bin/env python3
"""Generate README, daily digests, category pages, index, and CHANGELOG from prompt JSON files."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "data" / "prompts"
INDEX_PATH = ROOT / "data" / "index.json"
README_PATH = ROOT / "README.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
DAILY_DIR = ROOT / "daily"
CATEGORIES_DIR = ROOT / "categories"

CATEGORIES = [
    "cinematic",
    "ads",
    "ugc",
    "anime",
    "drama",
    "vfx",
    "product",
    "meme",
    "other",
]

CATEGORY_LABELS = {
    "cinematic": "Cinematic",
    "ads": "Advertising & Commercial",
    "ugc": "UGC",
    "anime": "Anime & Animation",
    "drama": "Short Drama & Emotion",
    "vfx": "VFX & Experimental",
    "product": "Product Showcase",
    "meme": "Social & Meme",
    "other": "Other",
}

LANG_BADGE = {
    "en": "https://img.shields.io/badge/lang-English-blue",
    "zh": "https://img.shields.io/badge/lang-中文-red",
    "mixed": "https://img.shields.io/badge/lang-Mixed-purple",
    "other": "https://img.shields.io/badge/lang-Other-lightgrey",
}

MODEL_BADGE = {
    "seedance-2.5": "https://img.shields.io/badge/Seedance-2.5-0ea5e9",
    "seedance-2.0": "https://img.shields.io/badge/Seedance-2.0-38bdf8",
    "seedance-2.x": "https://img.shields.io/badge/Seedance-2.x-94a3b8",
}

# README keeps full cards for featured + top N of latest day to stay readable.
README_LATEST_FULL_CARDS = 8
README_FEATURED_FULL_CARDS = 6


def log_score(likes: int, reposts: int, views: int) -> float:
    return round(
        3 * math.log10(likes + 1)
        + 4 * math.log10(reposts + 1)
        + 1 * math.log10(views + 1),
        1,
    )


def load_prompts() -> list[dict]:
    items: list[dict] = []
    if not PROMPTS_DIR.exists():
        return items
    for path in sorted(PROMPTS_DIR.rglob("*.json")):
        if path.name == "schema.json":
            continue
        if "examples" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON: {path}: {exc}") from exc
        if "id" not in data or "prompt" not in data:
            continue
        data["_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
        src = data.get("source") or {}
        if not data.get("score"):
            data["score"] = log_score(
                int(src.get("likes") or 0),
                int(src.get("reposts") or 0),
                int(src.get("views") or 0),
            )
        items.append(data)
    items.sort(key=lambda p: (p.get("collected_at") or "", p.get("id") or ""), reverse=True)
    return items


def fmt_int(n: int | None) -> str:
    if n is None:
        return "—"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 10_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    if n >= 1_000:
        return f"{n:,}"
    return str(n)


def format_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        raw = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%b %d, %Y")
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", iso)
        return m.group(1) if m else iso


def author_parts(p: dict) -> tuple[str, str, str]:
    author = p.get("author") or {}
    name = (author.get("name") or "Unknown").strip() or "Unknown"
    handle = (author.get("x_handle") or "").strip()
    profile = (author.get("profile_url") or "").strip()
    if not profile and handle:
        h = handle.lstrip("@")
        profile = f"https://x.com/{h}"
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"
    return name, handle, profile


def badge_row(p: dict) -> str:
    model = p.get("model") or "seedance-2.x"
    lang = p.get("language") or "en"
    bits = [
        f"![model]({MODEL_BADGE.get(model, MODEL_BADGE['seedance-2.x'])})",
        f"![lang]({LANG_BADGE.get(lang, LANG_BADGE['other'])})",
    ]
    if p.get("featured"):
        bits.append("![Featured](https://img.shields.io/badge/%E2%AD%90-Featured-gold)")
    for cat in (p.get("category") or [])[:3]:
        label = cat.replace("-", "_")
        bits.append(f"![cat](https://img.shields.io/badge/{label}-1e293b)")
    return " ".join(bits)


def media_block(p: dict, img_width: int = 680) -> str:
    """Centered video/thumb preview with links to video and/or X post."""
    media = p.get("media") or {}
    src = p.get("source") or {}
    thumb = (media.get("thumb_url") or "").strip()
    video = (media.get("video_url") or "").strip()
    source_url = (src.get("url") or "").strip()
    title = xml_escape(p.get("title") or p.get("id") or "prompt")
    href = video or source_url

    lines = ['<div align="center">', ""]
    if thumb and href:
        lines.append(f'<a href="{href}">')
        lines.append(
            f'<img src="{thumb}" width="{img_width}" alt="{title}" '
            f'style="border-radius:12px;max-width:100%;">'
        )
        lines.append("</a>")
        lines.append("")
        actions = []
        if video:
            actions.append(f"**[▶ Watch video]({video})**")
        if source_url:
            actions.append(f"**[↗ View on X]({source_url})**")
        if actions:
            lines.append(" · ".join(actions))
            lines.append("")
        if video:
            lines.append("*Click image to open the video · X CDN links may expire; use the post if needed.*")
            lines.append("")
    elif thumb:
        lines.append(
            f'<img src="{thumb}" width="{img_width}" alt="{title}" '
            f'style="border-radius:12px;max-width:100%;">'
        )
        lines.append("")
        if source_url:
            lines.append(f"**[↗ View on X]({source_url})**")
            lines.append("")
    elif source_url:
        lines.append(f"**[↗ Watch / discuss on X]({source_url})**")
        lines.append("")
        lines.append("_No thumbnail stored yet — open the original post for the video._")
        lines.append("")
    else:
        lines.append("_No media preview available._")
        lines.append("")
    lines.append("</div>")
    lines.append("")
    return "\n".join(lines)


def details_block(p: dict) -> str:
    name, handle, profile = author_parts(p)
    src = p.get("source") or {}
    source_url = (src.get("url") or "").strip()
    platform = (src.get("platform") or "source").upper()
    if platform == "X":
        source_label = "X Post"
    elif platform == "TWITTER":
        source_label = "Twitter Post"
    else:
        source_label = "Original post"

    if profile:
        author_md = f"[{name}]({profile})"
        if handle:
            author_md += f" ([{handle}]({profile}))"
    elif handle:
        author_md = handle
    else:
        author_md = name

    source_md = f"[{source_label}]({source_url})" if source_url else "—"
    published = format_date(src.get("posted_at") or "")
    engagement = (
        f"❤ {fmt_int(src.get('likes'))} · "
        f"🔁 {fmt_int(src.get('reposts'))} · "
        f"👁 {fmt_int(src.get('views'))}"
    )
    if p.get("score"):
        engagement += f" · score `{p.get('score')}`"

    tags = ", ".join(f"`{t}`" for t in (p.get("tags") or [])) or "—"
    path = p.get("_path") or ""
    json_line = f"[`{p.get('id')}`]({path})" if path else f"`{p.get('id')}`"

    lines = [
        f"- **Author:** {author_md}",
        f"- **Source:** {source_md}",
        f"- **Published:** {published}",
        f"- **Engagement:** {engagement}",
        f"- **ID:** {json_line}",
        f"- **Tags:** {tags}",
    ]
    notes = (p.get("notes") or "").strip()
    if notes:
        lines.append(f"- **Notes:** {notes}")
    return "\n".join(lines) + "\n"


def render_card(
    p: dict,
    heading_level: int = 3,
    *,
    rank: int | None = None,
    img_width: int = 680,
    show_prompt: bool = True,
) -> str:
    """Rich prompt card: badges, prompt, media preview, author/source links."""
    h = "#" * heading_level
    title = p.get("title") or p.get("id") or "Untitled"
    rank_prefix = f"No. {rank}: " if rank is not None else ""
    featured_mark = " ⭐" if p.get("featured") else ""
    model = p.get("model") or "seedance-2.x"
    cats = ", ".join(p.get("category") or []) or "—"
    prompt = (p.get("prompt") or "").rstrip()

    parts = [
        f"{h} {rank_prefix}{title}{featured_mark}",
        "",
        badge_row(p),
        "",
        f"`{p.get('id', '')}` · `{model}` · {cats}",
        "",
    ]

    if show_prompt:
        parts.extend(
            [
                "#### Prompt",
                "",
                "```text",
                prompt,
                "```",
                "",
            ]
        )

    parts.extend(
        [
            "#### Video",
            "",
            media_block(p, img_width=img_width),
            "#### Details",
            "",
            details_block(p),
        ]
    )
    return "\n".join(parts).rstrip() + "\n"


def render_compact_row(p: dict) -> str:
    """One-line index entry with author + source + optional thumb."""
    name, handle, profile = author_parts(p)
    src = p.get("source") or {}
    source_url = (src.get("url") or "").strip()
    media = p.get("media") or {}
    thumb = (media.get("thumb_url") or "").strip()
    path = p.get("_path") or ""
    title = p.get("title") or p.get("id")
    star = " ⭐" if p.get("featured") else ""

    author_md = f"[{name}]({profile})" if profile else name
    if handle and profile:
        author_md = f"[{handle}]({profile})"
    source_md = f"[post]({source_url})" if source_url else "—"
    json_md = f"[json]({path})" if path else ""
    thumb_md = f"[thumb]({thumb})" if thumb else ""
    extras = " · ".join(x for x in (author_md, source_md, thumb_md, json_md) if x)
    score = p.get("score") or 0
    model = p.get("model") or ""
    return (
        f"- **{title}**{star} — `{p.get('id')}` · `{model}` · "
        f"❤ {fmt_int(src.get('likes'))} · score {score} · {extras}"
    )


def day_key(p: dict) -> str:
    collected = p.get("collected_at") or ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", collected)
    if m:
        return m.group(1)
    pid = p.get("id") or ""
    if re.match(r"^\d{8}-", pid):
        return f"{pid[0:4]}-{pid[4:6]}-{pid[6:8]}"
    return "unknown"


def build_index(prompts: list[dict]) -> dict:
    by_model: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    entries = []
    for p in prompts:
        by_model[p.get("model") or "seedance-2.x"] += 1
        for c in p.get("category") or ["other"]:
            by_category[c] += 1
        media = p.get("media") or {}
        author = p.get("author") or {}
        entries.append(
            {
                "id": p["id"],
                "title": p.get("title"),
                "model": p.get("model"),
                "category": p.get("category"),
                "score": p.get("score"),
                "collected_at": p.get("collected_at"),
                "path": p.get("_path"),
                "source_url": (p.get("source") or {}).get("url"),
                "author": author.get("name"),
                "author_url": author.get("profile_url"),
                "thumb_url": media.get("thumb_url") or "",
                "video_url": media.get("video_url") or "",
                "featured": bool(p.get("featured")),
            }
        )
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(prompts),
        "by_model": dict(by_model),
        "by_category": dict(by_category),
        "prompts": entries,
    }


def join_cards(items: list[dict], heading_level: int = 3, ranked: bool = False) -> str:
    blocks = []
    for i, p in enumerate(items, 1):
        blocks.append(
            render_card(
                p,
                heading_level=heading_level,
                rank=i if ranked else None,
            )
        )
    return "\n---\n\n".join(blocks)


def write_daily(prompts: list[dict]) -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list[dict]] = defaultdict(list)
    for p in prompts:
        by_day[day_key(p)].append(p)

    for day, items in sorted(by_day.items(), reverse=True):
        if day == "unknown":
            continue
        items_sorted = sorted(items, key=lambda x: x.get("score") or 0, reverse=True)
        cards = join_cards(items_sorted, heading_level=3, ranked=True)
        body = f"""# Daily Digest — {day}

> Seedance **2.5** first, **2.0** compatible. Curated from high-engagement community posts (mostly X).

**Added this day:** {len(items_sorted)} prompt(s)

Each card includes the **full prompt**, **author X profile**, **source post**, and **video/thumbnail** when available.

---

{cards}

---

[← Back to README](../README.md)
"""
        (DAILY_DIR / f"{day}.md").write_text(body, encoding="utf-8")


def write_categories(prompts: list[dict]) -> None:
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for p in prompts:
        cats = p.get("category") or ["other"]
        for c in cats:
            by_cat[c].append(p)

    for cat in CATEGORIES:
        items = sorted(by_cat.get(cat, []), key=lambda x: x.get("score") or 0, reverse=True)
        if items:
            cards = join_cards(items, heading_level=3, ranked=False)
        else:
            cards = "_No prompts in this category yet._\n"
        body = f"""# {CATEGORY_LABELS.get(cat, cat)}

Prompts tagged `{cat}`. Primary focus: Seedance 2.5 (2.0 compatible).

**Count:** {len(items)}

---

{cards}

[← Back to README](../README.md)
"""
        (CATEGORIES_DIR / f"{cat}.md").write_text(body, encoding="utf-8")


def write_readme(prompts: list[dict], index: dict) -> None:
    featured = [p for p in prompts if p.get("featured")]
    featured = sorted(featured, key=lambda x: x.get("score") or 0, reverse=True)
    featured = featured[:README_FEATURED_FULL_CARDS]
    if not featured and prompts:
        featured = sorted(prompts, key=lambda x: x.get("score") or 0, reverse=True)[:3]

    days = sorted({day_key(p) for p in prompts if day_key(p) != "unknown"}, reverse=True)
    latest_day = days[0] if days else None
    latest_items = (
        sorted(
            [p for p in prompts if day_key(p) == latest_day],
            key=lambda x: x.get("score") or 0,
            reverse=True,
        )
        if latest_day
        else []
    )
    latest_full = latest_items[:README_LATEST_FULL_CARDS]
    latest_rest = latest_items[README_LATEST_FULL_CARDS:]

    top = sorted(prompts, key=lambda x: x.get("score") or 0, reverse=True)[:12]
    recent = prompts[:12]

    cat_table_rows = []
    for cat in CATEGORIES:
        count = index.get("by_category", {}).get(cat, 0)
        cat_table_rows.append(
            f"| [{CATEGORY_LABELS[cat]}](categories/{cat}.md) | `{cat}` | {count} |"
        )
    cat_table = "\n".join(cat_table_rows)

    model_bits = index.get("by_model") or {}
    model_line = ", ".join(f"`{k}`: {v}" for k, v in sorted(model_bits.items())) or "none"

    daily_links = (
        "\n".join(f"- [{d}](daily/{d}.md)" for d in days[:14])
        if days
        else "_No daily digests yet._"
    )

    featured_section = (
        join_cards(featured, heading_level=3, ranked=True)
        if featured
        else "_No featured prompts yet._\n"
    )

    if latest_day and latest_full:
        latest_section = (
            f"### {latest_day} — {len(latest_items)} new\n\n"
            f"Full cards below (top {len(latest_full)} by score). "
            f"See the [daily digest](daily/{latest_day}.md) for every card that day.\n\n"
            f"{join_cards(latest_full, heading_level=4, ranked=True)}"
        )
        if latest_rest:
            latest_section += "\n#### More from this day\n\n"
            latest_section += "\n".join(render_compact_row(p) for p in latest_rest) + "\n"
    else:
        latest_section = "_None yet. Add the first prompt via the daily workflow in `AGENTS.md`._\n"

    top_list = "\n".join(render_compact_row(p) for p in top) + "\n" if top else "_None yet._\n"
    recent_list = (
        "\n".join(render_compact_row(p) for p in recent) + "\n" if recent else "_None yet._\n"
    )

    toc = """## Table of contents

- [Stats](#stats)
- [Featured prompts](#featured-prompts)
- [Latest day](#latest-day)
- [Top by engagement](#top-by-engagement)
- [Recent additions](#recent-additions)
- [Categories](#categories)
- [Daily digests](#daily-digests)
- [How cards work](#how-cards-work)
- [Add prompts](#add-prompts-human--agent)
"""

    readme = f"""# Seedance 2.5 Prompts

[![Seedance 2.5](https://img.shields.io/badge/Seedance-2.5_primary-0ea5e9)](#)
[![Seedance 2.0](https://img.shields.io/badge/Seedance-2.0_compatible-38bdf8)](#)
[![Prompts](https://img.shields.io/badge/prompts-{index.get('total', 0)}-f97316)](data/prompts/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Daily-curated video prompts for ByteDance Seedance** — **2.5 first**, **2.0 compatible**.  
> Each entry is a **rich card**: full prompt, **author X profile**, **source post**, and **video thumbnail** when available.

This repo is designed for a simple loop: **you drop links or prompts → the curator agent adds structured JSON → docs regenerate into browsable cards**.

{toc}

---

## Why this repo

| Goal | How we do it |
|------|----------------|
| Stay current | Daily digests under [`daily/`](daily/) |
| Prefer 2.5 | `model` field marks `seedance-2.5` / `seedance-2.0` / `seedance-2.x` |
| Stay usable | Full copy-paste prompts + author/source links on every card |
| Show results | Thumbnail + video link when the X post has media |
| Stay maintainable | One JSON file per prompt; generated README / daily / categories |

**Not** a generic ChatGPT prompt dump. **Not** claiming ownership of community prompts.

---

## Stats

| Metric | Value |
|--------|------:|
| Total prompts | **{index.get('total', 0)}** |
| By model | {model_line} |
| Last index update | {index.get('updated_at', '—')} |

---

## Featured prompts

> Hand-picked or top-signal prompts with full cards.

{featured_section}

---

## Latest day

{latest_section}

---

## Top by engagement

{top_list}

---

## Recent additions

{recent_list}

---

## Categories

| Category | Tag | Count |
|----------|-----|------:|
{cat_table}

---

## Daily digests

{daily_links}

---

## How cards work

Every prompt card aims to include:

| Block | Content |
|-------|---------|
| Badges | Model, language, categories, featured |
| Prompt | Full copy-paste text |
| Video | Clickable thumbnail → video URL (or X post) |
| Details | **Author X profile**, **source post**, engagement, tags, JSON path |

Media fields live in each prompt JSON:

```json
"media": {{
  "video_url": "https://video.twimg.com/...",
  "thumb_url": "https://pbs.twimg.com/...",
  "duration_sec": 10.0
}}
```

Prefer **linking** media over committing large binaries. X CDN video URLs can expire; always keep `source.url`.

After JSON changes:

```bash
python scripts/generate_readme.py
```

To refresh thumbnails/videos from X for existing entries:

```bash
python scripts/enrich_media.py
```

---

## Repository layout

```text
data/prompts/YYYY-MM-DD/<id>.json   # source of truth (incl. author + media)
data/schema.json                    # JSON shape
data/index.json                     # generated index
data/sources.json                   # watchlist keywords / accounts
daily/YYYY-MM-DD.md                 # generated daily digest (full cards)
categories/*.md                     # generated category pages (full cards)
scripts/generate_readme.py          # rebuild docs / cards
scripts/enrich_media.py             # backfill thumb/video from X
AGENTS.md                           # rules for the daily curator agent
```

---

## Add prompts (human → agent)

You can ask the curator agent every day with any of:

```text
Add this prompt: https://x.com/.../status/...
```

```text
Daily update:
1) <url or pasted prompt>
2) <url or pasted prompt>
```

```text
Add prompt for Seedance 2.5
Author: @handle
Link: https://x.com/...
Likes: 1200
Prompt:
...
```

The agent will write JSON **with author profile + media when available**, then regenerate **rich cards** automatically.

Human cheatsheet: **[`HOW_TO_DAILY.md`](HOW_TO_DAILY.md)**  
Rules for the agent: **[`AGENTS.md`](AGENTS.md)**  
Contribution notes: **[`CONTRIBUTING.md`](CONTRIBUTING.md)**

---

## Prompt JSON (minimal example)

```json
{{
  "id": "20260814-001",
  "title": "Rainy night car chase",
  "prompt": "Full prompt text...",
  "model": "seedance-2.5",
  "category": ["cinematic"],
  "language": "en",
  "author": {{
    "name": "Creator",
    "x_handle": "@creator",
    "profile_url": "https://x.com/creator"
  }},
  "source": {{
    "platform": "x",
    "url": "https://x.com/creator/status/123",
    "posted_at": "2026-08-14T12:00:00Z",
    "likes": 1000,
    "reposts": 100,
    "views": 50000
  }},
  "media": {{
    "video_url": "https://video.twimg.com/...",
    "thumb_url": "https://pbs.twimg.com/...",
    "duration_sec": 12.5
  }},
  "collected_at": "2026-08-14T09:00:00Z",
  "featured": false,
  "tags": ["multi-shot", "night"],
  "notes": ""
}}
```

---

## Copyright & takedown

Prompts are collected from the public community for **educational and archival** purposes.  
Rights remain with the original creators.

If you are a creator and want content removed, open an issue with the prompt `id` or source URL and we will delete it promptly.

---

## License

Code and documentation scaffolding: [MIT](LICENSE).  
Prompt text and media: copyright of original authors; retained here with attribution for learning use.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
"""
    readme = readme.replace("{{", "{").replace("}}", "}")
    README_PATH.write_text(readme, encoding="utf-8")


def write_changelog(prompts: list[dict]) -> None:
    by_day: dict[str, list[dict]] = defaultdict(list)
    for p in prompts:
        by_day[day_key(p)].append(p)

    lines = [
        "# Changelog",
        "",
        "All notable prompt additions are listed here (generated).",
        "",
    ]
    for day in sorted(by_day.keys(), reverse=True):
        if day == "unknown":
            continue
        items = sorted(by_day[day], key=lambda x: x.get("id") or "")
        lines.append(f"## {day}")
        lines.append("")
        lines.append(f"- Added **{len(items)}** prompt(s)")
        for p in items:
            lines.append(
                f"  - `{p['id']}` — {p.get('title', '')} (`{p.get('model', '')}`)"
            )
        lines.append("")

    if len(lines) == 4:
        lines.append("_No entries yet._")
        lines.append("")

    CHANGELOG_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    prompts = load_prompts()
    index = build_index(prompts)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_daily(prompts)
    write_categories(prompts)
    write_readme(prompts, index)
    write_changelog(prompts)
    print(f"OK — {len(prompts)} prompts indexed.")
    print(f"  index:   {INDEX_PATH.relative_to(ROOT)}")
    print(f"  readme:  {README_PATH.relative_to(ROOT)}")
    print(f"  daily:   {DAILY_DIR.relative_to(ROOT)}/")
    print(f"  cats:    {CATEGORIES_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
