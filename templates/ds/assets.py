"""math-concept-film 数据结构资产包（原 ds-algo-film，实测可渲染），全部实测可渲染。

用法：拷进影片工作目录，`from assets import *`，Scene 定义为
    class XxxFilm(ThreeDScene, FilmClock):
        def construct(self):
            paper_stage(self)
            self._t = 0.0
            ...

依赖：manim >= 0.19（本机 0.20.1 实测）；无 LaTeX、无文件 IO、无网络。
字体纪律：所有文字一律走 T()，按内容自动路由（纯 ASCII→Consolas 等宽，
含中文→Microsoft YaHei），防豆腐块。
"""
from __future__ import annotations

from manim import *
import numpy as np

# ====================================================================
# 纸墨调色板（风格 DNA，与 math-concept-film 一致）
# ====================================================================
PAPER_BG = "#f3ecd8"     # 宣纸暖底
INK      = "#26221c"     # 主文字
CHARCOAL = "#4a463e"     # 次级文字
INDIGO   = "#2c4d7d"     # 指针 / 引用 / 双向
STONE    = "#3e7a54"     # 链表主体 / 结论 / 正确
AMBER    = "#cf9433"     # 当前焦点 / 遍历光点（慎用）
VERM     = "#b23a2e"     # 删除 / 警示 / 失败
CARD     = "#faf5e8"     # 节点底
GRAY     = "#9a938a"     # 删除灰 / None / 英文小注
BLUE_L   = "#b9d4ec"     # 内存指针格

CODE_FONT = "Consolas"
CJK_FONT  = "Microsoft YaHei"


def T(text: str, font_size: int = 30, color: str = INK,
      weight: str | None = None, code: bool | None = None) -> Text:
    """按内容路由字体：纯 ASCII 用等宽，含中文用雅黑。weight 传 None 会崩，必须给 NORMAL。"""
    is_code = all(ord(ch) < 128 for ch in text) if code is None else code
    return Text(text, font=(CODE_FONT if is_code else CJK_FONT),
                font_size=font_size, color=color, weight=weight or "NORMAL")


# ====================================================================
# 舞台 / 字幕 / 时钟
# ====================================================================
def paper_stage(scene) -> None:
    """俯视相机读作 2D；全片运镜只允许 move_camera。"""
    scene.camera.background_color = PAPER_BG
    scene.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES, zoom=1.0)


def caption(scene, text: str, font_size: int = 30) -> None:
    """字幕硬切：remove 旧 + add 新，零过渡。文本自带 \n 控制换行（每行 ≤26 字）。"""
    new = Text(text, font=CJK_FONT, font_size=font_size, color=INK, line_spacing=0.9)
    new.set(width=min(new.width, 12.2))
    new.to_edge(DOWN, buff=0.32)
    old = getattr(scene, "_film_caption", None)
    if old is not None:
        scene.remove(old)
    scene.add_fixed_in_frame_mobjects(new)
    scene._film_caption = new


def headline(scene, text: str, sub: str | None = None):
    """全屏大字宣言。返回组对象——淡出时用返回值，并记得 self._t += 0.9 补记时钟！"""
    title = T(text, 52, INK, weight="BOLD")
    title.set(width=min(title.width, 11.0))
    group = VGroup(title)
    if sub:
        subline = T(sub, 26, CHARCOAL)
        subline.set(width=min(subline.width, 9.5))
        subline.next_to(title, DOWN, buff=0.45)
        group.add(subline)
    group.move_to(ORIGIN)
    scene.add_fixed_in_frame_mobjects(group)
    scene.play(FadeIn(group, shift=UP * 0.15), run_time=0.9)
    return group


def chip(text: str, x, y=None, sz: int = 26, c: str = INK, cap: float = 4.5) -> VGroup:
    """不透明底文字块（防叠字）。签名与 math-concept-film/preflight.py 静态检查约定一致：
    chip("文本", x, y, 字号, 颜色, 最大半宽) + `c1 = chip(...)` 赋值形式 + FadeIn(c1)。

    兼容数组中心：chip("文本", np.array([1.5, 2.0, 0]), 26, STONE, 4.6)（历史误用转正）。"""
    if isinstance(x, (np.ndarray, list, tuple)):
        cx, cy = float(x[0]), float(x[1])
        sz, c, cap = y, sz, c
    else:
        cx, cy = float(x), float(y)
    tx = T(text, sz, c)
    tx.set(width=min(tx.width, cap))
    bx = SurroundingRectangle(tx, buff=0.14, stroke_color=CHARCOAL, stroke_width=1.6)
    bx.set_fill(PAPER_BG, 1.0)
    return VGroup(bx, tx).move_to(np.array([cx, cy, 0.0]))


