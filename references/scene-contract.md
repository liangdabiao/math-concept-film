# 场景硬约束清单（写完 film.py 后逐条自查）

来源：数十次真实运行磨出来的契约 + 静态验证器规则 + 2026-11 吸引力复盘。
这些不是建议，是放行条件。

## 结构

- [ ] 恰好**一个** Scene 子类，继承 `ThreeDScene(+FilmClock)`，类名 PascalCase（建议以 Film 结尾）
- [ ] 零仓库依赖、零网络、零文件 IO——不 import os/subprocess/socket/urllib/requests，不 open()
- [ ] 确需随机，必须固定种子：`np.random.default_rng(7)`
- [ ] 模块级常量组织调色板与字号，不在函数里散落魔法数字

## 时钟（音画同步的根基）

- [ ] 每幕开头 `self._t = 0.0`（幕内本地时间）
- [ ] 所有 play/wait 走 `self._p` / `self._until` / 表现力助手（它们自动记账）
- [ ] 任何裸 `self.play` / `self.wait`（末尾谢幕 wait 除外）都算时钟失真
- [ ] 幕末 `self._until(budget)`，budget = aligned.json 行时长 + 行间 gap 0.25

## 相机

- [ ] 开场 `set_camera_orientation(phi=0*DEGREES, theta=-90*DEGREES, zoom=1.0)`
- [ ] 全片运镜只出现在 `move_camera(...)`（或 punch_in/pull_back 助手）
- [ ] 从未出现 `self.camera` 被 animate / play / 赋值
- [ ] 推近之后必有回归：punch_in 与 pull_back 成对（观众不能被丢在局部）

## 视觉

- [ ] 背景 `#f3ecd8` 宣纸底；主文字墨色 `#26221c`
- [ ] 每幕至多两个强调色；琥珀只给"当前焦点"
- [ ] 公式全部 Text()+Unicode（无 MathTex，见 pitfalls#3）
- [ ] 文字一律走 `T()`（纯 ASCII→Consolas，含中文→雅黑，防豆腐块）
- [ ] 字幕走骨架 caption()（自动替换、底部固定帧层、每行≤18字×≤2行）
- [ ] 文字入场前先想宽度：`text.set(width=min(text.width, 11.0))` 防溢出
- [ ] 文字块背景必须不透明（`set_fill(PAPER_BG, opacity=1.0)`），防叠字穿透

## 动效（负面清单制——2026-11 起）

**禁止**：大幅旋转飞入（>90°）、剧烈弹跳（多次 overshoot）、无意义晃动。
**其余全部放开**，且优先用骨架助手：write_in / pop_in / lagged_in / traced_move /
sweep / indicate / burst / ink_iris / punch_in / pull_back。

- [ ] 每片有"过程动画主角"：一个贯穿多幕被持续操作的 结构（被拼的图/被填的表/被搬的块）
- [ ] 每幕有快慢对比（0.4~0.6s 快节拍段 ↔ 1.5~2s 定格蓄力），禁匀速 FadeIn 贴片
- [ ] 每片 ≥1 处高潮定格（burst + hold ≥2s）
- [ ] 冲突/失败/回退必须可视化（红 X、攻击线、块飞走），成功用石绿固化
- [ ] TracedPath 移动结束时轨迹要 FadeOut（残迹会跨幕穿帮）

## 吸引力

- [ ] 前 5 秒有动画在进行；标题叠加在演示上
- [ ] 钩子幕与结论幕不是纯文字/chip——问题要"演"，结论要"定"
- [ ] 结构动画占比 ≥40%（对象被创建/移动/变形/重排的秒数 / 总时长）
- [ ] 每 2~4 秒有新视觉元素（新登场/移动/变形/变色任一）
- [ ] 版面利用率：全片平均 ≥35%（bbox 口径，frame_coverage.py），无连续两帧 <20%；内容"占满"而非"居中漂"

## 节奏

- [ ] construct 顶部有"时间轴誊写区"注释，逐行抄自 captions/aligned.json
- [ ] 幕末 0.5s 不上新元素
- [ ] 巡讲每站 1.4s 以上
- [ ] 收尾有定格（结论画面停 ≥2s）再淡出

## 数学

- [ ] 画面上每个数字、每个等式都人工验算过
- [ ] 变量首次出现必有定义（文字或标签）
- [ ] 台词、字幕、画面三者讲的是同一个词
- [ ] 几何图形必须"点名"：每个顶点圆点+字母标签随线段同时入场，辅助点同样点名
- [ ] 几何证明画在图上（同色刻度对/同色角弧），不许用文字 chip 陈述步骤；
      全片同屏叙述文字 ≤2 行
