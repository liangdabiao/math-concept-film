"""渲染前静态预检：不渲染就拦住四类高频返工（约 2 秒跑完）。

用法：python preflight.py film.py [captions/aligned.json]

检查项（红灯=必须修，黄灯=提醒）：
  1. 时长对账   幕预算总和 vs aligned.json 总时长（差 >3.5s 红）
  2. 文字重叠   同幕内两个 chip() 的 y 相差 <0.62 且 x 区间相交（红）
               y 相差 <0.75 且 x 区间相交（黄，可放过）
  3. 越界       chip 中心 y < -2.75 或 > 3.3，|x| > 6.2（红）
  4. 黑名单     豆腐块字符 ⟺⟹ᵏℵ 等（红）
  5. 顺带       检查行间 gap 计入（幕预算 = duration+0.25 是否成立，黄）
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except AttributeError: pass

BAD_CHARS = set("⟺⟹ᵏℵ") | {chr(c) for c in range(0x1D62, 0x1D6A)}

# chip(t,x,y,sz,c,cap,bold) 的调用点（跳过注释行）
CHIP_RE = re.compile(
    r'chip\(\s*"([^"]*)"\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*(?:,\s*\d+\s*,[^,]+,\s*([\d.]+))?')

def check_chars(src: str):
    hits = sorted({c for c in src if c in BAD_CHARS})
    if hits:
        print(f"[红] 黑名单字符: {' '.join(hits)} → 换白名单写法")
    return not hits

def check_bounds(chips, act):
    ok = True
    for text, x, y, _cap in chips:
        if y < -2.75 or y > 3.3:
            print(f"[红] {act} 「{text}」y={y} 越界（字幕区顶约 -3.03）"); ok = False
        if abs(x) > 6.2:
            print(f"[红] {act} 「{text}」x={x} 越出画布"); ok = False
    return ok

def est_half_width(text, cap):
    """估 chip 半宽：中文≈0.42/字@26pt，ASCII 减半；再套 cap 上限。"""
    w = sum(0.21 if ord(ch) < 128 else 0.42 for ch in text)
    w = min(w, cap if cap else 5.0)
    return w / 2 + 0.28  # +SurroundingRectangle buff

def check_overlap(chips, act):
    ok = True; n = len(chips)
    for i in range(n):
        for j in range(i + 1, n):
            t1, x1, y1, c1 = chips[i]; t2, x2, y2, c2 = chips[j]
            if abs(y1 - y2) >= 0.75:
                continue
            hw1, hw2 = est_half_width(t1, c1), est_half_width(t2, c2)
            if abs(x1 - x2) < hw1 + hw2:  # x 区间相交
                if abs(y1 - y2) < 0.62:
                    print(f"[红] {act} 「{t1}」×「{t2}」y={y1}/{y2} 同排相撞"); ok = False
                else:
                    print(f"[黄] {act} 「{t1}」×「{t2}」y={y1}/{y2} 轻微贴边（可放过）")
    return ok

def check_duration(src, aligned_path):
    if not aligned_path or not Path(aligned_path).exists():
        print("[黄] 未给 aligned.json，跳过时长对账"); return True
    d = json.load(open(aligned_path, encoding="utf-8"))
    total = d["total_duration"]   # 已含行间 gap
    lines = d["lines"]
    budgets = re.findall(r'_act_\w+\(\s*([\d.]+)\s*\)', src)
    if not budgets:
        print("[黄] construct 里没找到 _act_ 预算，跳过对账"); return True
    s = sum(float(x) for x in budgets)
    gap = 0.25 * (len(lines) - 1)
    diff = s - total
    verdict = "绿" if abs(diff) <= 0.6 else ("黄" if abs(diff) <= 3.5 else "红")
    print(f"[{verdict}] 幕预算和 {s:.1f}s vs 配音总长 {total:.1f}s（差 {diff:+.1f}s，容忍 ±3s）")
    if gap > 1.0 and -gap - 0.5 < diff < -gap * 0.7:
        print(f"[黄] 差值≈行间gap({gap:.2f}s)：幕预算可能没加每行 +0.25 的静默")
    return verdict != "红"

CHIP_CALL = re.compile(r'(\w+)?\s*=\s*chip\(\s*"([^"]*)"\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*(?:,\s*\d+\s*,[^,]+,\s*([\d.]+))?')

def call_args(src, start):
    """从 src[start] 处的函数名后取平衡括号的完整参数串。"""
    i = src.find('(', start)
    if i < 0: return src[start:start+60]
    depth = 0
    for j in range(i, min(i+160, len(src))):
        if src[j] == '(': depth += 1
        elif src[j] == ')':
            depth -= 1
            if depth == 0: return src[i:j+1]
    return src[i:i+80]

def check_overlap_walk(act_name, body):
    """按源码顺序走一遍：chip 在其 FadeIn 调用处入场，在其 FadeOut 调用处退场。
    只对'同时活跃'的 chip 判重叠（本管线代码严格按时间顺序书写，位置≈时刻）。"""
    ok = True
    events = []
    for m in CHIP_CALL.finditer(body):
        var = m.group(1)
        line_start = body.rfind("\n", 0, m.start()) + 1
        if body[line_start:m.start()].strip().startswith("#"):
            continue
        # 入场时刻 = 首次参数里引用了该变量的 FadeIn（对象常先创建后入画）
        appear = m.start()
        if var:
            for fm in re.finditer(r'FadeIn', body):
                if re.search(r'\b' + re.escape(var) + r'\b(?!=)', call_args(body, fm.start())):
                    appear = fm.start(); break
        events.append((appear, "in", var, m.group(2), float(m.group(3)), float(m.group(4)),
                       float(m.group(5)) if m.group(5) else None))
    for fm in re.finditer(r'FadeOut', body):
        args = call_args(body, fm.start())
        events.append((fm.start(), "out", args, None, None, None, None))
    events.sort(key=lambda e: e[0])
    live = []  # [var, text, x, y, cap]
    for pos, kind, var, text, x, y, cap in events:
        if kind == "in":
            for lv in live:  # lv: [var, text, x, y, cap]
                if abs(y - lv[3]) < 0.45:
                    hw1, hw2 = est_half_width(text, cap), est_half_width(lv[1], lv[4])
                    if abs(x - lv[2]) < hw1 + hw2:
                        print(f"[红] {act_name} 「{text}」×「{lv[1]}」y={y}/{lv[3]} 同排相撞"); ok = False
                elif abs(y - lv[3]) < 0.75:
                    hw1, hw2 = est_half_width(text, cap), est_half_width(lv[1], lv[4])
                    if abs(x - lv[2]) < hw1 + hw2:
                        print(f"[黄] {act_name} 「{text}」×「{lv[1]}」y={y}/{lv[3]} 轻微贴边（可放过）")
            live.append([var, text, x, y, cap])
        else:
            live = [c for c in live if not (c[0] and re.search(r'\b' + re.escape(c[0]) + r'\b(?!=)', var))]
    return ok

def main():
    film = Path(sys.argv[1] if len(sys.argv) > 1 else "film.py")
    aligned = sys.argv[2] if len(sys.argv) > 2 else None
    src = film.read_text(encoding="utf-8")
    all_ok = True
    all_ok &= check_chars(src)
    acts = re.split(r'def (_act_\w+)', src)
    # acts = [前文, 名1, 体1, 名2, 体2, ...]
    for i in range(1, len(acts), 2):
        name, body = acts[i], acts[i + 1]
        live = []
        for m in CHIP_CALL.finditer(body):
            line_start = body.rfind("\n", 0, m.start()) + 1
            if body[line_start:m.start()].strip().startswith("#"):
                continue
            live.append((m.group(2), float(m.group(3)), float(m.group(4)),
                         float(m.group(5)) if m.group(5) else None))
        if not live:
            continue
        all_ok &= check_bounds(live, name)
        all_ok &= check_overlap_walk(name, body)
    all_ok &= check_duration(src, aligned)
    print("== 预检结果:", "全绿 ✓ 可以渲染" if all_ok else "有红灯 ✗ 先修再渲")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
