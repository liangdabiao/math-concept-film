"""math-concept-film 场景骨架 v2 —— 复制本文件作为新片起点。

使用方法（写新片时）：
    1. 复制本文件到影片工作目录，改类名为 <主题>PascalCase+Film
    2. 先跑 scripts/tts_lines.py 拿到 captions/aligned.json
    3. 把每段台词的 start/end 秒"誊写"进 construct 的注释区
    4. 替换各幕内容。保留契约代码（相机纪律/纸墨舞台/字幕/时钟）

v2 新增（吸引力层，2026-11）：
    * 动效负面清单取代 4 动词白名单 —— Write/LaggedStart/TracedPath/
      ShowPassingFlash/Indicate/rate_functions/updaters 全部放开
    * 节奏对比：快节拍(0.4~0.6s) ↔ 定格蓄力(1.5~2s)，每片至少一处高潮定格
    * 表现力助手（全部自动记账时钟）：write_in / pop_in / lagged_in /
      traced_move / sweep / indicate / burst / punch_in / pull_back
    * 幕间转场：只用快速淡出（_wipe，0.3~0.5s）；全屏吞没式转场（墨盘/
      闪白闪黑）闪眼，已废除，不要发明新转场

硬约束速记（完整版见 references/scene-contract.md）：
    * 只用 ThreeDScene；开场 set_camera_orientation，运镜 move_camera，
      绝不 .animate 相机
    * 本机无 LaTeX：公式一律 Text()+Unicode(x² xⁿ √ ∫ Σ ÷ · ± ≥ ≠)
    * 时钟纪律：所有 play/wait 走 self._p / self._until / 表现力助手，
      任何裸 self.play/self.wait 都会让音画漂移（headline 除外，它自己记账）
    * 无文件 IO、无网络、无 os/subprocess；确需随机必须给固定种子
    * 纸墨 DNA：背景 #f3ecd8，墨色系文字，克制用色（每幕至多两个强调色）
    * 字幕每行 ≤18 字，最多 2 行；台词长就拆成多条 caption 硬切
"""
from __future__ import annotations

from manim import *
import numpy as np

# ====================================================================
# 纸墨调色板（风格 DNA，不可换）
# ====================================================================
PAPER_BG = "#f3ecd8"     # 宣纸暖底
INK      = "#26221c"     # 主文字
CHARCOAL = "#4a463e"     # 次级文字/坐标轴
INDIGO   = "#2c4d7d"     # 强调一：主对象
STONE    = "#3e7a54"     # 强调二：验证/结论
AMBER    = "#cf9433"     # 强调三：当前焦点(慎用，留给关键)
VERM     = "#b23a2e"     # 强调四：误差/警示
CARD     = "#faf5e8"     # 卡片底
CODE_FONT = "Consolas"
CJK_FONT  = "Microsoft YaHei"


def T(text: str, font_size: int = 30, color: str = INK,
      weight: str | None = None, code: bool | None = None) -> Text:
    """按内容路由字体：纯 ASCII 用等宽，含中文用雅黑（防豆腐块）。
    weight 传 None 会崩，必须给 NORMAL。"""
    is_code = all(ord(ch) < 128 for ch in text) if code is None else code
    return Text(text, font=(CODE_FONT if is_code else CJK_FONT),
                font_size=font_size, color=color, weight=weight or "NORMAL")


# ====================================================================
# 舞台 / 字幕 / 大字
# ====================================================================
def paper_stage(scene: ThreeDScene) -> None:
    """开场：宣纸舞台。俯视相机让 ThreeDScene 读作 2D。"""
    scene.camera.background_color = PAPER_BG
    scene.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES, zoom=1.0)


