# Film 工具能力清单 · 导航页

> **这是导航页，不是操作手册。**
> 每个工具只列"做什么 / 入参 / 出参"。**怎么用、何时用、几次用、配套打法**全部在 `skill_*.md` 里，按场景自取。

---

## 何时读哪个 skill（场景索引）

| 场景 | 读这个 |
|---|---|
| 拿到 brief，要拆分镜 | [skill_storyboard.md](./skill_storyboard.md) |
| **每次** 调 `gen_video_t2v` / `gen_image` 之前最后一道 prompt 文本检查 | **[skill_prompt_engineering.md](./skill_prompt_engineering.md)** ⭐ |
| 要保证主体（角色/道具/场景）跨镜头一致 / 防 ID 漂移 / 防双胞胎 / >4 人多人场景 | [skill_entity_consistency.md](./skill_entity_consistency.md) |
| 要出 ≥2 段视频 / 想做镜头衔接 / 要拼接（V-6 帧裁剪）/ 防画质劣化（V-8 白模化） | **[skill_video_chain.md](./skill_video_chain.md)** ⭐ |
| 任何带声音的视频 / 配乐连贯性 / 多段共享 BGM / MV 模式 / A-1~A-4 | **[skill_audio.md](./skill_audio.md)** ⭐ |
| 视觉产物落盘后，要审一下 | [skill_director_vlm.md](./skill_director_vlm.md) |
| 要批量出图/出片 / 决定串行还是并行 / 预算紧张 | [skill_async_schedule.md](./skill_async_schedule.md) |
| 想 ask_user / 拿不准要不要打断 | [skill_self_decision.md](./skill_self_decision.md) |

---

## 模型清单（你能调动的视觉/文本智能）

| 模型 | 模型 ID | 能力 |
|---|---|---|
| **Doubao Seed 2.0 pro** | `doubao-seed-2-0-pro-260215` | 文本 + 多图理解 + 视频原生理解（不抽帧） |
| **Doubao Seedream 4.0** | `doubao-seedream-4-0-250828` | 文生图 / 图编辑（带 ref_image_url） |
| **Doubao Seedance 2.0** | `doubao-seedance-2-0-260128` | 文生视频，**只走多模态参考模式**（reference_images / reference_video_url） |

---

## 工作区工具

### `project_create(brief, max_seedance_calls=0)`
建项目目录 `projects/<id>/{manifest.json, entities/, shots/, composed/, reviews/, logs/}`。每个新需求第一步必调。
- `max_seedance_calls=0`（默认）= **无预算上限**（仅记账，不阻断），便于无限审片迭代
- 传正整数 = 硬上限（超额抛错）
- VLM 调用同样默认无上限

> `logs/` 下每个项目自动产出 3 条审计流水：
> - `tool_calls.jsonl` —— GA 框架视角，所有工具调用入参/出参摘要
> - `seedance_calls.jsonl` —— Seedance 专项审计，每段视频用了哪些参考图/参考视频
> - **`model_calls.jsonl`** ⭐ —— 所有"调用云端模型"的**全量请求**：seedream / seedance / vlm_video / vlm_image / tts / gen_bgm，含**完整 prompt**（不截断）+ 关键参数 + 结果。**复盘调用流程时优先看这个**。

### `project_status(project_id?)`
读 manifest：phase / budget / storyboard 摘要 / entities 摘要。

### `project_open(project_id)`
切换活跃项目（跨会话续接老项目用）。

---

## 分镜（详见 [skill_storyboard.md](./skill_storyboard.md)）

### `storyboard_set(title, duration_total, ratio, style, synopsis, entities_planned[], shots[])`
覆盖式写入分镜到 `projects/<pid>/storyboard.json`。`project_create` 之后第一件事（≥2 镜头必做）。

### `storyboard_get()`
读分镜。出每个 shot 之前先调一次。

---

## Entity 档案库（详见 [skill_entity_consistency.md](./skill_entity_consistency.md)）