class FilmClock:
    """绝对时钟混入：防音画漂移。每幕开头 self._t = 0.0；
    所有 play/wait 必须走 _p/_until，任何裸 self.play 都会让时钟失真。"""

    _t: float = 0.0

    def _p(self, *args, rt: float = 1.0, **kw) -> None:
        # 兼容 run_time= 关键字误用；守卫空路径 MoveAlongPath；自动包装 mobject 列表
        if "run_time" in kw:
            rt = kw["run_time"]
        fixed = []
        for a in args:
            if isinstance(a, list):
                a = VGroup(*a) if a else None
                if a is None:
                    continue
            if isinstance(a, MoveAlongPath) and a.path.has_no_points():
                print("WARN: 跳过空路径 MoveAlongPath")
                continue
            fixed.append(a)
        if fixed:
            self.play(*fixed, run_time=rt)
            self._t += rt

    def _until(self, t: float) -> None:
        if t > self._t + 1e-6:
            self.wait(t - self._t)
            self._t = t

    def _wipe(self, rt: float = 0.5) -> None:
        """换幕：整场淡出（含字幕），耗时计入时钟。"""
        ms = list(self.mobjects)
        if ms:
            self.play(*[FadeOut(m) for m in ms], run_time=rt)
            self._t += rt
        self._film_caption = None


# ====================================================================
# 链式结构节点（链表/树/图的通用单元）
# ====================================================================
class Node:
    """两格节点：左格值 + 右格引用点。位置操作走 .g；箭头锚点用 .dot_out / .left。"""

    def __init__(self, val, name=None, size=1.0, accent=INK):
        w, h = 1.30 * size, 0.90 * size
        box = RoundedRectangle(corner_radius=0.13 * size, width=w, height=h,
                               stroke_color=CHARCOAL, stroke_width=2.5)
        box.set_fill(CARD, 1.0)
        div = Line(np.array([w * 0.17, -h / 2, 0]), np.array([w * 0.17, h / 2, 0]),
                   stroke_color=CHARCOAL, stroke_width=2.0)
        vt = T(str(val), int(34 * size), accent).move_to(np.array([-w * 0.165, 0, 0]))
        dt = Dot(radius=0.085 * size, color=INDIGO).move_to(np.array([w * 0.30, 0, 0]))
        parts = [box, div, vt, dt]
        nm = None
        if name:
            nm = T(name, max(14, int(19 * size)), CHARCOAL, code=True)
            nm.next_to(box, DOWN, buff=0.10 * size)
            parts.append(nm)
        self.g = VGroup(*parts)
        self.box, self.div, self.val_text, self.dot, self.name_text = box, div, vt, dt, nm

    def move_to(self, point):
        self.g.move_to(point)
        return self

    def shift(self, v):
        self.g.shift(v)
        return self

    @property
    def center(self):
        return self.g.get_center()

    @property
    def left(self):
        return self.g.get_left() + RIGHT * 0.02

    @property
    def right(self):
        return self.g.get_right()

    @property
    def top(self):
        return self.g.get_top()

    @property
    def bottom(self):
        return self.g.get_bottom()

    @property
    def dot_out(self):
        return self.dot.get_right()


def ref_arrow(a: Node, b: Node, color: str = CHARCOAL, sw: float = 3.5, tip: float = 0.17):
    """a 的引用点 → b 左缘。插入/删除的"改接"都用它。"""
    return Arrow(a.dot_out, b.left, buff=0.04, stroke_width=sw, color=color, tip_length=tip)


def dash_arrow(a: Node, b: Node, color: str = GRAY, sw: float = 2.2):
    """虚线引用：被替换的旧引用、已删除节点残留的引用。"""
    l = DashedLine(a.dot_out, b.left, dash_length=0.09, stroke_width=sw, color=color)
    l.add_tip(tip_length=0.13, tip_width=0.13)
    return l


def none_label(size=1.0):
    return T("None", int(24 * size), GRAY, code=True)


def glow_dot(color: str = AMBER, r: float = 0.11) -> VGroup:
    """带光晕的巡视点：MoveAlongPath(glow, Line(a.center, b.center)) 逐站移动。"""
    halo = Dot(radius=r * 2.0, color=color).set_fill(color, 0.22).set_stroke(width=0)
    core = Dot(radius=r, color=color)
    return VGroup(halo, core)


def badge(k: int, node: Node, color: str = AMBER):
    """访问序号徽章 ①②③④⑤，挂节点上方。k 从 0 起。"""
    return T("①②③④⑤⑥⑦⑧⑨"[k], 20, color).next_to(node.top, UP, buff=0.1)


