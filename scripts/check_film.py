# -*- coding: utf-8 -*-
"""check_film.py —— 渲染前静态体检：防错检查 + 吸引力检查（2026-11）。

用法：
    python check_film.py film.py lines.json [captions/aligned.json]

防错检查（历史事故逐一对应，红灯必修）：
  1. lines.json 重复 id          → CAP 键互相覆盖（ds14 S1 重名事故）
  2. film.py 漏写 CAP 字典        → NameError: CAP（ds11/ds14 事故）
  3. CAP 键重复 / CAP 覆盖不全     → 某幕挂错字幕
  4. _p(..., run_time=...)        → FilmClock._p 不收 run_time（Keyword 事故）
  5. MoveAlongPath 沿 DashedLine   → 空路径异常挂死渲染（ds21 事故）
  6. 每幕缺少 self._until(...)    → 音画漂移
  7. 幕函数遗漏 self._t = 0.0     → 时钟累计漂移

吸引力检查（宪法硬指标，红=违反 / 黄=提醒）：
  8. 台词 >36 字                  → 字幕需 3 行，违反 ≤18×2 约束
  9. 钩子幕纯贴片                 → 第一个 _act_ 幕只有 chip 无结构动画（吸引力事故）
  10. 某幕疑似贴片幕              → 该幕 chip ≥2 且结构动画动词为 0（黄）
  11. 全片无 burst( 高潮爆点       → 缺高潮定格载体（黄）
  12. 幕内裸 self.play/self.wait  → 时钟失真（谢幕 wait 除外）（黄）
"""
import re
import sys
import json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# 结构动画动词：对象被创建/写出/变形/移动/重排的可见动作
STRUCT_VERBS = (r'Create|Write|LaggedStart|TracedPath|ShowPassingFlash|Transform|'
                r'ReplacementTransform|TransformMatchingShapes|GrowFrom|FadeIn\([^)]*scale|'
                r'move_camera|punch_in|pull_back|lagged_in|pop_in|traced_move|sweep|'
                r'burst|indicate|write_in|ink_iris|ghost_move|glow_dot|MoveAlongPath|'
                r'swap|cascade|arrow_grow')


def act_bodies(src: str):
    """[(幕名, 幕体)]，幕函数按 def _act_* 切分。"""
    out = []
    parts = re.split(r'(def _act_\w+)', src)
    for i in range(1, len(parts), 2):
        name = parts[i]
        seg = re.search(rf'{re.escape(name)}\(.*?\n(.*?)(?=\n    def |\nclass |\Z)',
                        src, re.S)
        if seg:
            out.append((name, seg.group(1)))
    return out