def caption(scene: ThreeDScene, text: str, color: str = INK, font_size: int = 30) -> float:
    """字幕硬切：直接替换，无过渡动画。每行 ≤18 字，最多 2 行（\\n 分行）。
    台词超过 36 字 → 拆成多次 caption 硬切，别挤成段落。"""
    new = Text(text, font=CJK_FONT, font_size=font_size, color=color, line_spacing=0.9)
    new.set(width=min(new.width, 11.5))
    new.to_edge(DOWN, buff=0.42)
    old = getattr(scene, "_film_caption", None)
    if old is not None:
        scene.remove(old)
    scene.add_fixed_in_frame_mobjects(new)
    scene._film_caption = new
    return 0.0


def headline(scene: ThreeDScene, text: str, sub: str | None = None,
             write: bool = False) -> VGroup:
    """全屏大字宣言。write=True 时逐笔写出（纸墨手账感）。返回组对象。
    自记账时钟：write 版 +1.6s（有副标）/+1.1s，普通版 +0.9s。"""
    title = T(text, 56, INK, weight="BOLD")
    title.set(width=min(title.width, 11.0))
    group = VGroup(title)
    if sub:
        subline = T(sub, 26, CHARCOAL)
        subline.set(width=min(subline.width, 9.5))
        subline.next_to(title, DOWN, buff=0.5)
        group.add(subline)
    group.move_to(ORIGIN)
    scene.add_fixed_in_frame_mobjects(group)
    if write:
        scene.play(Write(title), run_time=1.1)
        scene._t += 1.1
        if sub:
            scene.play(FadeIn(subline, shift=UP * 0.15), run_time=0.5)
            scene._t += 0.5
    else:
        scene.play(FadeIn(group, shift=UP * 0.15), run_time=0.9)
        scene._t += 0.9
    return group


# ====================================================================
# 绝对时钟（音画同步的根基）
# ====================================================================
class FilmClock:
    """每幕开头 self._t = 0.0；所有 play/wait 走 _p/_until/表现力助手。
    _p 兼容 run_time= 误用、守卫空路径 MoveAlongPath、自动包装裸列表。"""

    _t: float = 0.0

    def _p(self, *args, rt: float = 1.0, **kw) -> None:
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

    def _fade(self, *targets, rt: float = 0.25) -> None:
        """精确淡出指定对象。"""
        alive = [t for t in targets if t is not None]
        if alive:
            self._p(*[FadeOut(t) for t in alive], rt=rt)

    def _wipe(self, rt: float = 0.5) -> None:
        """换幕：整场淡出（含字幕），耗时计入时钟。图形跨幕存续时禁止用！"""
        ms = list(self.mobjects)
        if ms:
            self._p(*[FadeOut(m) for m in ms], rt=rt)
        self._film_caption = None


# ====================================================================
# 表现力助手（动效负面清单内的安全封装，全部自动记账时钟）
# ====================================================================
def write_in(scene: ThreeDScene, mob: VMobject, rt: float = 1.0) -> None:
    """逐笔写出——纸墨手账的招牌入场，用于公式/标题/关键词。(+rt)"""
    scene.play(Write(mob), run_time=rt)
    scene._t += rt


def pop_in(scene: ThreeDScene, mob: Mobject, rt: float = 0.45) -> None:
    """小弹入场：1.2 倍缩入 + rush_from 减速落地。快节拍专用。( +rt)"""
    scene.play(FadeIn(mob, scale=1.2), run_time=rt, rate_func=rush_from)
    scene._t += rt


def lagged_in(scene: ThreeDScene, *mobs, shift=DOWN * 0.22, rt: float = 1.0,
              lag: float = 0.15, scale: float | None = None) -> None:
    """齿落式依次登场——一组格子/块/项的群体入场。(+rt)"""
    anims = [FadeIn(m, shift=shift, scale=scale) if scale else FadeIn(m, shift=shift)
             for m in mobs]
    scene.play(LaggedStart(*anims, lag_ratio=lag), run_time=rt, rate_func=rush_from)
    scene._t += rt


