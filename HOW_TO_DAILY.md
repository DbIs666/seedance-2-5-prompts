# How to update this repo every day

Primary language: **English**  
Models: **Seedance 2.5** (primary) · **Seedance 2.0** (compatible)

You do **not** need to edit Markdown by hand. Talk to the curator agent (e.g. Grok in this project) and paste sources.

---

## One-line recipes

### Add one X post

```text
Add this prompt: https://x.com/<user>/status/<id>
```

### Add several today

```text
Daily update (Seedance 2.5):
1) https://x.com/.../status/...
2) https://x.com/.../status/...
3) https://x.com/.../status/...
```

### Paste a prompt when there is no clean link

```text
Add prompt for Seedance 2.5
Title: Rainy phone booth scene
Author: @someone
Link: https://x.com/someone/status/...   (or: unknown)
Likes: 800
Reposts: 120
Category: cinematic, drama
Prompt:
<full prompt text here>
```

### Feature / remove / rebuild

```text
Mark 20260814-001 as featured
```

```text
Remove prompt 20260814-001
```

```text
Regenerate README
```

---

## What the agent will do

1. Validate quality (full prompt, attribution, not duplicate)
2. Write `data/prompts/YYYY-MM-DD/YYYYMMDD-NNN.json`
3. Run `python scripts/generate_readme.py`
4. Refresh `README.md`, `daily/…`, `categories/…`, `CHANGELOG.md`

Detailed rules: [`AGENTS.md`](AGENTS.md)

---

## Quality bar (quick)

| Keep | Skip |
|------|------|
| Full copy-paste prompt | Title-only / vibe-only |
| Real source when possible | Invented likes or fake URLs |
| 2.5 preferred, good 2.0 OK | Unrelated models only |
| Clear structure (shots/camera) | Pure product spam |

---

## After the agent finishes

Optional local check:

```bash
python scripts/generate_readme.py
```

Commit when you are ready (agent will not commit unless you ask):

```bash
git add data daily categories README.md CHANGELOG.md data/index.json
git commit -m "chore: add daily Seedance prompts"
```
