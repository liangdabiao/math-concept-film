---
name: math-concept-film
description: 把一个数学/数据结构/算法概念变成一部带中文旁白的 Manim 动画短片:纸墨质感舞台、六幕教学叙事、TTS 先行的字幕驱动时间轴、静帧自检循环、吸引力宪法(前5秒法则/结构动画/节奏对比/高潮定格)。当用户想要"把 XX 概念讲清楚/可视化/做成视频",提到数学解释视频、概念动画、微积分/线性代数/概率/物理讲解、数据结构/算法可视化、链表/树/哈希表/排序/动态规划动画、泰勒展开、傅里叶、带配音的数学短片时,必须使用本技能。产出:final.mp4(画面+语音+烧录字幕)。
---

# Math Concept Film（概念短片·统一流水线）

把用户提出的一个概念，变成一部 **2~5 分钟、纸墨质感、带中文旁白**的 Manim 动画短片。
你（运行的 agent）就是整条流水线：策划、编剧、数学审校、摄影、程序员、审片人。
本技能只提供四样东西：**思考框架、风格宪法、吸引力宪法、一堆哑工具**。没有 harness——
流转判断永远由你做。

> 本技能已整合原 ds-algo-film（数据结构领域包：assets/treelib/sortlib、九幕模板、
> 体检工具）与 manim-cjk-font（字体纪律与字形验证法）。做数据结构片时多拷一个
> `templates/ds/` 包、多看一份 `references/template-ds-film.md`，其余流程完全相同。

```
<skill>/
├── SKILL.md                    ← 本文件:操作宪法
├── references/
│   ├── cinematography-grammar.md   镜头动词手册(表现力动词表/节奏对比/转场)
│   ├── scene-contract.md           场景硬约束全清单(写码前过一遍)
│   ├── pitfalls.md                 血泪坑全集(API漂移/排版/字体/DS领域坑)
│   └── template-ds-film.md         数据结构片领域模板(九幕/视觉语言)
├── templates/
│   ├── film_skeleton.py        ← 新片起点:可直接渲染,含表现力助手与绝对时钟
│   └── ds/                     ← 数据结构片资产包(assets.py/treelib.py/sortlib.py)
└── scripts/
    ├── doctor.py               环境体检
    ├── tts_lines.py            台词→语音+时间轴
    ├── preflight.py            渲染前静态预检(重叠/越界/黑名单/时长)
    ├── gen_cap.py              台词→字幕字典(自动折行≤18字,超长报错拆页)
    ├── check_film.py           渲染前体检(字幕挂接/时钟/吸引力检查)
    ├── render.py               渲染运行器(chdir/日志直写/自动混流对账)
    └── frame_coverage.py       版面利用率抽帧检查(内容包围盒≥55%)
```

## 铁律（五条，违反即返工）

0. **技能自包含。** 影片工作区建在用户当前目录里，绝不写进技能文件夹。
1. **先语音后画面。** 台词没合成出 `aligned.json` 之前，不许写一行动画代码。
2. **自检靠眼睛。** 每幕首/中/尾抽静帧亲自看；标准只有一个：你愿意署名发出去。
3. **风格 DNA 不可变。** 宣纸底色、墨色系、镜头纪律照抄不变；**动效按"负面清单"
   放开**（见风格 DNA 表），创意花在叙事与动效上，不花在换皮上。
4. **吸引力底线（2026-11 新增）。** 防错只是及格线。每部片必须通过"吸引力宪法"
   全部硬指标（见下节）， boring = 返工，与画错数字同级。

## 工作流（七步）