def traced_move(scene: ThreeDScene, mob: Mobject, anim: Animation, rt: float = 1.0,
                color: str = INDIGO, sw: float = 3.0) -> Mobject:
    """移动时身后拖出墨迹轨迹（指针游走/块搬运的灵魂）。返回轨迹。(+rt)
    用法：trail = traced_move(self, block, block.animate.move_to(target), rt=0.8)"""
    trail = TracedPath(mob.get_center, stroke_color=color, stroke_width=sw,
                       stroke_opacity=0.75)
    scene.add(trail)
    scene.play(anim, run_time=rt)
    scene._t += rt
    return trail


def sweep(scene: ThreeDScene, mob: VMobject, color: str = AMBER,
          rt: float = 1.0, width: float = 8.0) -> None:
    """一段流光沿轮廓扫过——强调"这条线/这个面"。每幕至多一次。(+rt)"""
    flash = mob.copy().set_stroke(color=color, width=width)
    scene.play(ShowPassingFlash(flash, time_width=0.45), run_time=rt)
    scene._t += rt


def indicate(scene: ThreeDScene, mob: Mobject, color: str = AMBER,
             rt: float = 0.6) -> None:
    """小幅度强调：外框闪现一圈再散。比注释轻、比 FadeIn 有力。(+rt)"""
    box = SurroundingRectangle(mob, color=color, buff=0.1, stroke_width=2.5)
    scene.play(Create(box), run_time=rt * 0.6, rate_func=rush_from)
    scene._t += rt * 0.6
    scene.play(FadeOut(box), run_time=rt * 0.4)
    scene._t += rt * 0.4


def burst(scene: ThreeDScene, center, color: str = STONE, rt: float = 0.9,
          rings: int = 3, size: float = 0.3) -> None:
    """高潮爆点：同心圆涟漪扩散消隐。全片至多 1~2 处（留给真高潮）。(+rt)"""
    group = VGroup(*[Circle(radius=size * (i + 1), color=color,
                            stroke_width=max(2.0, 5.0 - 1.4 * i)) for i in range(rings)])
    group.move_to(center.get_center() if isinstance(center, Mobject)
                  else np.array(center, dtype=float))
    scene.play(*[r.animate.scale(2.4).set_stroke(opacity=0) for r in group],
               run_time=rt, rate_func=rush_from)
    scene._t += rt


def punch_in(scene: ThreeDScene, target: Mobject, zoom: float = 2.0,
             rt: float = 0.9) -> None:
    """镜头推近（讲局部）。运镜消耗真实时间，同样记账。(+rt)"""
    scene.move_camera(frame_center=target.get_center(), zoom=zoom, run_time=rt)
    scene._t += rt


def pull_back(scene: ThreeDScene, rt: float = 0.9) -> None:
    """镜头回归全景（讲完局部必回）。(+rt)"""
    scene.move_camera(frame_center=ORIGIN, zoom=1.0, run_time=rt)
    scene._t += rt