# ====================================================================
# 数组条（对比 / 演示通用）
# ====================================================================
def array_row(vals, cell=0.78, y=0.0, x_center=0.0, idx_labels=False, empty_last=0):
    """返回 (cells, texts, idxs) 三个 VGroup。
    注意：idx 标签在 y-cell/2-0.20 处，数组行放下半屏(y<-1.4)时必须 idx_labels=False，
    否则小字淹进字幕带。"""
    n = len(vals) + empty_last
    step = cell + 0.06
    x0 = x_center - (n - 1) * step / 2
    cells, texts, idxs = [], [], []
    for i in range(n):
        c = Rectangle(width=cell, height=cell, stroke_color=CHARCOAL, stroke_width=2.2)
        if i < len(vals):
            c.set_fill(CARD, 1.0)
        else:
            c.set_fill(CARD, 0.0).set_stroke(opacity=0.45)
        c.move_to(np.array([x0 + i * step, y, 0]))
        cells.append(c)
        if i < len(vals):
            texts.append(T(str(vals[i]), int(30 * cell / 0.78), INK).move_to(c))
        if idx_labels:
            idxs.append(T(str(i), 16, GRAY, code=True)
                        .move_to(np.array([x0 + i * step, y - cell / 2 - 0.20, 0])))
    return VGroup(*cells), VGroup(*texts), VGroup(*idxs)


def array_insert_cascade(texts, cells, drop_at: int):
    """数组在 drop_at 位插入的级联右移动画序列（从队尾开始！）。
    前提：cells 必须比 texts 多一格空位（array_row(..., empty_last=1)），否则越界。
    用法：self._p(LaggedStart(*array_insert_cascade(texts, cells, 1), lag_ratio=0.22), rt=1.3)
    之后再把新元素文本落进 cells[drop_at]。"""
    n = len(texts)
    return [texts[k].animate.move_to(cells[k + 1]) for k in range(n - 1, drop_at - 1, -1)]


def array_delete_cascade(texts, cells, at: int):
    """数组删除 at 位元素的级联左移动画序列（at 位先灰化淡出）。"""
    return [texts[k].animate.move_to(cells[k - 1]) for k in range(at + 1, len(texts))]


# ====================================================================
# 内存网格（"为什么需要这个结构"的动机幕）
# ====================================================================
MCELL = 0.62
MORG = np.array([-4.35, -1.75, 0.0])   # 左下格中心（网格占 x -4.9..1.0, y -2.1..1.0）


def gpos(col: float, row: float) -> np.ndarray:
    return MORG + RIGHT * col * MCELL + UP * row * MCELL


def mem_empty_grid(cols=9, rows=5) -> VGroup:
    cells = []
    for rr in range(rows):
        for cc in range(cols):
            c = Rectangle(width=MCELL - 0.05, height=MCELL - 0.05,
                          stroke_color=CHARCOAL, stroke_width=1.2)
            c.set_stroke(opacity=0.5).set_fill("#eee4cc", 0.45)
            c.move_to(gpos(cc, rr))
            cells.append(c)
    return VGroup(*cells)


def mem_pair(col: int, row: int, val: int) -> VGroup:
    """内存中的一对格子：绿格=值，蓝格=引用。返回 [绿格, 值文字, 蓝格, 引用点]。"""
    v = Rectangle(width=MCELL - 0.05, height=MCELL - 0.05,
                  stroke_color=STONE, stroke_width=1.5).set_fill(STONE, 1.0)
    v.move_to(gpos(col, row))
    vt = T(str(val), 19, "#f6efdc").move_to(v)
    p = Rectangle(width=MCELL - 0.05, height=MCELL - 0.05,
                  stroke_color=INDIGO, stroke_width=1.5).set_fill(BLUE_L, 1.0)
    p.move_to(gpos(col + 1, row))
    pd = Dot(radius=0.055, color=INDIGO).move_to(p)
    return VGroup(v, vt, p, pd)


def mem_pair_arrow(pa: VGroup, pb: VGroup) -> Arrow:
    """内存格之间的跳跃引用箭头（灰，跨格）。"""
    return Arrow(pa[2].get_center(), pb[0].get_center(),
                 buff=0.13, stroke_width=2.6, color=CHARCOAL, tip_length=0.15)


def mem_legend(x: float = 2.45, y1: float = 0.75, y2: float = 0.0):
    """图例：绿格=存值，蓝格=存引用。返回 (leg1, leg1t, leg2, leg2d, leg2t)。"""
    leg1 = Rectangle(width=0.42, height=0.42, stroke_color=STONE, stroke_width=1.5)
    leg1.set_fill(STONE, 1.0).move_to(np.array([x, y1, 0]))
    leg1t = T("存储节点值", 22, INK).next_to(leg1, RIGHT, buff=0.25)
    leg2 = Rectangle(width=0.42, height=0.42, stroke_color=INDIGO, stroke_width=1.5)
    leg2.set_fill(BLUE_L, 1.0).move_to(np.array([x, y2, 0]))
    leg2d = Dot(radius=0.06, color=INDIGO).move_to(leg2)
    leg2t = T("存储节点引用", 22, INK).next_to(leg2, RIGHT, buff=0.25)
    return leg1, leg1t, leg2, leg2d, leg2t
