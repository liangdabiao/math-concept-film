# -*- coding: utf-8 -*-
"""frame_coverage.py —— 版面利用率抽帧检查（吸引力宪法#6）。

用法：
    python frame_coverage.py <video.mp4> [--every 8] [--min 35]

从视频均匀抽帧，逐帧计算"内容包围盒占画幅比例"：
  内容像素 = 与宣纸底色 #f3ecd8 色差超过阈值的像素（含墨迹/色块/字幕）。
  利用率 = 内容包围盒面积 / 全画幅面积。
判定：平均 ≥35% 且无"连续两帧 <20%"= 达标；20~35% 黄；连续 <20% 红（真·小图事故）。
口径说明：bbox 度量下，居中方图构图天然在 28~38%（合格），双栏/宽幅构图在 42%+；
转场边界处 <0.1s 的单帧空拍不可感知，由"连续两帧"判据排除。

依赖：Pillow + numpy（manim 自带）+ imageio-ffmpeg 或系统 ffmpeg（抽帧）。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

PAPER = (0xF3, 0xEC, 0xD8)
THRESH = 26          # 与纸底的 RGB 最大分量差
MIN_RATIO = 35.0


def ffmpeg_exe() -> str:
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration_of(video: str) -> float:
    import re, shutil
    fp = shutil.which("ffprobe")
    if fp:
        out = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", video], capture_output=True, text=True)
        try:
            return float(out.stdout.strip())
        except ValueError:
            pass
    out = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", video],
                         capture_output=True, text=True, errors="replace")
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", out.stderr)
    if not m:
        return 0.0
    h, mi, s, cs = map(int, m.groups())
    return h * 3600 + mi * 60 + s + cs / 100


def coverage_of_frame(png: str) -> float:
    from PIL import Image
    import numpy as np
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.int16)
    diff = np.abs(img - np.array(PAPER, dtype=np.int16)).max(axis=2)
    mask = diff > THRESH
    ys, xs = np.nonzero(mask)
    if len(xs) < 40:          # 近乎空帧
        return 0.0
    h, w = mask.shape
    bw = (xs.max() - xs.min() + 1) / w
    bh = (ys.max() - ys.min() + 1) / h
    return bw * bh * 100.0


def main() -> int:
    args = sys.argv[1:]
    video = args[0] if args else ""
    every = 8.0
    min_ratio = MIN_RATIO
    if "--every" in args:
        every = float(args[args.index("--every") + 1])
    if "--min" in args:
        min_ratio = float(args[args.index("--min") + 1])
    if not video or not Path(video).exists():
        print("usage: python frame_coverage.py <video.mp4> [--every 8] [--min 35]")
        return 1

    dur = duration_of(video)
    if dur <= 0:
        print("[红] 读不到视频时长")
        return 1
    stamps = [t for t in
              [every * (i + 0.5) for i in range(int(dur // every))]
              if t < dur - 0.3][:40]
    with tempfile.TemporaryDirectory() as td:
        ratios = []
        for i, t in enumerate(stamps):
            png = str(Path(td) / f"f{i:03d}.png")
            subprocess.run([ffmpeg_exe(), "-y", "-v", "error",
                            "-ss", f"{t:.2f}", "-i", video,
                            "-frames:v", "1", png], check=True)
            r = coverage_of_frame(png)
            ratios.append((t, r))
    # 红线=持续性空旷：连续两个采样点都 <20%（单帧 <0.1s 的转场空拍不可感知，不算）
    reds = [(t, r) for i, (t, r) in enumerate(ratios)
            if r < 20.0 and i + 1 < len(ratios) and ratios[i + 1][1] < 20.0]
    yellows = [(t, r) for t, r in ratios if 20.0 <= r < min_ratio]
    n = len(ratios) or 1
    avg = sum(r for _, r in ratios) / n
    for t, r in ratios:
        mark = "绿" if r >= min_ratio else ("黄" if r >= 20.0 else "红")
        print(f"  [{mark}] t={t:6.1f}s  版面利用率 {r:5.1f}%")
    print(f"== 平均 {avg:.1f}%  ·  红 {len(reds)} 帧 / 黄 {len(yellows)} 帧 / 共 {len(ratios)} 帧")
    if reds:
        print("[红] 存在 <20% 的空旷帧（内容缩成一小块）——吸引力宪法#6：返工")
        return 1
    if yellows:
        print("[黄] 存在 <35% 的帧——尽量扩构图（大图+左右注释列 > 居中小图）")
    if avg < min_ratio:
        print(f"[黄] 全片平均 {avg:.1f}% < {min_ratio:.0f}%")
    else:
        print(f"[绿] 版面利用率达标（≥{min_ratio:.0f}%）")
    return 0 if not reds else 1


if __name__ == "__main__":
    raise SystemExit(main())
