# Agent Rules — Daily Prompt Curation

This repository is a **curated Seedance prompt library**.
Primary model: **Seedance 2.5**. Compatible: **Seedance 2.0**.
Primary language of the repo: **English**.

When the user says things like:

- “add today’s prompts”
- “加几条提示词”
- “collect from this X link”
- “update the repo with these”

…follow this file **exactly**.

---

## 1. Mission

Collect high-engagement, recent, useful **Seedance video prompts** (mostly from X/Twitter), store them as structured JSON, then regenerate docs so the repo stays browsable and daily-updated.

Do **not** invent viral stats. Do **not** fabricate source URLs. Do **not** rewrite prompts so heavily that they no longer match the source (light cleanup for formatting is OK).

---

## 2. Daily workflow (mandatory order)

1. **Intake** — read what the user provided (links, screenshots, pasted prompts, handles, like counts).
2. **Validate** each candidate against [§3 Acceptance](#3-acceptance-criteria).
3. **Assign IDs** using [§4 ID rules](#4-id-and-file-rules).
4. **Write one JSON file per prompt** under `data/prompts/YYYY-MM-DD/`.
5. **Rebuild index** — run `python scripts/generate_readme.py` (updates `data/index.json`, `README.md`, `daily/*.md`, `categories/*.md`, `CHANGELOG.md`).
6. **Report** — tell the user what was added, skipped, and why (in English or Chinese matching the user).

If the generate script cannot run, still write the JSON files correctly and note that docs need regeneration.

---

## 3. Acceptance criteria

### Accept when most of these are true

| Rule | Detail |
|------|--------|
| Model | Seedance **2.5** preferred; **2.0** OK if clearly useful / transferable |
| Prompt body | Full text, copy-paste ready, not a vague one-liner |
| Source | Prefer original X/web URL; if user only pastes text, set `source.platform` to `community` or `other` and put `url` as empty string only if truly unknown — better: ask or mark `notes` |
| Quality | Cinematic structure, multi-shot timing, camera language, or clear commercial use is a plus |
| Language of prompt text | Keep original (en/zh/mixed). Repo UI stays English |
| Safety | No CSAM, no non-consensual deepfake requests, no clear malware/scam content |

### Soft engagement thresholds (not hard blocks)

- Prefer posts with **likes ≥ 50** when ranking.
- If likes are unknown but quality is high and user insists, still accept and omit inflated metrics.
- Newer posts outrank older ones when scores are close.

### Reject or skip when

- Duplicate of an existing `source.url` or near-identical `prompt` hash already in the repo
- Prompt is missing / only a title / only a video with no text
- Pure ads for SaaS with no usable prompt
- User asked to invent a “fake viral” entry

When skipping, list the skip reason in the end-of-turn summary.

---

## 4. ID and file rules

- **ID format:** `YYYYMMDD-NNN`  
  Example: `20260814-001`, `20260814-002`
- **NNN** is the sequence for that calendar day in the repo (UTC+8 or user’s local day if they specify; default to the date the user is curating for).
- **File path:**

```text
data/prompts/YYYY-MM-DD/<id>.json
```

Example: `data/prompts/2026-08-14/20260814-001.json`

- Never reuse an ID.
- Before writing, scan existing files for that day to pick the next NNN.
- Default `model`:
  - `seedance-2.5` if the post says 2.5 / user says 2.5 / unclear but current focus
  - `seedance-2.0` only when the source clearly targets 2.0
  - `seedance-2.x` when version is unknown but still Seedance

---

## 5. JSON field checklist

Every new file **must** include:

```json
{
  "id": "YYYYMMDD-NNN",
  "title": "Short English title",
  "prompt": "full prompt...",
  "model": "seedance-2.5",
  "category": ["cinematic"],
  "language": "en",
  "author": {
    "name": "Display Name",
    "x_handle": "@handle",
    "profile_url": "https://x.com/handle"
  },
  "source": {
    "platform": "x",
    "url": "https://x.com/handle/status/...",
    "posted_at": "2026-08-13T12:00:00Z",
    "likes": 0,
    "reposts": 0,
    "views": 0
  },
  "media": {
    "video_url": "",
    "thumb_url": "",
    "duration_sec": null
  },
  "tags": [],
  "score": 0,
  "collected_at": "2026-08-14T09:00:00Z",
  "featured": false,
  "notes": ""
}
```

### Field guidance

- **title**: English, descriptive, ≤ 160 chars. Not the raw first line of the prompt if that line is messy.
- **prompt**: Preserve creator wording. Fix only broken whitespace/fences. Do not translate unless user asks; if you add an English title only, keep prompt original.
- **category**: 1–3 of: `cinematic`, `ads`, `ugc`, `anime`, `drama`, `vfx`, `product`, `meme`, `other`
- **language**: language of the **prompt text** (`en` / `zh` / `mixed` / `other`)
- **score**: if engagement known, compute roughly:

```text
score = 3*log10(likes+1) + 4*log10(reposts+1) + 1*log10(views+1)
```

Round to 1 decimal. If unknown, use `0` and explain in notes if needed.

- **featured**: `true` only for exceptional quality or user-marked picks.
- **notes**: curator remarks in **English** (e.g. “Strong multi-shot timing; works on 2.5”).

Schema reference: `data/schema.json`.

---

## 6. How the user will talk to you (intake formats)

Accept any of these:

### A) Links only

```text
Add these:
https://x.com/.../status/...
https://x.com/.../status/...
```

Agent should open/fetch what it can, extract prompt + metadata, then add.

### B) Pasted prompt + metadata

```text
Title: ...
Model: 2.5
Author: @foo
Link: https://x.com/...
Likes: 1200
Prompt:
...
```

### C) Batch “today’s picks”

```text
今天加 3 条，都是 2.5
1) ...
2) ...
3) ...
```

### D) Minimal

```text
加一条：<paste prompt>
来源：<url or “unknown”>
```

If critical fields are missing (no prompt body), **ask once** for the missing piece. If only likes/views are missing, proceed with zeros.

---

## 7. Doc generation

After JSON files are written:

```bash
python scripts/generate_readme.py
```

This regenerates:

- `data/index.json`
- `README.md` (English hub)
- `daily/YYYY-MM-DD.md`
- `categories/*.md`
- `CHANGELOG.md` (prepend daily entry)

Do not hand-edit generated sections in `README.md` unless the script is broken; fix the script or the data instead.

---

## 8. Copy and safety rules

- Always credit **author + source URL** when known.
- Educational / archival use; do not claim prompts are owned by this repo.
- If a creator requests removal, delete the JSON and regenerate docs.
- Prefer **linking** videos over committing large binaries.
- Never store API keys or personal cookies in the repo.

---

## 9. End-of-turn report template

After each daily add, reply with:

```markdown
## Added (N)
- `id` — title — model — source

## Skipped (N)
- reason

## Repo status
- Total prompts: X
- Today’s digest: `daily/YYYY-MM-DD.md`
- Regenerated: yes/no
```

---

## 10. What not to do

- Do not dump everything into README by hand.
- Do not create parallel folder schemes.
- Do not switch primary language away from English without user request.
- Do not mass-add low-quality one-line prompts to inflate counts.
- Do not commit unless the user explicitly asks to commit/push.

---

## 11. Quick command cheatsheet for the human

| User intent | What to say |
|-------------|-------------|
| Add one link | `Add this prompt: <url>` |
| Add several | `Daily update: <url1> <url2> …` |
| Paste text | `Add prompt for 2.5:` + body + source |
| Feature one | `Mark <id> as featured` |
| Remove | `Remove prompt <id> / <url>` |
| Rebuild only | `Regenerate README` |
