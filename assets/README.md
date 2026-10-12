# Profile artwork

`profile-banner.svg` is the original, static artwork. `profile-banner.gif` is its animated companion: an eight-second, 160-frame loop at 1200 × 360 pixels and 20 frames per second.

The animation is decorative. All text stays still. The profile README selects the static SVG when the browser reports `prefers-reduced-motion: reduce`, and also provides a visible static-image link. The GIF itself has no embedded pause control.

## Rebuild

Install Python 3, Inkscape, FFmpeg (including `ffprobe`), and ImageMagick 6 (`convert`), then run from the repository root:

```sh
python3 scripts/render_banner.py
```

To retain individual SVG and PNG frames for inspection, use an output directory outside the repository:

```sh
python3 scripts/render_banner.py --frames-dir /tmp/profile-banner-frames
```

The renderer derives the typography and background from the static SVG and builds the moving layers as vector paths. A shared 128-color palette keeps the stationary text stable; ImageMagick optimizes the frame rectangles without changing their appearance. It requires no API keys, network calls, Python packages, or scheduled automation. Rasterization can vary slightly with installed font and tool versions; the published render uses Inkscape 1.2.2, FFmpeg 6.1.1, ImageMagick 6, and Nimbus Sans as the Arial fallback. Exports are checked for incomplete PNGs, and the finished GIF is checked for its dimensions, frame count, and duration.

To return to the original appearance, point the README image at `./assets/profile-banner.svg`. Git history retains both the initial design and subsequent changes.