# ====================================================================
# 影片本体 —— 把下面两幕换成你的内容
# ====================================================================
class ConceptFilm(ThreeDScene, FilmClock):
    """《示例：多项式吻住曲线》——骨架自带的最小可渲染样片。
    演示词汇表：钩子演示开场 / traced_move / sweep / Write / punch_in /
    burst 高潮定格 / 节奏对比。"""

    def construct(self) -> None:
        paper_stage(self)
        # ── 时间轴誊写区（从 captions/aligned.json 手工抄录，改完台词就更新）
        # 每幕预算 = 该幕各行 duration 之和 + 行间 gap 0.25（末行除外）
        # A1 钩子 预算 6.4s   （A2 起 0.0/6.4）
        # A2 建造 预算 10.6s  （6.4 → 17.0）
        self._act_hook(budget=6.4)      # 钩子：问题必须"演出来"，不许静态标题开场
        self._act_build(budget=10.6)
        self.wait(1.0)  # 谢幕余量（帧量化补偿，勿计入预算）

    # ── 幕一·钩子：前 5 秒必须有动画在进行 ──────────────────────────
    def _act_hook(self, budget: float) -> None:
        self._t = 0.0                                   # 每幕本地时钟，必写
        axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 2, 1],
                    x_length=9, y_length=5,
                    axis_config={"color": CHARCOAL, "stroke_width": 2}).shift(DOWN * 0.3)
        curve = axes.plot(np.sin, color=INDIGO, stroke_width=4)
        caption(self, "一条曲线，凭什么被一个式子吻住？")
        self._p(Create(axes), rt=0.8)                     # 0.8
        self._p(Create(curve), rt=1.2)                    # 1.2 曲线先"活"起来
        probe = Dot(axes.c2p(0.6, np.sin(0.6)), radius=0.09, color=AMBER)
        self._p(FadeIn(probe, scale=2.0), rt=0.35)        # 0.35
        trail = traced_move(self, probe,                # 0.9 光点游走拖墨迹
                            probe.animate.move_to(axes.c2p(1.8, np.sin(1.8))),
                            rt=0.9, color=AMBER)
        sweep(self, curve, color=AMBER, rt=0.8)           # 0.8 流光扫过
        # 大字宣言叠在演示上，Write 逐笔写出（不单独占屏）
        title = T("用一个多项式，吻住一条曲线", 44, INK, weight="BOLD")
        title.set(width=min(title.width, 10.5))
        title.to_edge(UP, buff=0.7)
        self.add_fixed_in_frame_mobjects(title)
        self._p(Write(title), rt=1.0)                     # 1.0
        self._until(5.8)
        self._p(FadeOut(probe), FadeOut(trail), rt=0.4)   # 0.4（空间对象先退）
        self._p(FadeOut(title), rt=0.3)                   # 0.3（fixed 大字单独退）
        self._until(budget)

    # ── 幕二·建造：推近讲局部 + 高潮定格 ─────────────────────────────
    def _act_build(self, budget: float) -> None:
        self._t = 0.0                                   # 每幕本地时钟，必写
        self._fade(*list(self.mobjects), rt=0.3)          # 0.3 收掉钩子残景
        self._film_caption = None
        axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 2, 1],
                    x_length=9, y_length=5,
                    axis_config={"color": CHARCOAL, "stroke_width": 2}).shift(DOWN * 0.3)
        caption(self, "先有一条曲线")
        self._p(Create(axes), rt=0.8)                     # 0.8
        curve = axes.plot(np.sin, color=INDIGO, stroke_width=4)
        label = T("sin x", 30, INDIGO)
        label.next_to(axes.c2p(2.4, np.sin(2.4)), UP, buff=0.3)
        lagged_in(self, curve, label, rt=1.0, lag=0.3)    # 1.0 齿落式登场
        # ── 推近讲局部 ──
        probe = Dot(axes.c2p(0, 0), radius=0.09, color=AMBER)
        caption(self, "在 x=0 附近动手脚")
        self._p(FadeIn(probe, scale=2.0), rt=0.4)         # 0.4
        punch_in(self, probe, zoom=2.2, rt=0.9)           # 0.9 推近
        tangent = Line(axes.c2p(-1.2, -1.2), axes.c2p(1.2, 1.2),
                       color=VERM, stroke_width=3.5)
        self._p(Create(tangent), rt=0.6)                  # 0.6
        self._until(self._t + 0.6)                        # 短定格蓄力
        pull_back(self, rt=0.9)                           # 0.9 回归全景
        # ── 高潮：结论 + 涟漪爆点 + 定格 ──
        concl = T("sin x ≈ x − x³/6 + x⁵/120", 36, STONE, weight="BOLD")
        concl.set(width=min(concl.width, 10.0))
        concl.move_to(UP * 2.55)
        caption(self, "多项式吻住了曲线")
        self._p(Write(concl), rt=1.0)                     # 1.0
        burst(self, concl, color=STONE, rt=0.8)           # 0.8 高潮爆点
        self._until(budget - 0.4)
        self._p(FadeOut(concl), rt=0.4)                   # 0.4
        self._until(budget)