```bash
# 第 0 步·开工
FILM=<工作目录>/<slug>          # 例: ./film-build/taylor-series
mkdir -p "$FILM" && cd "$FILM"
cp <skill>/templates/film_skeleton.py film.py
# 数据结构片追加：cp <skill>/templates/ds/{assets,treelib,sortlib}.py .
#                （film.py 里 from assets import *，Scene 继承 ThreeDScene+FilmClock）

# ① 立意（脑内）  六幕框架 + 一句话核心主张 + 情绪弧线；一件事讲透
# ② 写台词 lines.json：口语、有承接、每句≤60字；对照"第一原则"自查
python <skill>/scripts/tts_lines.py lines.json --rate "+12%"
# ③ 读 captions/aligned.json：每行 start/end 秒
#    字幕字典用 gen_cap 生成（数据结构片）；数学片直接把台词誊进 caption()
python <skill>/scripts/gen_cap.py lines.json -o cap_block.py
# ④ 写场景：骨架上改。旁白说到哪，画面演到哪。
#    先对照 scene-contract.md，再跑静态体检：
python <skill>/scripts/preflight.py film.py captions/aligned.json
python <skill>/scripts/check_film.py film.py lines.json captions/aligned.json   # 有 cap_block 时
# ⑤ 渲染（render.py 内部 chdir+清缓存+日志直写，免踩 cwd/管道坑）
python <skill>/scripts/render.py <项目目录> <SceneName> --mux
# ⑥ 静帧自检 + 导演 pass：
#    a. 抽帧每幕首/中/尾+关键动作段，逐帧看：硬伤必修
#    b. frame_coverage.py 查版面利用率
python <skill>/scripts/frame_coverage.py media/videos/film/480p15/<SceneName>.mp4
#    c. 导演 pass：以观众视角过一遍每幕——"想继续看吗"打分，<3 分的幕重设计
#    d. 有问题改 film.py → 只重跑 ⑤（最多两轮，第二轮剩小瑕疵即交付）
# ⑦ 交付：final.mp4 路径、时长、每幕讲了什么
```

## 吸引力宪法（2026-11 确立；每条都对应一次"用户嫌无聊"的教训）

**背景**：AST 审计实证过——历史成片结构动画占比普遍 <8%，多片 0%（纯 chip 贴结论）；
开场即静态大字；节奏恒定如催眠。以下六条是底线，不是建议：

| # | 硬指标 | 判定 |
|---|---|---|
| 1 | **前 5 秒法则** | 开场 5 秒内必须有动画在进行（问题现场演出来）；标题只许叠加在演示上，不许静态标题独占画面 |
| 2 | **问题要"演"不要"写"** | 钩子幕与结论幕禁止纯文字/chip 贴片——问题用动画发生，结论用画面定格 |
| 3 | **结构动画占比 ≥ 40%** | 全片"结构动秒"（对象被创建/移动/变形/重排的秒数，AST 口径）≥ 总时长 40%；每片至少一个"过程动画主角"——贯穿多幕被持续操作的 结构（被拼的图/被填的表/被搬的块/被走的指针） |
| 4 | **节奏对比** | 禁止匀速：快节拍段（0.4~0.6s 连续小步）与定格蓄力段（1.5~2s hold）交替；一幕内至少一次快慢切换 |
| 5 | **高潮定格** | 每片至少一处高潮：最强画面 + burst 涟漪 + 定格 ≥2s，放结论/最大转折处 |
| 6 | **版面利用率** | 全片平均 ≥35%（bbox 口径，frame_coverage.py 实测）且无连续两帧 <20%；居中方图构图天然在 28~38%（合格），双栏/宽幅 42%+；内容缩成中间一小块 = 返工 |

字幕附加：**每行 ≤18 字、最多 2 行**；台词 >36 字拆成多次 caption 硬切。
旁白每 2~4 秒必须有新视觉元素（新登场/移动/变形/变色，任一都算）。

## 第一原则：讲给高中生听（优先级最高）

**台词是"教学"，不是"教材朗读"。判定标准一句话：把台词念给一个高中生听，
他不开视频能不能听懂、想不想继续听？不能，就重写。**

六条硬规则：
1. **每部片从一个具体问题/场景开始**，先抛问题让观众心里想答案，再往下讲。
   禁止用"X 是一种……"开场。
2. **对人说话**：用"你、我们、你看、猜猜"，不用"设、给定、由此可得"。
3. **公式之前必须有直觉故事**；公式出场时说"把刚才的事记下来"，而不是"可得"。
4. **大数字必须翻译**：2^60 → "算到宇宙毁灭"；n! → "百亿亿条路"。
5. **每幕收一句"所以记住…"**；全片结尾是一句能背走的话（≤14 字）。
6. **先错后对**：先演直觉做法踩的坑，再引出正确解法。观众记住的永远是"坑"。

台词记号纪律：`O(1)/O(n)/log n` 不进台词（TTS 读法不可控）——旁白说"常数时间/
线性时间"，O 记号只出现在画面上。数字结论画面与旁白必须逐一对过。

## 六幕思考框架（写台词前的一次内化）