def main() -> int:
    ok = True
    film_path = sys.argv[1] if len(sys.argv) > 1 else "film.py"
    lines_path = sys.argv[2] if len(sys.argv) > 2 else "lines.json"
    src = Path(film_path).read_text(encoding="utf-8")

    # 1. lines.json 重复 id + 8. 台词过长
    if Path(lines_path).exists():
        data = json.load(open(lines_path, encoding="utf-8"))
        ids = [d["id"] for d in data]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            print(f"[红] lines.json 重复 id：{dup}（CAP 键会互相覆盖）")
            ok = False
        else:
            print("[绿] lines.json id 无重复")
        for d in data:
            if len(d["text"].replace("\n", "")) > 36:
                print(f"[红] 台词 {d['id']} 超 36 字（字幕需 >2 行，违反 ≤18×2 约束）："
                      f"「{d['text'][:20]}…」→ 拆成两条")
                ok = False

    # 2/3. CAP 存在性、键重复、覆盖（内联 CAP 或 cap_block.py 均可）
    cap_src = src
    if 'CAP = {' not in src:
        cap_block = Path(film_path).parent / 'cap_block.py'
        if cap_block.exists():
            cap_src += cap_block.read_text(encoding='utf-8')
    if 'CAP = {' not in cap_src:
        print("[黄] 没有 CAP 字典（数学片手写 caption 可跳过本项）")
        cap_keys_unique = []
    else:
        cap_region = cap_src[cap_src.find("CAP = {"):]
        cap_region = cap_region[:cap_region.find("}")]
        cap_keys = re.findall(r'"([A-Za-z0-9_\-]+)":\s*"', cap_region)
        seen = set()
        dupc = sorted({k for k in cap_keys if k in seen or seen.add(k)})
        cap_keys_unique = sorted(set(cap_keys))
        if dupc:
            print(f"[红] CAP 键重复：{dupc}")
            ok = False
        else:
            print(f"[绿] CAP 字典存在，{len(cap_keys_unique)} 键无重复")
        if Path(lines_path).exists():
            need = {d["id"] for d in json.load(open(lines_path, encoding="utf-8"))}
            missing = sorted(need - set(cap_keys_unique))
            if missing:
                print(f"[红] CAP 缺少键：{missing}（对应台词行会挂错字幕）")
                ok = False
            else:
                print("[绿] CAP 覆盖全部台词 id")

    # 4. _p 携带 run_time 关键字
    bad_rt = re.findall(r'_p\([^)]*run_time\s*=', src)
    if bad_rt:
        print(f"[红] _p(..., run_time=...) × {len(bad_rt)}（应使用 rt=）")
        ok = False
    else:
        print("[绿] 无 run_time 关键字误用")

    # 5. MoveAlongPath + DashedLine
    all_body = "\n".join(b for _, b in act_bodies(src))
    hit_dash = False
    for m in re.finditer(r'MoveAlongPath\([^,]+,\s*(\w+)', all_body):
        var = m.group(1)
        if re.search(rf'{var}\s*=\s*DashedLine', all_body):
            print(f"[红] MoveAlongPath 沿 {var}（DashedLine）→ 空路径挂死，改用 Line")
            ok = False
            hit_dash = True
            break
    if not hit_dash:
        print("[绿] 无 DashedLine 游走")

    acts = act_bodies(src)
    if not acts:
        print("[黄] 未发现 _act_* 幕函数（跳过幕级检查）")

    hook_checked = False
    for name, body in acts:
        # 6/7. 时钟纪律
        if "self._until(" not in body:
            print(f"[红] {name} 缺少 self._until（音画漂移）")
            ok = False
        if "self._t = 0.0" not in body:
            print(f"[红] {name} 开头缺少 self._t = 0.0（时钟漂移）")
            ok = False
        # 12. 裸 play/wait（黄）
        bare = len(re.findall(r'\bself\.play\(|\bself\.wait\(', body))
        if bare:
            print(f"[黄] {name} 有 {bare} 处裸 self.play/self.wait（走 _p/_until，谢幕除外）")
        # 9. 钩子幕纯贴片（第一个幕）
        chips_n = len(re.findall(r'\bchip\(', body))
        struct_n = len(re.findall(STRUCT_VERBS, body))
        if not hook_checked:
            hook_checked = True
            if chips_n >= 1 and struct_n == 0:
                print(f"[红] 钩子幕 {name} 只有 chip 贴片、无结构动画——"
                      f"问题必须'演出来'（吸引力宪法#2）")
                ok = False
            else:
                print(f"[绿] 钩子幕 {name} 含结构动画（吸引力宪法#2）")
        # 10. 疑似贴片幕（黄）
        if chips_n >= 2 and struct_n == 0:
            print(f"[黄] {name} 疑似贴片幕：chip×{chips_n} 结构动画×0（宪法#3：40% 口径）")
    if ok and acts:
        print("[绿] 所有幕时钟纪律完整")

    # 11. 高潮爆点（黄）
    if 'burst(' not in src:
        print("[黄] 全片无 burst( 高潮爆点——宪法#5 要求每片一处高潮定格")
    else:
        print("[绿] 存在高潮爆点 burst")

    print("== check_film:", "通过 ✓ 可以渲染" if ok else "有红灯 ✗ 先修再渲")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
