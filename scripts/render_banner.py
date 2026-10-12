#!/usr/bin/env python3
"""Render the loop using Python 3, Inkscape, FFmpeg and ImageMagick.

Run from any directory: python3 scripts/render_banner.py
The original SVG remains the static, reduced-motion alternative.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
FPS = 20
SECONDS = 8
FRAMES = FPS * SECONDS
EDGE = math.hypot(171, 91)
PERIMETER = EDGE * 4


def frame_svg(source, frame):
    phase = frame / FRAMES
    angle = math.tau * phase
    # Keep the entire typographic composition unchanged.
    prefix = source.split('  <g stroke="url(#accent)"', 1)[0]
    effects = '''
    <defs>
      <filter id="softGlow" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="3"/>
      </filter>
      <linearGradient id="pulse" x1="0" x2="1">
        <stop stop-color="#8CF6CB" stop-opacity="0"/>
        <stop offset=".55" stop-color="#8CF6CB" stop-opacity=".55"/>
        <stop offset="1" stop-color="#8CF6CB" stop-opacity="0"/>
      </linearGradient>
    </defs>
    '''
    # A slow, seamless energy sweep along the existing lower hairline.
    sweep_x = -360 + phase * 1560
    effects += f'<rect x="{sweep_x:.3f}" y="334" width="360" height="2" fill="url(#pulse)"/>'
    # Back to front: independently floating infrastructure, API and interface.
    layers = [(230, 3, 0.9, "#0B171D"),
              (191, 5, 0.45, "#10252D"),
              (152, 7, 0, "#173A41")]
    for index, (cy, amplitude, offset, fill) in enumerate(layers):
        dy = amplitude * math.sin(angle + offset)
        path = f"M792 {cy}L963 {cy-91}L1134 {cy}L963 {cy+91}Z"
        travel = ((phase + index / 3) % 1) * PERIMETER
        dash_offset = -travel
        pulse = 0.24 + 0.08 * math.sin(angle + index)
        effects += f'''<g transform="translate(0 {dy:.3f})" stroke-linejoin="round">
          <path d="{path}" fill="{fill}" stroke="url(#accent)" stroke-width="1.5"/>
          <path d="{path}" stroke="#8CF6CB" stroke-width="7"
            stroke-dasharray="65 {PERIMETER-65:.4f}" stroke-dashoffset="{dash_offset:.4f}"
            opacity="{pulse:.4f}" filter="url(#softGlow)"/>
          <path d="{path}" stroke="#B2FFE4" stroke-width="2"
            stroke-dasharray="52 {PERIMETER-52:.4f}" stroke-dashoffset="{dash_offset:.4f}"
            opacity=".85"/>
        '''
        # Follow the same perimeter as the light trail, with constant speed.
        points = [(792, cy), (963, cy-91), (1134, cy), (963, cy+91)]
        progress = (phase + index / 3) % 1 * 4
        segment = int(progress)
        u = progress - segment
        a, b = points[segment], points[(segment + 1) % 4]
        x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        effects += f'''<circle cx="{x:.3f}" cy="{y:.3f}" r="6" fill="#8CF6CB" opacity=".32" filter="url(#softGlow)"/>
          <circle cx="{x:.3f}" cy="{y:.3f}" r="2.5" fill="#C1FFE8"/>
        '''
        if index == 2:
            code = "M915 142L895 152L915 162M1011 142L1031 152L1011 162M975 128L951 176"
            glow = 0.28 + 0.12 * math.sin(angle)
            effects += f'''<path d="{code}" stroke="#8CF6CB" stroke-width="8" opacity="{glow:.4f}" filter="url(#softGlow)"/>
              <path d="{code}" stroke="#A4FFDD" stroke-width="3" stroke-linecap="round"/>
            '''
        effects += '</g>'
    effects += '<path d="M758 56H731V83M1145 305H1172V278" stroke="#8CF6CB" stroke-opacity=".5"/>'
    return prefix + effects + '</svg>\n'


def run(command):
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))


def complete_png(path):
    """Catch incomplete PNG exports even if the renderer reports success."""
    try:
        data = path.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return False
        cursor = 8
        while cursor + 12 <= len(data):
            length = struct.unpack('>I', data[cursor:cursor+4])[0]
            end = cursor + 8 + length
            if end + 4 > len(data):
                return False
            chunk = data[cursor+4:end]
            if zlib.crc32(chunk) != struct.unpack('>I', data[end:end+4])[0]:
                return False
            if chunk[:4] == b'IEND':
                return True
            cursor = end + 4
    except OSError:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/profile-banner.gif')
    parser.add_argument('--frames-dir', type=Path, help='Keep source frames for inspection')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    for executable in ('inkscape', 'ffmpeg', 'ffprobe', 'convert'):
        if not shutil.which(executable):
            parser.error(f'{executable} must be installed')
    if args.workers < 1:
        parser.error('--workers must be positive')
    source = (ROOT / 'assets/profile-banner.svg').read_text()
    if '  <g stroke="url(#accent)"' not in source:
        parser.error('The static SVG no longer has the expected layer marker')
    with tempfile.TemporaryDirectory(prefix='profile-banner-') as tmp:
        frames_dir = args.frames_dir.resolve() if args.frames_dir else Path(tmp)
        frames_dir.mkdir(parents=True, exist_ok=True)

        def render(index):
            svg = frames_dir / f'frame-{index:03d}.svg'
            png = svg.with_suffix('.png')
            svg.write_text(frame_svg(source, index))
            for attempt in range(3):
                run(['inkscape', str(svg), '--export-type=png',
                     f'--export-filename={png}', '--export-width=1200'])
                if complete_png(png):
                    return
            raise RuntimeError(f'Incomplete PNG export: {png}')

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(render, range(FRAMES)))
        sequence = str(frames_dir / 'frame-%03d.png')
        palette = Path(tmp) / 'palette.png'
        run(['ffmpeg', '-y', '-v', 'error', '-xerror', '-framerate', str(FPS),
             '-t', str(SECONDS), '-i', sequence,
             '-vf', 'palettegen=max_colors=128:stats_mode=full', '-frames:v', '1',
             '-threads', '1', str(palette)])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        intermediate = Path(tmp) / 'unoptimized.gif'
        run(['ffmpeg', '-y', '-v', 'error', '-xerror', '-framerate', str(FPS), '-i', sequence,
             '-i', str(palette), '-lavfi',
             'paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle',
             '-frames:v', str(FRAMES), '-loop', '0', '-gifflags', '+offsetting+transdiff', str(intermediate)])
        run(['convert', str(intermediate), '-coalesce', '-layers', 'Optimize', str(args.output)])
        metadata = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames,duration,width,height', '-of', 'json', str(args.output)]))
        stream = metadata['streams'][0]
        if (int(stream['nb_frames']) != FRAMES or
                abs(float(stream['duration']) - SECONDS) > 0.001 or
                (stream['width'], stream['height']) != (1200, 360)):
            raise RuntimeError(f'Unexpected GIF dimensions, frame count or duration: {stream}')
    print(f'{args.output}: {FRAMES} frames, {FPS} fps, {SECONDS}s, {args.output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
