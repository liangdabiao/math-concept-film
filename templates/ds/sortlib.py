# -*- coding: utf-8 -*-
"""sortlib —— 排序动画资产库：块状数组 + 交换/比较/标记/覆盖。
配合 assets.py 使用：from assets import *; from sortlib import *
"""
from __future__ import annotations

from manim import *
import numpy as np
from assets import *

LOOSE = "#a8c8b8"      # 未排序块填充
SORTED_FILL = STONE    # 已排序块填充


class SortArr:
    """块状数组：每元素一个圆角块，支持交换/比较/标记/覆盖。"""

    def __init__(self, vals, x_center: float = 0.0, y: float = 0.5,
                 w: float = 0.82, gap: float = 0.14):
        self.vals = [str(v) for v in vals]
        self.w, self.gap, self.y = w, gap, y
        self.x0 = x_center - (len(vals) - 1) * (w + gap) / 2
        self.blocks = [self._make(v, k) for k, v in enumerate(self.vals)]

    def _x(self, i: float) -> float:
        return self.x0 + i * (self.w + self.gap)

    def pos(self, i: float) -> np.ndarray:
        return np.array([self._x(i), self.y, 0.0])

    def _make(self, v, i: int) -> VGroup:
        b = RoundedRectangle(corner_radius=0.08, width=self.w, height=0.66,
                             stroke_color=CHARCOAL, stroke_width=2.0)
        b.set_fill(LOOSE, 1.0)
        t = T(str(v), 24, INK).move_to(b)
        g = VGroup(b, t)
        g.move_to(self.pos(i))
        return g

    def group(self) -> VGroup:
        return VGroup(*self.blocks)

    # ---- 动画原语 ----
    def swap(self, film, i: int, j: int, rt: float = 0.55) -> None:
        a, b = self.blocks[i], self.blocks[j]
        pa, pb = a.get_center(), b.get_center()
        film._p(a.animate.move_to(pb), b.animate.move_to(pa), rt=rt)
        self.blocks[i], self.blocks[j] = b, a

    def cmp_pair(self, film, i: int, j: int, rt: float = 0.4) -> None:
        r1 = SurroundingRectangle(self.blocks[i], color=AMBER, buff=0.03,
                                  stroke_width=3.0)
        r2 = SurroundingRectangle(self.blocks[j], color=AMBER, buff=0.03,
                                  stroke_width=3.0)
        film._p(Create(r1), Create(r2), rt=rt)
        film._p(FadeOut(r1), FadeOut(r2), rt=0.18)

    def flash(self, film, i: int, color: str = AMBER, rt: float = 0.35) -> None:
        r = SurroundingRectangle(self.blocks[i], color=color, buff=0.03,
                                 stroke_width=3.0)
        film._p(Create(r), rt=rt * 0.6)
        film._p(FadeOut(r), rt=rt * 0.4)

    def mark_sorted(self, film, i: int, rt: float = 0.25) -> None:
        film._p(self.blocks[i][0].animate.set_fill(SORTED_FILL, 1.0)
                .set_stroke(color=SORTED_FILL), rt=rt)

    def set_val(self, film, i: int, v, rt: float = 0.3) -> None:
        blk = self.blocks[i]
        old = blk[1]
        nt = T(str(v), 24, INK).move_to(blk)
        self.vals[i] = str(v)
        blk.remove(old)
        blk.add(nt)
        film._p(FadeOut(old), FadeIn(nt), rt=rt)

    def dim_range(self, film, ks, rt: float = 0.4) -> None:
        anims = []
        for k in ks:
            anims.append(self.blocks[k].animate.set_opacity(0.3))
        film._p(*anims, rt=rt)

    def undim_all(self, film, rt: float = 0.4) -> None:
        anims = [b.animate.set_opacity(1.0) for b in self.blocks]
        film._p(*anims, rt=rt)


def ghost_move(film, src_block: VGroup, target: np.ndarray,
               rt: float = 0.6, fade_out: bool = True) -> None:
    """复制一块沿弧线下落到目标处（归并/入堆的"搬运"视觉）。"""
    g = src_block.copy()
    film.add(g)
    anims = [g.animate.move_to(target)]
    if fade_out:
        anims.append(g.animate.set_opacity(0.0))
    film._p(*anims, rt=rt)