### `entity_register(name, type, description, canonical_view=None, views_needed=None)`
登记档案，**不出图**。type ∈ character / prop / scene / other。

### `entity_add_view(entity_name, view, prompt, ref_image_url=None)`
出一张视角/状态图。第一张是基准图（无 ref），之后自动用 canonical_view 当 ref。

### `entity_get(entity_name=None)`
查档案。不传 → 列出全部摘要；传了 → 返回 ref.json（每个 view 的 file 和 url）。

### 目录结构

```
projects/<pid>/entities/
├── protagonist_li/                ← character
│   ├── ref.json                   ← 元信息：description / canonical_view / views
│   └── turnaround.png             ← canonical（1 张白底三视图，front/side/back 合一）
└── sword_qingfeng/                ← prop
    ├── ref.json
    ├── sheathed.png               ← canonical（入鞘）
    └── drawn.png                  ← 出鞘
```

---

## 视觉生成

### `gen_image(prompt, name, ref_image_url=None, size='1024x1024')`
Seedream 文生图 / 图编辑。带 `ref_image_url` 即图编辑模式。落到 `shots/<name>.png`。
> ⚠️ 登记过的 entity 角色/道具的视角图请用 `entity_add_view`，不要用这个工具。

### `gen_video_t2v(prompt, name, duration?, generate_audio=False, reference_entities?, reference_images?, reference_video_url?, reference_audios?, resolution='720p', ratio='16:9')`
**唯一的视频生成入口**。Seedance 异步出片，立即返回 `task_id`。
- 只走多模态参考模式：`reference_entities` / `reference_images` / `reference_video_url` / `reference_audios`（**最多 9 张图 + 1 段参考视频 + 0-3 段参考音频**）
- 不支持 first_frame / last_frame / image_url
- ⭐ **链式段（≥2 段视频时第 N 段）**：要承接动作/姿态/光影时把上段视频塞 `reference_video_url`；要对白音色连贯就把上段塞 `reference_audios`。何时要承接、何时不要 → 见 [skill_video_chain.md](./skill_video_chain.md) + [skill_audio.md](./skill_audio.md)
- ⚠️ prompt 4 类特殊字符：音效 `<>` / 台词 `{}` / 字幕 `【】`；🚫 **禁用** `（）` 写 BGM（代码层 lint 直接 raise，整片 BGM 走 `gen_audio_bgm`）

### `query_video_task(task_id, save_name?, duration?, wait=True, max_wait?)`
阻塞轮询到任务完成，**自动按 duration 估 ETA、动态调轮询间隔、打印进度条**（10s 视频约 210s，15s 视频约 285s）。建议传 duration 让 ETA 准。落到 `shots/<save_name>.mp4`，返回 `{path, video_url}`，把云端 url 写到 `<save_name>.url.txt` sidecar 方便后续段引用。

### `cancel_video_task(task_id)`
尝试取消 Seedance 任务（DELETE）。⚠️ **仅在 queued / pending 阶段可取消**；一旦 running 平台拒绝（HTTP 409），只能等它跑完。已 succeeded 或不存在也会 graceful 返回。

### `sleep(seconds)`
显式等待，最多 120s。query 已自带等待，几乎不用单独调。

---

## 视频处理

| 工具 | 能力 | 注意 |
|---|---|---|
| `video_concat(clips, name)` | ffmpeg 硬拼接（无重编码，秒级） | 所有 clip 同分辨率/帧率 |
| `video_crossfade(clip_a, clip_b, name, duration=1, offset=4)` | 交叉淡化 | 会重编码，慢于 concat |
| `video_trim(clip, start, end, name)` | 裁剪 [start, end] 秒区间 | 时间是秒，浮点 |
| `video_speed(clip, factor, name)` | 变速（音视频同步） | 0.5-2.0 最稳；⚠️ 严禁拿来凑分镜总时长 |
| `video_overlay(base, pip, name, pip_scale=0.33, position='br')` | 画中画 | position ∈ tl/tr/bl/br |
| `video_fade(clip, name, fade_in=0.5, fade_out=0.5)` | 头尾黑场（音视频同步） | total_duration 不传会 ffprobe 探测 |
| `video_portrait(clip, name, width=720, height=1280)` | 横转竖（居中裁剪） | 短视频/竖屏发布 |
| `burn_subtitle(clip, text, name, start, end, fontsize=32)` | 字幕硬烧（drawtext） | 永久叠加，不可关 |

