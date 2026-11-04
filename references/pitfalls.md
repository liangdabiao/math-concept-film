# 血泪坑全集（v2 整合版）

每一坑都真实付过学费。渲染前扫一遍，两分钟。
2026-11 整合：清除重复段落，合并原 ds-algo-film 的 28 条领域坑与 manim-cjk-font
的字体纪律。

## 一、Manim CE 0.20 API 漂移（本机实测）

### 1. `FRAME_WIDTH` / `FRAME_HEIGHT` 已移除
用 `from manim import config` → `config.frame_width`。

### 2. 构造函数里裸 `opacity=` 不存在
`Dot(..., opacity=0.5)` ✗ → `fill_opacity=` / `stroke_opacity=` ✓。
`.set_opacity()` 方法仍在，构造参数才是坑。

### 3. MathTex/Tex/DecimalNumber 一律禁用（无 LaTeX）
报错特征：FileNotFoundError WinError 2。Unicode 公式纪律：
- 上下标：`x² xⁿ x⁵/120`；希腊字母直接 Unicode：`θ φ Σ π ε δ`
- 分式：两行 Text + 中间 Line 做分数线；分段函数：`⎧⎨⎩` 字符
- 数字显示：`Text(f"{value:.2f}")` 自己格式化
- `Brace.get_text()` 返回 Tex → 改 `brace.put_at_tip(T(...))`；
  `NumberLine(include_numbers=True)` → 手画刻度+Text 标签

### 4. 渲染崩溃留 partial_movie_files
别用 `rglob("*.mp4")` 找成品，只认 `media/videos/film/480p15/<Scene>.mp4`。
出片前 `rm -rf media` 更干净（render.py 已自动做）。

### 5. 相机纪律
开场 `set_camera_orientation(...)`；运镜只 `move_camera`；绝不 `self.camera`
被 animate/play/赋值；`begin_ambient_camera_rotation` 后必须 `stop_...`。

### 5b. 不连续函数必须 `use_smoothing=False`
方波/阶梯用 `Axes.plot` 默认平滑会在跳变处产生假振铃。

### 5c. `.animate.set_opacity()` 会顺手打开填充
曲线变淡用 `.animate.set_stroke(opacity=0.28)`，否则闭合路径被糊成一片。

### 5d. `Axes` 不认 `ticks` kwarg（TypeError）

### 5e. 动效放开后的新坑（2026-11）
- `Write` 用在长段中文上极慢且糊——只用于标题/短公式/关键词。
- `TracedPath` 轨迹不会自己消失：移动结束记得 FadeOut，否则残迹跨幕穿帮。
- fixed-in-frame 大字别和空间对象塞进同一个 VGroup 做 FadeOut（标志位会丢）——分开退场。
- `LaggedStart` 的总时长 = rt（不是各动画之和）：rt 要覆盖最长子动画 + lag 展开量。

## 二、Windows / 本机特性

### 6. 控制台编码：print 中文前 `sys.stdout.reconfigure(encoding="utf-8")`（脚本已内置）
### 7. ffmpeg：PATH 有就用系统的；没有则 imageio-ffmpeg 兜底。concat 清单写绝对路径
### 8. 渲染日志禁用管道：`python -m manim ... | head` 会在异常时永久阻塞。
     一律 `> render_log.txt 2>&1`（或直接用 scripts/render.py）
### 9. shell cwd 会漂移：跨调用工作目录不可信。用 scripts/render.py（内部 chdir），
     或每条命令显式 `cd <绝对路径> && pwd && ...`
### 10. SVG ParseError: no element found = texts/SVG 缓存损坏，`rm -rf media` 重渲

## 三、工作流坑

### 11. 时长必须来自 aligned.json
"先做画面再估配音" = 音画必然错位。顺序：lines.json → tts → aligned.json → 写码。

### 12. 幕内计时只用绝对时钟（FilmClock），禁手算 spent
手算低估 + `_tail` 补差 = 每幕超时数秒、成片比配音长 20s 级事故。
规则：每幕开头 `self._t = 0.0`；一切 play/wait 走 `_p`/`_until`；幕末
`self._until(budget)`。帧量化使成片略短，construct 末尾留 `self.wait(1.0)` 冗余。

### 13. TTS 行间静默必须计入幕预算
tts_lines.py 行间 gap 0.25s 不在任何单行 duration 里。幕预算 = 行 duration + gap
（末行除外），否则画面渐进提前、片尾整整漂一个 gap × N。

