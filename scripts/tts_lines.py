"""TTS 合成 + 字幕时间轴 —— math-concept-film 的唯一脚本工具。

设计立场：这是一个"哑工具"。只做三件事——
  1. 把 lines.json 里的每一行台词合成 mp3（edge-tts，免费，需联网）
  2. 量每段真实时长（ffprobe；无 ffprobe 时用 ffmpeg 兜底解析）
  3. 拼出整轨 voice.mp3、aligned.json（时间轴真源）、captions.srt

没有重试、没有编排、没有校验逻辑。失败就让异常炸出来，
由运行的 agent 自己判断原因（换音色/查网络/改台词）并决定下一步。

用法：
    python tts_lines.py lines.json                    # 最常用
    python tts_lines.py lines.json --gap 0.35         # 句间留 0.35s 静默
    python tts_lines.py --list-voices                 # 列中文音色

lines.json 格式：
[
  {"id": "A1", "chapter": "钩子",   "text": "……"},
  {"id": "P1", "chapter": "准备",   "text": "……"}
]

输出（相对 --out-root，默认当前目录）：
    audio/<id>.mp3            分段语音
    audio/voice.mp3           整条旁白轨（含句间 gap）
    captions/aligned.json     ★ 场景时间轴的唯一依据：每行 start/end 秒与帧
    captions/captions.srt     标准 SRT（备用）
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:  # Windows 控制台默认 GBK，打印中文会炸；统一转 UTF-8。
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

FPS = 30
DEFAULT_VOICE = "zh-CN-YunyangNeural"      # 云扬：新闻旁白风，适合数学解说
# 备选： zh-CN-XiaoxiaoNeural(晓晓,女声) / zh-CN-YunxiNeural(云希,男声年轻)


def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------------------
# ffmpeg 解析链：系统 PATH → imageio-ffmpeg（pip 包自带二进制）。
# 注意 imageio-ffmpeg 只带 ffmpeg、不带 ffprobe，所以量时长准备了两条实现。
# ---------------------------------------------------------------------------
_FFMPEG: str | None = None
_FFPROBE: str | None = None
_ff_resolved = False


def resolve_ff() -> tuple[str, str | None]:
    global _FFMPEG, _FFPROBE, _ff_resolved
    if _ff_resolved:
        return _FFMPEG, _FFPROBE
    _ff_resolved = True
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            raise RuntimeError(
                "找不到 ffmpeg。两选一：\n"
                "  1) 安装系统 ffmpeg（Windows: winget install ffmpeg | "
                "macOS: brew install ffmpeg | Ubuntu: sudo apt install ffmpeg）\n"
                "  2) pip install imageio-ffmpeg   # 本技能自动使用它自带的 ffmpeg"
            )
    _FFMPEG, _FFPROBE = ffmpeg, ffprobe
    return _FFMPEG, _FFPROBE


def _duration_from_stderr(stderr_text: str) -> float:
    """从 `ffmpeg -i` 的 stderr 抠 'Duration: 00:00:04.03'。"""
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", stderr_text)
    if not match:
        raise RuntimeError(f"无法从 ffmpeg 输出解析时长：{stderr_text[:200]}")
    h, m, s, cs = (int(g) for g in match.groups())
    return h * 3600 + m * 60 + s + cs / 100


def measure(path: Path) -> float:
    ffmpeg, ffprobe = resolve_ff()
    if ffprobe:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15, encoding="utf-8",
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())
    # 兜底：无 ffprobe（imageio-ffmpeg 路径），让 ffmpeg 读一遍文件头
    probe = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
        errors="replace",
    )
    return _duration_from_stderr(probe.stderr)


def make_silence(seconds: float, out_path: Path) -> None:
    ffmpeg, _ = resolve_ff()
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi",
         "-i", f"anullsrc=r=24000:cl=mono", "-t", f"{seconds:.3f}",
         "-c:a", "libmp3lame", "-q:a", "9", str(out_path)],
        check=True, capture_output=True,
    )


def concat_audio(parts: list[Path], out: Path) -> None:
    # ffmpeg 以清单文件所在目录为基准解析条目，必须写绝对路径。
    ffmpeg, _ = resolve_ff()
    listfile = out.parent / f"{out.stem}.list"
    listfile.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in parts),
                        encoding="utf-8")
    result = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:a", "libmp3lame", "-q:a", "4", str(out)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"voice.mp3 拼接失败: {result.stderr[-400:]}")
    listfile.unlink()


def srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def synth_line(text: str, voice: str, rate: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    communicate.save_sync(str(out_path))


def list_zh_voices() -> int:
    voices = asyncio.run(__import__("edge_tts").list_voices())
    print("=== edge-tts 中文音色 ===")
    for v in voices:
        if v["Locale"].startswith("zh-"):
            print(f"  {v['ShortName']:42s} {v['Locale']:10s} {v['Gender']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TTS 合成 + 字幕时间轴")
    parser.add_argument("lines", nargs="?", help="lines.json 路径")
    parser.add_argument("--out-root", default=".", help="输出根目录(默认当前目录)")
    parser.add_argument("--voice", default=None,
                        help=f"edge-tts 音色(默认 {DEFAULT_VOICE})")
    parser.add_argument("--rate", default="+15%",
                        help="语速增量字符串，如 '+15%%' 或 '-5%%'(默认 +15%%)")
    parser.add_argument("--gap", type=float, default=0.25,
                        help="句间静默秒数(默认 0.25，幕转换可写进台词或调大此值)")
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--force", action="store_true",
                        help="已存在的分段也重新合成")
    parser.add_argument("--list-voices", action="store_true")
    args = parser.parse_args()

    if args.list_voices:
        return list_zh_voices()
    if not args.lines:
        parser.error("需要 lines.json 参数")

    lines = json.loads(Path(args.lines).read_text(encoding="utf-8"))
    if not isinstance(lines, list) or not lines:
        print("lines.json 必须是非空数组"); return 1
    for i, line in enumerate(lines):
        missing = [k for k in ("id", "chapter", "text") if not line.get(k)]
        if missing:
            print(f"第{i}行缺字段: {missing}"); return 1

    root = Path(args.out_root)
    seg_dir, cap_dir = root / "audio", root / "captions"
    seg_dir.mkdir(parents=True, exist_ok=True)
    cap_dir.mkdir(parents=True, exist_ok=True)

    cursor = 0.0
    aligned, concat_parts = [], []
    tmp_gap = seg_dir / "_gap.mp3"

    print(f"voice={args.voice or DEFAULT_VOICE}  rate={args.rate}  gap={args.gap}s")
    for line in lines:
        lid, text = line["id"], line["text"]
        digest = hash_text(f"{lid}|{text}")
        seg = seg_dir / f"{lid}_{digest}.mp3"
        if args.force or not seg.exists():
            preview = text[:26].replace("\n", " ")
            print(f"  [{lid}] {preview}…")
            synth_line(text, args.voice or DEFAULT_VOICE, args.rate, seg)
            time.sleep(0.35)          # edge-tts 礼貌间隔，防限流
        duration = measure(seg)

        aligned.append({
            "id": lid,
            "chapter": line["chapter"],
            "text": text,
            "start": round(cursor, 3),
            "end": round(cursor + duration, 3),
            "start_frame": int(round(cursor * args.fps)),
            "end_frame": int(round((cursor + duration) * args.fps)),
            "duration": round(duration, 3),
        })
        concat_parts.append(seg)
        cursor += duration

        if args.gap > 0 and line is not lines[-1]:
            make_silence(args.gap, tmp_gap)
            gap_dur = measure(tmp_gap)
            concat_parts.append(tmp_gap)
            cursor += gap_dur

    voice_mp3 = seg_dir / "voice.mp3"
    concat_audio(concat_parts, voice_mp3)
    total = measure(voice_mp3)

    (cap_dir / "aligned.json").write_text(json.dumps({
        "fps": args.fps,
        "voice": args.voice or DEFAULT_VOICE,
        "rate": args.rate,
        "total_duration": round(total, 3),
        "total_frames": int(round(total * args.fps)),
        "lines": aligned,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    srt_chunks = []
    for idx, entry in enumerate(aligned, 1):
        srt_chunks.append(f"{idx}\n{srt_time(entry['start'])} --> "
                          f"{srt_time(entry['end'])}\n{entry['text']}\n")
    (cap_dir / "captions.srt").write_text("\n".join(srt_chunks), encoding="utf-8")
    if tmp_gap.exists():
        tmp_gap.unlink()

    print(f"\n完成: 总长 {total:.2f}s ({int(round(total * args.fps))} 帧 @{args.fps}fps)")
    print(f"  时间轴 → {cap_dir / 'aligned.json'}   ← 场景动画锚点唯一依据")
    print(f"  整轨   → {voice_mp3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