---

## 视觉评估

### `vlm_understand(clip, question, mode='auto', fps=1.0, max_tokens=1200, temperature=0.3, name='understand')`
**唯一的视觉评估入口**。自己写 question，Doubao Seed 2.0 pro 回答。
- 视频走原生理解（不抽帧），图片走多图理解
- `mode='frames'` 强制抽帧（视频很长想省钱）
- 输出自由文本，落到 `reviews/<name>.json`
- 怎么问才能拿到可执行答案 → 详见 [skill_director_vlm.md](./skill_director_vlm.md)

### `extract_frames(clip, name, fps=1.0)`
单纯抽帧（不调 VLM）。debug 看视频内容用。

---

## 音频

> ⭐⭐⭐ **项目级铁律**：
> - **Seedance 不出 BGM**：`gen_video_t2v(generate_audio=True)` 只生成"对话 + 音效"；prompt 禁止用 `（）` 写 BGM（代码层 lint 已硬拦）
> - **整片 BGM 唯一入口**：`gen_audio_bgm` + `query_audio_task`（火山 BigMusic GenBGM v5.0），出片流水线最后一步生成等长 BGM，amix 铺底，**必走 `vlm_understand(name="review_final_with_bgm")` 审过再交付**

| 工具 | 能力 | 注意 |
|---|---|---|
| `gen_video_t2v(..., generate_audio=True, reference_audios=[...])` | 生成"对话 + 音效"（本项目用法） | 🚫 **不要让它出 BGM**；prompt 禁用 `（）` 写 BGM；要对白音色连贯传 `reference_audios=[上段video_url]` |
| `gen_audio_bgm(prompt, name, base_video?, duration?, segments?)` | **整片 BGM 异步任务提交**（火山 BigMusic GenBGM） | 传 `base_video` 自动 probe 时长 + clamp 到 [30,120]；prompt ≥50 字含风格/情绪/乐器/场景 4 要素，否则踩 50000001 版权校验 |
| `query_audio_task(task_id, save_name)` | 阻塞轮询 BGM 任务，落盘到 `audios/<save_name>.mp3` | 单次 30-90s 完成；max_wait 默认 180s |
| `audio_amix(base_video, bgm_audio, name, bgm_volume=0.2)` | **整片合成：BGM 铺底** | bgm_volume 一般 0.15-0.25；先 `video_concat` 拼整片再 amix |
| `probe_duration(media)` | ffprobe 拿媒体时长（秒） | 通常 `gen_audio_bgm` 内部已自动调，外部一般不用 |
| `tts(text, name, voice='default')` | 豆包 TTS（备用，台词一般已走 Seedance 内建） | **当前需 TTS_APP_ID/TTS_TOKEN，无 key 报错** |

> **标准 BGM 流水线**：所有 shot 全过审 → `video_concat` 拼整片 → `gen_audio_bgm(base_video=final_no_bgm.mp4)` → `query_audio_task` 落盘 → `audio_amix` 铺底 → `vlm_understand(review_final_with_bgm)` 必审 → 过审才交付。
> 详细规范全部见 **[skill_audio.md](./skill_audio.md)** ⭐。

---

## GA 通用工具（继承）

`code_run` / `file_read` / `file_write` / `file_patch` / `web_scan` / `web_execute_js` / `update_working_checkpoint` / `ask_user` / `start_long_term_update`