### 14. 成片放行前必须音画对账
`ffprobe -show_entries format=duration` 成片与 audio/voice.mp3 各一次。
成片 < 配音 = 最后一句压冻结帧；超出 2s+ = 节拍超预算。混流 `-t 配音+2` 裁尾。

### 15. lines.json 禁止重复 id
两个 S1 = CAP 键互相覆盖、字幕错挂整幕。gen_cap.py / check_film.py 都会报错。

### 16. gen_cap.py 必须带 `-o cap_block.py`
不带 -o 只打印 stdout，文件不更新（用过期字幕渲完才发现的事故）。

### 17. 改完必删 media 重渲；成品只认 `media/videos/film/480p15/<Scene>.mp4`
### 18. 渲染疑似卡死先查两件事
`tasklist | grep -i python` 进程活着吗？partial_movie_files 数量涨吗？
死了 = 静默被杀，前台重跑；活着不涨 = 查 render_log.txt 的 Exception
（多半是空路径/零时长动画）。

## 四、排版与文字

### 19. 字幕切换一律硬切（remove 旧 + add 新，零过渡）
交叉淡化叠字、串行淡入残影，都试过全翻车。字幕是信息层，别给它加戏。

### 20. 文字块必须不透明背景
chip/bubble/caption 容器 `set_fill(PAPER_BG, opacity=1.0)`，否则位置重叠时文字穿透混叠。

### 21. 同一水平线多块文字重叠（用户两次点名返工）
- 同排多块 x 区间必须不交。估宽：字符数 × 0.42 × (字号/30) + 0.4（ASCII 减半）
- 竖排行距 ≥ 0.75；正文最低 y = -2.85（字幕区顶约 -3.03）
- 跨幕右列更替：旧对象精确 FadeOut（0.5s 计入时钟），禁止"不清场直接叠新字"
- 含图形跨幕存续的幕**禁止整场 clear/wipe**——会把主图清没

### 22. 同位注释条禁止交叉淡化
`FadeOut(旧)+FadeIn(新)` 放同一个 play 且同位置 = 双重曝光叠印。拆两个 play。

### 23. 推理步骤生命周期：新步骤出现前旧的必须淡出
左侧固定核心图形 → 右侧推理区，步骤**替换**不堆叠。45 秒幕 5 个节拍 = 10s 空白；
目标密度：每 2~4 秒一个新节拍。

### 24. 几何图形必须"点名"（用户怒斥返工）
旁白说 ∠BAC、BD、点 P，画面就必须有对应字母和点。顶点：圆点(≥0.075)+斜体字母
标签(≥28)随线段同时入场；辅助点（垂足/中点/交点）同样点名；角配弧+度数、等边配刻度。
写完一幕裁剪放大自检：确认每个字母真渲染出来了（构造了但没 add 是实际事故）。

### 25. 几何证明的视觉语言（文字陈述式证明禁止）
证明画在图上：全等=对应边同色刻度对；角等=同色弧；拼角=顶点分弧（子角异色、
和角同色粗弧）；结论文字紧邻所指图形；同屏叙述文字 ≤2 行。

### 26. 变量遮蔽陷阱
幕函数参数 `b`（预算 float）被循环里 `b = RoundedRectangle(...)` 覆盖 →
`_until(b)` TypeError。循环变量禁用参数名，用 blk/cell/bar。

## 五、字符豆腐块与字体纪律

默认字体 + Pango 回退不可靠。**根治方案：一切文字走 `T()`**（纯 ASCII→Consolas
等宽，含中文→Microsoft YaHei），manim 传 `font=None` 会崩，必须永远给真实字体名。

实测豆腐块（默认字体下）：`⟺ ⟹ ᵏ ℵ` 及一切音标扩展/下标字母（U+1D62–1D6A）。
长双箭头用 `⇔ ⇒`；上标只用 `² ³ ¹ ⁿ ⁴⁵⁶⁷⁸⁹⁰`；`ℝ ℚ ℤ ℂ ℕ ⊢ ⋯ ✓ ✗ ①②③④⑤ ₀₁₂
° ± × ÷ ≡ ≈ ≤ ≥ ≠ → ↔ ∈ ∉ ∅ ∞ ∠ ≅ ⊥ △ √ ∫ Σ ∏ α β γ δ ε θ λ μ π ρ σ φ ω χ Δ`
实测可渲染。**新字符拿不准 → 3 行测试场景渲一帧看一眼再上正片。**

