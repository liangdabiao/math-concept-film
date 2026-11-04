# -*- coding: utf-8 -*-
"""render.py —— 带工作目录的渲染运行器（根治 cwd 漂移 / 管道挂死 / 静默后台死亡）。

用法：
    python render.py <项目目录> <SceneName> [-qm]     # 渲染并报告成片时长
    python render.py <项目目录> <SceneName> --mux     # 渲染后自动混流配音

特性：
  - 内部 os.chdir 到项目目录，绝不受外层 shell cwd 漂移影响
  - manim 输出直写 render_log.txt（禁用管道：管道关闭会让 manim 写日志时永久阻塞）
  - 渲染完成后自动 ffprobe 成片时长，并给出与配音时长的对账
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def ffmpeg_exe() -> str:
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffprobe_exe() -> str:
    return ffmpeg_exe().replace("ffmpeg", "ffprobe")


def duration(path: str) -> float:
    import shutil
    fp = shutil.which("ffprobe")
    if fp:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True)
        try:
            return float(out.stdout.strip())
        except ValueError:
            pass
    out = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", path],
                         capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", out.stderr)
    if m:
        h, mi, sec, cs = map(int, m.groups())
        return h * 3600 + mi * 60 + sec + cs / 100
    return -1.0


def main() -> int:
    args = [a for a in sys.argv[1:]]
    project = args[0]
    # 项目根 = tools 的上两级（skills/ds-algo-film/tools → 根），免疫调用方 cwd 漂移
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if not os.path.isabs(project):
        project = os.path.join(ROOT, project)
    project = os.path.abspath(project)
    scene = args[1]
    quality = "-qm" if "-qm" in args else "-ql"
    do_mux = "--mux" in args

    proj = Path(project)
    if not (proj / "film.py").exists():
        print(f"[错误] {proj} 下没有 film.py")
        return 1
    voice = proj / "audio" / "voice.mp3"
    if not voice.exists():
        print("[错误] 缺 audio/voice.mp3 —— 先跑 tts_lines.py（先语音后画面）")
        return 1

    os.chdir(project)
    import shutil
    shutil.rmtree(proj / "media", ignore_errors=True)

    t0 = time.time()
    with open("render_log.txt", "w", encoding="utf-8") as log:
        code = subprocess.run(
            [sys.executable, "-m", "manim", quality, "--disable_caching",
             "film.py", scene],
            stdout=log, stderr=subprocess.STDOUT).returncode
    took = time.time() - t0
    if code != 0:
        tail = Path("render_log.txt").read_text(encoding="utf-8", errors="replace")[-1500:]
        print(f"[红] 渲染失败（{took:.0f}s），render_log.txt 尾部：\n{tail}")
        return 1

    mp4 = proj / "media" / "videos" / "film" / quality.replace("-", "p").replace(
        "ql", "480p15").replace("qm", "720p30") / f"{scene}.mp4"
    if quality == "-ql":
        mp4 = proj / "media" / "videos" / "film" / "480p15" / f"{scene}.mp4"
    else:
        mp4 = proj / "media" / "videos" / "film" / "720p30" / f"{scene}.mp4"
    if not mp4.exists():
        print("[红] 渲染完成但找不到成片")
        return 1

    vd = duration(str(mp4))
    vd_voice = duration(str(voice))
    print(f"[绿] 渲染完成 {took:.0f}s · 视频 {vd:.1f}s · 配音 {vd_voice:.1f}s "
          f"(差 {vd - vd_voice:+.1f}s)")

    if do_mux:
        fin = proj / "final.mp4"
        target = vd_voice + 2.0
        subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-i", str(mp4),
                        "-i", str(voice), "-c:v", "copy", "-c:a", "aac",
                        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{target:.1f}",
                        str(fin)], check=True)
        print(f"[绿] 混流完成 → {fin} ({duration(str(fin)):.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