| 幕 | 你要回答的问题 |
|---|---|
| **钩子** | 核心主张的一句话大白话？开场 5 秒演什么？（必须是一个动画演示，不是标题） |
| **地图** | 最小知识树：观众已会什么 → 缺哪块 → 核心主张。主干 3~5 个节点 |
| **课程** | 每幕只教一件事；每个"所以"的承接步骤；在哪里让观众跟着算一步 |
| **数学** | 每个符号的白话注释；**画面上每个数字都验算过——错误数字是最大事故** |
| **镜头** | 每幕的视觉主意与镜头动词（见 cinematography-grammar.md 动词表） |
| **装配** | 幕间转场（ink_iris/推拉）；哪些元素跨幕存活；高潮定格放哪一幕 |

## 风格 DNA（配色与质感不可变；动效按负面清单放开）

| 项 | 值 |
|---|---|
| 引擎 | Manim CE ≥0.19，ThreeDScene 俯视舞台模式（phi=0 读作 2D） |
| 画布 | 16:9；交付默认 -ql(480p15)，用户要高清才 -qm |
| 底色 | 宣纸 `#f3ecd8` |
| 墨色 | 主文字 `#26221c`，次级 `#4a463e`，坐标轴 `#4a463e` |
| 强调 | 黛蓝 `#2c4d7d`(主对象) · 石绿 `#3e7a54`(验证/结论) · 琥珀 `#cf9433`(焦点,慎用) · 朱红 `#b23a2e`(误差/警示) |
| 公式 | Text()+Unicode（x² xⁿ √ ∫ Σ ± ≥ ≠ ÷ ·）；禁 MathTex（无 LaTeX） |
| 字体 | 一律走骨架/资产的 `T()`：纯 ASCII→Consolas，含中文→Microsoft YaHei（防豆腐块） |
| 相机 | 开场 `set_camera_orientation`；运镜只许 `move_camera`（punch_in/pull_back 助手）；禁止 `.animate` 相机 |
| 字幕 | 底部字幕条硬切（caption()）；每行 ≤18 字 ×2 行 |
| 配音 | edge-tts `zh-CN-YunyangNeural` +12%（默认）；换声 `--voice` |
| **动效负面清单** | **禁**：大幅旋转飞入（>90° 转圈进）、剧烈弹跳（多次 overshoot 晃动）、无意义晃动、五色同场、相机全程乱动、**全屏吞没式转场（墨盘/闪白闪黑——闪眼，2026-11 用户反馈废除）**。<br>**放**：Write 逐笔写、LaggedStart 齿落、TracedPath 墨迹拖尾、ShowPassingFlash 流光、Indicate/Circumscribe 强调、squash 小弹(scale 1.2 缩入)、rate_functions 节奏对比(rush_from/rush_into/lingering)、updaters 跟随、move_camera 推拉。克制的是**色彩**，不是**动作** |
| 节奏 | 负面清单外的入场 0.4~1.2s；快节拍 0.4~0.6s；定格蓄力 1.5~2s；幕末 0.5s 缓冲；换幕一律快速淡出（_wipe 0.3~0.5s），禁止转场动效 |
| 禁项 | 无文件 IO、无网络、随机必须给种子、单一 Scene 类、无 LaTeX |

## 放行标准（交付前逐条打勾）

**防错组**（preflight/check_film 全绿；抽帧无大面积遮挡/画错/重叠/越界；
final 时长 = 配音 +2s 左右；画面数字全验算；字幕挂接正确；相机零 `.animate`）

**吸引力组**（任何一条不过 = 返工，与画错同级）：
- [ ] 前 5 秒有动画在进行（非静态标题）
- [ ] 钩子幕与结论幕不是纯文字/chip
- [ ] 结构动画占比 ≥40%，全片有"过程动画主角"
- [ ] 全片有快慢节奏对比，有高潮定格 ≥2s
- [ ] frame_coverage 版面利用率：平均 ≥35%，无连续 <20% 空旷帧
- [ ] 字幕每行 ≤18 字 ×≤2 行
- [ ] 导演 pass：每幕"想继续看吗"≥3 分

## 环境安装（首次使用）

```bash
python <skill>/scripts/doctor.py          # 体检：缺什么、怎么装
python <skill>/scripts/doctor.py --full   # 追加联网实测 TTS
pip install -r <skill>/requirements.txt   # manim + edge-tts + imageio-ffmpeg
```

- 渲染：manim 0.20+ 自带编解码，不需要系统 ffmpeg。
- 语音/混流：有系统 ffmpeg 用系统的；没有则 imageio-ffmpeg 兜底。
- LaTeX：永远不需要。中文字体：默认雅黑路径已由 `T()` 固化，不会豆腐块。

更多坑交付前扫一遍 `references/pitfalls.md`（两分钟）。数据结构片另读
`references/template-ds-film.md`。
