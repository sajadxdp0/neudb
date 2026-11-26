# neuDB launch video — archived

This directory preserves a historical 15-second product teaser (`neudb-launch-15s.mp4`, 1920×1080) and its historical thumbnail. Neither was **regenerated for 0.5.0**; they may show earlier branding and a superseded install call-to-action. They are archived demo artifacts, not current installation documentation.

For current setup instructions, use the [source installation guide](../../README.md#install-from-source).

## Watch

Open [`neudb-launch-15s.mp4`](neudb-launch-15s.mp4). The thumbnail is [`neudb-launch-thumb.jpg`](neudb-launch-thumb.jpg).

## Source files

[`promo.html`](promo.html) and [`render.py`](render.py) have been updated to source-first wording and the unified brand assets, but the rendered video remains unchanged. Regeneration is optional maintenance, not part of the 0.5.0 release.

To regenerate deliberately, install Playwright and Chromium plus FFmpeg, then run:

```bash
python -m pip install playwright
playwright install chromium
python docs/launch-video/render.py
```

Outputs:

- `raw.webm` — intermediate capture
- `neudb-launch-15s.mp4` — final H.264 video

## Source storyboard (15 seconds)

| Time | Content |
|------|---------|
| 0–4s | neuDB mark and wordmark |
| 4–8s | “Give your agent inspectable memory.” → “neuDB remembers.” |
| 8–12s | JSON on disk · text and vector search · zero core dependencies |
| 12–15s | “Install from source” + GitHub URL |