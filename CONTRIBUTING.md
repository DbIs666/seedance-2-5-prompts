# Contributing

Thanks for helping curate **Seedance 2.5** (and 2.0-compatible) prompts.

## Preferred path: daily curator agent

This repo is maintained with a daily agent workflow documented in [`AGENTS.md`](AGENTS.md).

Typical human messages:

- `Add this prompt: <X url>`
- `Daily update:` + one or more links / pasted prompts
- `Remove prompt <id>`

## Manual contribution (PR)

1. Create `data/prompts/YYYY-MM-DD/YYYYMMDD-NNN.json` following `data/schema.json`.
2. Run:

```bash
python scripts/generate_readme.py
```

3. Open a PR with:
   - source URL (when available)
   - model version (`seedance-2.5` preferred)
   - short English title

## Quality bar

- Full prompt text (copy-paste ready)
- Attribution (author + link)
- Useful structure (shots, camera, timing, style) beats keyword spam
- No fabricated engagement metrics

## Takedown

Creators can request removal via GitHub Issues. Include the prompt `id` or source URL.