出片前扫描：
```bash
python - <<'PY'
import glob
bad = set("⟺⟹ᵏℵʷʰᵈᵗ") | {chr(c) for c in range(0x1D62, 0x1D6A)}
for f in glob.glob("*/film.py") + ["film.py"]:
    try: s = open(f, encoding="utf-8").read()
    except OSError: continue
    hit = sorted({c for c in s if c in bad})
    if hit: print(f, "命中黑名单:", hit)
PY
```

看不到画面时的字形验证（像素度量，来自原 manim-cjk-font）：
- **空心度** = 1 − 腐蚀后墨迹/腐蚀前墨迹（3×3 全 1 结构元）。豆腐块笔画极细，
  腐蚀后清零；真字形留存多。参考值（30 号字 480p）：雅黑真字形 ≈0.921，豆腐块 ≈0.983。
- 绝对值随字号漂移，最终结论用 **A/B 自校准**：同串渲染两遍（旧字体 vs 新字体），
  墨迹增幅 ≥1.30 且空心度下降 = 修复生效。纯符号串（½ ² × √ α）前后几乎无变化属正常。
- 改字体后文字宽度会变：必跑 frame 抽帧检查溢出/裁切（右余量 <2px 即已裁）。

## 六、数据结构片领域坑（原 ds-algo-film 28 条，全部实测）

用 `templates/ds/assets.py` 时多数已被守卫兜底，但写码时仍须知道：

1. 辅助函数内的 play 必须补记时钟（`self._t += rt`）——headline 一样
2. 数组级联搬移**从队尾开始**：`for k in (n-1,…,1): texts[k]→cells[k+1]`，
   从队首开始会把元素两两叠进同一格
3. ArcBetweenPoints 正角=逆时针：右→左的弦要向下鼓用**负角**（-1.6 弧深≈弦长×0.22）；
   没把握先渲 1 帧再看
4. 数组下标小字别进字幕带（字幕顶 y≈-2.32）：去掉 idx 标签或把行抬到 y≥-1.6
5. zoom 后标签重算屏位置=(世界坐标−相机中心)×zoom；标签放被放大单元上方空白带
6. 上一段落的 chip/标签在下段落开场精确 FadeOut，否则与新图例相撞
7. 表格高亮按 (row,col) 索引：构建时存 `cell_rc[(r,c)]`，扁平下标会圈到行标题
8. 多行结构布局：行距≥1.7；行底≥-1.9；三行 ys 参考 `[2.15, 0.4, -1.35]`
9. 成片比配音长 2~4s 是帧量化，混流 `-t 配音+2` 裁掉，不回头改节拍
10. 别对 chip 的子对象做 FadeOut（盒子会把同组文字带没）；高亮一律 SurroundingRectangle
    外框叠加，用完 FadeOut 外框
11. 占位物与真值分开放：数组格里灰色占位和后续落入的真值不能混在同一 VGroup
    做搬移/替换——真值单独建 list 管理
12. 先摆好容器再写文字：`move_to(container)` 之后 `text.move_to(container)`，
    顺序反了文字留在组中心被遮
13. `chip()` 只收数值坐标：`chip("✓", cell.get_center()+UP)` 会把数组塞进 x 参数
    导致串位（assets.chip 已兼容三维数组中心，但动态偏移仍要先算好）
14. MoveAlongPath 不支持 DashedLine（points 为空 → 挂死）；回溯/虚线用普通 Line(GRAY)。
    回溯移动不要计入访问序列
15. ghost_move(fade_out=True) 落地即透明：把块"搬进"目标格传 fade_out=False，
    源块补 set_opacity(0.3) 表示已消耗
16. 二维中心补齐三维：`np.array([x, y, 0.0])`，(2,) 向量 move_to 会 broadcast 报错
17. 裸 Mobject 列表不能直接进 _p：`*lines` 展开会 TypeError，用 `Create(VGroup(*lines))`
    （FilmClock._p 已自动包装裸列表）
18. `sortlib.SortArr._make()` 建块后必须 `g.move_to(self.pos(i))`，否则全叠原点
19. `treelib.perfect_layout` 的 leaf_gap 是"整层总宽"：叶不重叠需 leaf_gap ≥ 0.8×槽数

## 七、内容密度与时长原则

