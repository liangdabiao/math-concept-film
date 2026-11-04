# -*- coding: utf-8 -*-
"""gen_cap.py —— 从 lines.json 自动生成 film.py 的 CAP 字典（自动折行 + 正确转义）。

用法：
    python gen_cap.py lines.json > cap_block.py     # 输出 CAP 块，粘贴进 film.py
    python gen_cap.py lines.json -o cap_block.py    # 或输出到文件（推荐）

规则（2026-11 吸引力宪法版）：
  - 每行 ≤18 字（旧版 26 → 收紧），在最近的标点（。！？；：，、）处折行
  - 最多 2 行；需要 3 行以上 = 台词太长，直接报错让作者拆成多条台词
  - 折行符输出为两字符 \\n（生成的 film.py 中是合法转义）
  - lines.json 里重复的 id 直接报错（防 S1 重名字幕事故）
"""
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BS = chr(92)          # 反斜杠，用于构造 film.py 中的 "\n" 转义
PUNCT = "。！？；：，、"
LIMIT = 18            # 每行字数上限（吸引力宪法：≤18×≤2 行）
MAX_LINES = 2


def wrap(s: str, limit: int = LIMIT) -> list:
    """在标点处折行，每行 ≤ limit 字；无标点则硬切兜底。超 MAX_LINES 行抛错。"""
    if len(s) <= limit:
        return [s]
    lines, buf = [], ""
    for ch in s:
        buf += ch
        if len(buf) >= limit and ch in PUNCT:
            lines.append(buf)
            buf = ""
    if buf:
        # 尾部 ≤6 字且合并后仍 ≤limit 才并入上行，否则单独成行
        if lines and len(buf) <= 6 and len(lines[-1]) + len(buf) <= limit:
            lines[-1] += buf
        else:
            lines.append(buf)
    # 无标点/残余超限 → 硬切兜底，保证任何行 ≤ limit
    out = []
    for ln in lines:
        while len(ln) > limit:
            out.append(ln[:limit])
            ln = ln[limit:]
        if ln:
            out.append(ln)
    if len(out) > MAX_LINES:
        raise ValueError(
            f"台词过长（折 {len(out)} 行，上限 {MAX_LINES}）：「{s}」"
            f"——请在 lines.json 里拆成两条台词（拆点选语义转折处），重新跑 TTS。")
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    out = None
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
    if not args:
        print("usage: python gen_cap.py lines.json [-o cap_block.py]")
        return 1
    data = json.load(open(args[0], encoding="utf-8"))
    ids = [d["id"] for d in data]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        print(f"[错误] lines.json 存在重复 id：{dup} —— 字幕键会互相覆盖，先改 lines.json")
        return 1
    block = "CAP = {\n"
    for d in data:
        # 作者换行（真实 \n）分段 → 段内自动折行 → 统一转义
        try:
            parts = [wrap(p) for p in d["text"].split("\n")]
        except ValueError as e:
            print(f"[错误] 台词 {d['id']}：{e}")
            return 1
        block += '    "%s": "%s",\n' % (d["id"], (BS + "n").join(sum(parts, [])))
    block += "}\n"
    if out:
        open(out, "w", encoding="utf-8").write(block)
        print(f"已写出 {out}（{len(data)} 条，每行≤{LIMIT}字×≤{MAX_LINES}行）")
    else:
        sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
