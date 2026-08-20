#!/usr/bin/env python3
"""Generate README, daily digests, category pages, index, and CHANGELOG from prompt JSON files."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

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
        # samples / docs only — never index
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


def author_line(p: dict) -> str:
    author = p.get("author") or {}
    name = author.get("name") or "Unknown"
    handle = author.get("x_handle") or ""
    profile = author.get("profile_url") or ""
    if handle and profile:
        return f"{name} ([{handle}]({profile}))"
    if handle:
        return f"{name} ({handle})"
    return name


def engagement_line(p: dict) -> str:
    src = p.get("source") or {}
    parts = []
    if src.get("likes") is not None:
        parts.append(f"❤ {src.get('likes') or 0}")
    if src.get("reposts") is not None:
        parts.append(f"🔁 {src.get('reposts') or 0}")
    if src.get("views") is not None:
        parts.append(f"👁 {src.get('views') or 0}")
    score = p.get("score")
    if score:
        parts.append(f"score {score}")
    return " · ".join(parts) if parts else "—"


def render_card(p: dict, heading_level: int = 3) -> str:
    h = "#" * heading_level
    model = p.get("model") or "seedance-2.x"
    cats = ", ".join(p.get("category") or [])
    tags = ", ".join(p.get("tags") or []) or "—"
    src = p.get("source") or {}
    media = p.get("media") or {}
    source_url = src.get("url") or ""
    source_md = f"[Original post]({source_url})" if source_url else "Source unavailable"
    preview = ""
    if media.get("video_url"):
        preview = f"\n**Preview:** {media['video_url']}\n"
    elif media.get("thumb_url"):
        preview = f"\n**Thumb:** ![]({media['thumb_url']})\n"
    notes = p.get("notes") or ""
    notes_md = f"\n> Note: {notes}\n" if notes else ""
    featured = " ⭐" if p.get("featured") else ""
    prompt = (p.get("prompt") or "").rstrip() + "\n"
    return f"""{h} {p.get('title', p['id'])}{featured}

`{p['id']}` · `{model}` · {cats}

**Prompt:**

```text
{prompt}```
{preview}
| Field | Value |
|-------|-------|
| Author | {author_line(p)} |
| Source | {source_md} |
| Engagement | {engagement_line(p)} |
| Collected | {p.get('collected_at', '—')} |
| Tags | {tags} |
{notes_md}"""


def day_key(p: dict) -> str:
    """Return YYYY-MM-DD for grouping."""
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
            }
        )
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(prompts),
        "by_model": dict(by_model),
        "by_category": dict(by_category),
        "prompts": entries,
    }


def write_daily(prompts: list[dict]) -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list[dict]] = defaultdict(list)
    for p in prompts:
        by_day[day_key(p)].append(p)

    # remove stale generated days? keep all that have data
    for day, items in sorted(by_day.items(), reverse=True):
        if day == "unknown":
            continue
        items_sorted = sorted(items, key=lambda x: x.get("score") or 0, reverse=True)
        cards = "\n---\n\n".join(render_card(p, 3) for p in items_sorted)
        body = f"""# Daily Digest — {day}

> Seedance **2.5** first, **2.0** compatible. Curated from high-engagement community posts (mostly X).

**Added this day:** {len(items_sorted)} prompt(s)

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
            cards = "\n---\n\n".join(render_card(p, 3) for p in items)
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
    featured = featured[:6] or prompts[:3]

    # latest day
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

    recent = prompts[:10]

    def list_links(items: list[dict]) -> str:
        if not items:
            return "_None yet. Add the first prompt via the daily workflow in `AGENTS.md`._\n"
        lines = []
        for p in items:
            model = p.get("model", "")
            score = p.get("score") or 0
            path = p.get("_path", "")
            lines.append(
                f"- **{p.get('title', p['id'])}** — `{p['id']}` · `{model}` · score {score} · [json]({path})"
            )
        return "\n".join(lines) + "\n"

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

    latest_section = (
        f"### {latest_day} — {len(latest_items)} new\n\n{list_links(latest_items)}"
        if latest_day
        else list_links([])
    )

    readme = f"""# Seedance 2.5 Prompts

[![Seedance 2.5](https://img.shields.io/badge/Seedance-2.5_primary-0ea5e9)](#)
[![Seedance 2.0](https://img.shields.io/badge/Seedance-2.0_compatible-38bdf8)](#)
[![Prompts](https://img.shields.io/badge/prompts-{index.get('total', 0)}-f97316)](data/prompts/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Daily-curated video prompts for ByteDance Seedance** — **2.5 first**, **2.0 compatible**.  
> Focus: high-engagement posts from **X (Twitter)** and the wider community. English hub, original prompt languages preserved.

This repo is designed for a simple loop: **you drop links or prompts → the curator agent adds structured JSON → docs regenerate**.

---

## Why this repo

| Goal | How we do it |
|------|----------------|
| Stay current | Daily digests under [`daily/`](daily/) |
| Prefer 2.5 | `model` field marks `seedance-2.5` / `seedance-2.0` / `seedance-2.x` |
| Stay usable | Full copy-paste prompts + source attribution |
| Stay maintainable | One JSON file per prompt; generated README |

**Not** a generic ChatGPT prompt dump. **Not** claiming ownership of community prompts.

---

## Stats

| Metric | Value |
|--------|------:|
| Total prompts | **{index.get('total', 0)}** |
| By model | {model_line} |
| Last index update | {index.get('updated_at', '—')} |

---

## Latest day

{latest_section}

## Featured

{list_links(featured)}

## Recent additions

{list_links(recent)}

---

## Categories

| Category | Tag | Count |
|----------|-----|------:|
{cat_table}

---

## Daily digests

{daily_links}

---

## Repository layout

```text
data/prompts/YYYY-MM-DD/<id>.json   # source of truth
data/schema.json                    # JSON shape
data/index.json                     # generated index
data/sources.json                   # watchlist keywords / accounts
daily/YYYY-MM-DD.md                 # generated daily digest
categories/*.md                     # generated category pages
scripts/generate_readme.py          # rebuild docs
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

Human cheatsheet: **[`HOW_TO_DAILY.md`](HOW_TO_DAILY.md)**  
Rules for the agent: **[`AGENTS.md`](AGENTS.md)**  
Contribution notes: **[`CONTRIBUTING.md`](CONTRIBUTING.md)**

After JSON files change:

```bash
python scripts/generate_readme.py
```

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
  "author": {{ "name": "Creator", "x_handle": "@creator", "profile_url": "https://x.com/creator" }},
  "source": {{
    "platform": "x",
    "url": "https://x.com/creator/status/123",
    "likes": 1000,
    "reposts": 100,
    "views": 50000
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
    # fix double-brace escape used for JSON example in f-string
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