1. 不限时长：内容要多长就多长，一章可出 10-15 分钟、拆 5a/5b/5c 分集
2. 每个概念必须有动机（为什么需要）→ 解释（是什么）→ 例子（长什么样）
3. 旁白每一句 ↔ 屏幕视觉精确对应：说"P1"屏上必须有 P1——零容忍
4. 面向高中生：不突然抛概念，先"为什么需要"再"是什么"
5. 改编英文书时图形要真实复刻（说蜂窝晶格就画真蜂窝，不能拿三角网格充数）；
   生成式图形函数的参数语义写死在 docstring；场景画坐标逐点写绝对值，别靠 move_to 事后挪

## 八、实拍验收沉淀（2026-11 film-gougu《弦图》全流程）

0. **全屏吞没式转场闪眼，一律禁用（用户强烈反馈）**：墨色圆盘扩张吞没画面
   （ink_iris 类）在成片上非常刺眼。换幕一律 `_wipe(rt=0.35)` 快速淡出 +
   新幕正常入场；任何"圆盘/闪白/闪黑吞全屏"的转场动效都不要发明。
   注意 _wipe 会连字幕一起清掉，新幕开头记得重挂第一句 caption。

1. **拼图/重排动画的刚体放置有镜像歧义**：把一块三角形搬到目标位，用"斜边向量对齐"
   算出的旋转有 ±180° 两个候选，其中一个是镜像（块翻到斜边错误一侧、落位出框）。
   必须用**直角顶点位置验证**消歧（两个候选里选能把直角顶点映到目标直角顶点的那个，
   参考验收片 film.py 的 `place_piece()`）。切拼图时优先选**所有块都能纯平移入位**的
   对角线切法——纯平移搬运观感最稳，也天然避开镜像。
2. **墨渍转场会把字幕一并吃掉**：`covered_reset()` 静默清场移除了 `_film_caption`，
   之后首句旁白全程无字幕。`ink_iris_out` 之后必须立刻 `caption(self, CAP[首句])`
   重挂（caption 硬切零耗时，不占预算）。
3. **版面利用率不达标时，第一杠杆是相机 zoom 全局放大**：`set_camera_orientation(zoom=1.25)`
   一次搞定，fixed-in-frame 的字幕/口诀不受影响、零重排成本。注意两件事：① 画面底部
   元素 ×zoom 后可能压字幕带，先整组上移再放大；② 居中方图构图的 bbox 利用率天然在
   28~38%（合格），不要拿宽幅双栏的标准硬套。
4. **批量坐标换算禁止手算**：缩放/平移一组顶点时写成 `S(p)` 小函数程序化生成
   （`x'=k·x0；y'=y0+k·(y−y0)`），手算必错——实测 y 基点算错导致落位校验直接炸。
5. **验证器的正则要跟 id 命名走**：CAP/台词键带连字符（`A1-1`）时，
   check_film 的键匹配正则必须含 `-`，否则整批键报"缺失"假红灯。

## 九、速度纪律（2026-11 超时事故：66 秒片渲了 9 次，其中 3 次失败）

渲染/TTS/检查全是秒级——超时 = agent 迭代轮数失控。以下每条都是真实浪费：

1. **新几何先测帧**：弦图顶点坐标手推后直接进正片，全片渲完才发现拼图落位镜像
   ——一整轮报废。任何新几何构造（手推坐标/拼图目标位/新图形函数），先写 3 行
   测试场景渲一帧验证。
2. **指标阈值先测基线再定标**：版面红线一口气改了 4 次（55→45→40→35/20）。
   先对已有成片跑 frame_coverage 量出分布，一次定标。
3. **删代码用函数名精确锚点**（`def foo` 到 `def bar` 之间），禁止"循环跳到下一个
   def"的遍历删除——实测把 CAP 字典和几何助手整段误删，连环返工 3 轮。
4. **CAP 字典只拼接 cap_block.py**（脚本生成/脚本读入），绝不手写或重打——
   转义（
）手写必错。
5. **迁移契约类代码（FilmClock/T/caption/_wipe）整段拷贝**——拷一半漏一个方法，
   渲染时 NameError。
6. **批量坐标换算写 S() 函数**，禁止手算数值（y 基点算错过一次，渲染直接炸）。
7. **抽帧 ≤8 张、一轮看完**：每幕挑 1 张代表帧+关键动作帧，只修硬伤（遮挡/画错/
   越界/序列错/字幕丢失），软瑕疵放过。16 帧逐批看是时间黑洞。
8. **构图第一版就大**：unit/边长按"场景宽 60%+"取。事后 zoom 补救 = 多一轮
   （且底部元素 ×zoom 会压字幕带）。
