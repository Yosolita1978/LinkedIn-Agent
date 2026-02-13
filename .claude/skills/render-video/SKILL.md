---
name: render-video
description: Render the Remotion showcase video for the LinkedIn Outreach Agent
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
argument-hint: "[--codec h264|gif|vp9] [--scale 0.5|1] [--output path]"
---

# Render Video

Renders the Remotion demo video from the `video/` directory.

## Steps

1. Check if `video/node_modules` exists. If not, install dependencies:
   ```bash
   cd video && npm install
   ```

2. Parse any user arguments. Supported flags:
   - `--codec <codec>` — h264 (default), gif, vp9, h265
   - `--scale <number>` — Output scale factor (default: 1)
   - `--output <path>` — Output file path (default: video/out/demo.mp4)

3. Ensure the output directory exists:
   ```bash
   mkdir -p video/out
   ```

4. Render the video:
   ```bash
   cd video && npx remotion render src/index.ts DemoVideo out/demo.mp4
   ```
   Apply any user-specified flags (e.g., `--codec gif --scale 0.5`).

5. Report the output file path and file size when complete.

## Example Usage

- `/render-video` — Render with defaults (H.264, 1080p)
- `/render-video --codec gif --scale 0.5` — Render as half-size GIF
- `/render-video --output out/showcase.mp4` — Custom output name

## Troubleshooting

- If Chrome is not found: `cd video && npx remotion browser ensure`
- If rendering fails with memory errors, add `--concurrency 2`
- Run `cd video && npm run studio` to preview in the browser before rendering
