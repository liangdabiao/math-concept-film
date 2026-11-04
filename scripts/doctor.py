"""math-concept-film 环境体检 —— 缺什么、怎么装，一次说清。

给谁用：首次使用本技能的 agent 或人类。跑一遍，照着修。
    python scripts/doctor.py            # 快速体检（纯本地）
    python scripts/doctor.py --full     # 追加联网实测（真合成一句 TTS）

依赖模型（为什么有的检查标"可选"）：
    * 渲染:  manim 0.20 起用 PyAV 写视频，FFmpeg 编解码库已随 pip 包自带，
             不需要系统安装 ffmpeg.exe。
    * 语音/拼接/混流: 需要 ffmpeg 可执行文件。有系统 ffmpeg 最好；
             没有 pip 装 imageio-ffmpeg 也能顶（本技能脚本自动识别）。
    * LaTeX: 本技能刻意不用 MathTex，永远不需要装 LaTeX。
"""
from __future__ import annotations

import importlib
import platform
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

OK, BAD, WARN = "✓", "✗", "△"


def pip_name(mod: str) -> str:
    return {"cv2": "opencv-python"}.get(mod, mod)


def try_import(mod: str):
    try:
        return importlib.import_module(mod), None
    except Exception as exc:  # noqa: BLE001 - 体检边界
        return None, f"{type(exc).__name__}: {exc}"


def os_install_cmds() -> dict[str, list[str]]:
    system = platform.system()
    if system == "Windows":
        return {
            "ffmpeg": ["winget install --id Gyan.FFmpeg",
                       "  (或 choco install ffmpeg / scoop install ffmpeg)"],
        }
    if system == "Darwin":
        return {"ffmpeg": ["brew install ffmpeg"]}
    return {"ffmpeg": ["sudo apt install ffmpeg     # Debian/Ubuntu",
                       "sudo dnf install ffmpeg     # Fedora"]}


def main() -> int:
    full = "--full" in sys.argv
    problems: list[str] = []
    lines: list[str] = []

    # 1. Python
    version = sys.version_info
    if version >= (3, 10):
        lines.append(f"{OK} Python {version.major}.{version.minor}.{version.micro}")
    else:
        lines.append(f"{BAD} Python {version.major}.{version.minor} —— 需要 ≥ 3.10"
                     "（python.org 下载新版）")
        problems.append("python")

    # 2. manim（渲染引擎，PyAV 自带 FFmpeg 库）
    manim, err = try_import("manim")
    if manim:
        lines.append(f"{OK} manim {getattr(manim, '__version__', '?')}"
                     "（渲染走 PyAV，无需系统 ffmpeg）")
    else:
        lines.append(f"{BAD} manim 未安装 → pip install manim   ({err})")
        problems.append("manim")

    # 3. PyAV（manim 的视频后端，随 manim 一起装，单独确认一次）
    av, err = try_import("av")
    if av:
        lines.append(f"{OK} PyAV {getattr(av, '__version__', '?')}"
                     "（自带 FFmpeg 编解码库）")
    else:
        lines.append(f"{BAD} PyAV 未安装 → pip install av   ({err})")
        problems.append("av")

    # 4. edge-tts（旁白合成，需联网使用）
    edge, err = try_import("edge_tts")
    if edge:
        lines.append(f"{OK} edge-tts 已安装（合成时需联网）")
    else:
        lines.append(f"{BAD} edge-tts 未安装 → pip install edge-tts   ({err})")
        problems.append("edge-tts")

    # 5. ffmpeg 可执行文件：系统 PATH → imageio-ffmpeg 兜底
    has_sys_ff = bool(shutil.which("ffmpeg"))
    has_ffprobe = bool(shutil.which("ffprobe"))
    imageio, _ = try_import("imageio_ffmpeg")
    if has_sys_ff:
        lines.append(f"{OK} 系统 ffmpeg 已在 PATH"
                     + ("" if has_ffprobe else "（无 ffprobe，脚本自动用 ffmpeg 兜底）"))
    elif imageio:
        lines.append(f"{WARN} 无系统 ffmpeg，但 imageio-ffmpeg 可兜底"
                     "（技能脚本自动识别；更稳的长期方案见文末安装命令）")
    else:
        lines.append(f"{BAD} 找不到任何 ffmpeg → pip install imageio-ffmpeg（最快），"
                     "或按文末命令装系统 ffmpeg")
        problems.append("ffmpeg")

    # 6. LaTeX —— 刻意不用，只为打消疑虑
    lines.append(f"{OK} LaTeX：本技能不需要（公式走 Text+Unicode，见 SKILL.md 风格DNA）")

    # 7. --full：真金火炼，合成一句试试
    if full and not problems:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
        import tts_lines  # noqa: PLC0415 - 体检专用延迟导入
        from pathlib import Path  # noqa: PLC0415
        tmp = Path("_doctor_tts_test.mp3")
        try:
            import edge_tts
            edge_tts.Communicate(
                "环境自检，正常。", "zh-CN-YunyangNeural", rate="+15%"
            ).save_sync(str(tmp))
            dur = tts_lines.measure(tmp)
            lines.append(f"{OK} 联网实测：TTS 合成 {dur:.2f}s ✓")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"{BAD} 联网实测失败（检查网络/代理）：{exc}")
            problems.append("network")
        finally:
            tmp.unlink(missing_ok=True)

    print("\n".join(lines))
    if problems:
        print("\n── 修复指引 ──")
        # 一条 pip 命令覆盖所有 pip 可修的项
        pip_map = {"manim": "manim", "av": "av", "edge-tts": "edge-tts",
                   "ffmpeg": "imageio-ffmpeg"}
        pip_pkgs = sorted({pip_map[p] for p in problems if p in pip_map})
        if pip_pkgs:
            print(f"  pip install {' '.join(pip_pkgs)}")
        if "ffmpeg" in problems:
            for cmd in os_install_cmds().get("ffmpeg", []):
                print(f"  {cmd}")
        if "python" in problems:
            print("  从 python.org 安装 Python ≥ 3.10 后重开终端")
        if "network" in problems:
            print("  edge-tts 走微软在线服务；检查网络/代理后重试 --full")
        return 1
    print("\n环境就绪，可以开工。（加 --full 可追加联网实测）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
