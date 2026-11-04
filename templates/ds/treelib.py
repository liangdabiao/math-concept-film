"""math-concept-film 树形资产包 —— 圆形节点 / 树边 / 完美二叉树布局 / DFS 游走路径。
配合 assets.py 使用：from assets import *; from treelib import *
"""
from __future__ import annotations

from manim import *
import numpy as np
from assets import T, CARD, CHARCOAL, STONE, INK


class TNode:
    """圆形树节点。"""

    def __init__(self, val, center=np.array([0, 0, 0]), r=0.36, accent=INK,
                 fill=None):
        self.c = Circle(radius=r, stroke_color=CHARCOAL, stroke_width=2.4)
        self.c.set_fill(fill or CARD, 1.0)
        self.t = T(str(val), int(r * 52), accent).move_to(self.c)
        self.g = VGroup(self.c, self.t)
        self.pos = np.array(center, dtype=float)
        self.g.move_to(self.pos)

    def move_to(self, p):
        self.g.move_to(p)
        self.pos = np.array(p, dtype=float)
        return self

    @property
    def center(self):
        return self.g.get_center()


def tedge(p1, p2, r=0.38, color=CHARCOAL, sw=2.4):
    """节点间的树边：两端各缩短半径长度。"""
    d = np.array(p2, dtype=float) - np.array(p1, dtype=float)
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return Line(p1, p2)
    u = d / L
    return Line(np.array(p1, dtype=float) + u * r,
                np.array(p2, dtype=float) - u * r,
                stroke_color=color, stroke_width=sw)


def perfect_layout(vals, cx=0.0, top=2.2, dy=1.25, leaf_gap=2.6):
    """完美二叉树布局：vals 为层序值列表。返回 (nodes, edges)。"""
    n = len(vals)
    levels = 0
    while (1 << levels) < n:
        levels += 1
    levels += 1
    pos = {}
    for l in range(levels):
        cnt = 1 << l
        gap = leaf_gap / cnt
        for p in range(cnt):
            i = (1 << l) - 1 + p
            if i >= n:
                break
            pos[i] = np.array([cx + (p - (cnt - 1) / 2) * gap,
                               top - l * dy, 0.0])
    nodes = [TNode(v, pos[i]) for i, v in enumerate(vals)]
    edges = []
    for i in range(n):
        l, r = 2 * i + 1, 2 * i + 2
        if l < n:
            edges.append(tedge(nodes[i].center, nodes[l].center))
        if r < n:
            edges.append(tedge(nodes[i].center, nodes[r].center))
    return nodes, edges


def tree_pos_map(vals, cx=0.0, top=2.2, dy=1.25, leaf_gap=2.6):
    """只取位置表（层序 0-based 索引 → 坐标），供手工布局参考。"""
    n = len(vals)
    levels = 0
    while (1 << levels) < n:
        levels += 1
    levels += 1
    pos = {}
    for l in range(levels):
        cnt = 1 << l
        gap = leaf_gap / cnt
        for p in range(cnt):
            i = (1 << l) - 1 + p
            if i >= n:
                break
            pos[i] = np.array([cx + (p - (cnt - 1) / 2) * gap,
                               top - l * dy, 0.0])
    return pos
