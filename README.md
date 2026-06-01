<div align="center">

# 🎬 VibeFilming

### 一句 Brief，一部短片。AI 导演自己分镜、自己出片、自己审、自己改。

**你只管说一句话——「给我做个 30 秒校园霸凌警示公益片」**
**它做：分镜 → 出图 → 出视频 → VLM 审片 → 拼片 → 配 BGM → 交付**

*基于 [GenericAgent](https://github.com/JinyiHan99/GA-Technical-Report) 框架 · ARK + BigMusic 双引擎 · 全流程自主决策*

---

🎨 Seedream 4.0 出图　🎬 Seedance 2.0 出视频　👁️ Seed 2.0 当导演审片　🎵 BigMusic 自主配乐

</div>

---

## ✨ 它能做什么

| 你说一句 | 它干这些活 |
|---|---|
| "做个 30s 公益小视频" | 分镜（4 镜）→ 4 个角色档案 → 4 段视频 → 拼片 → 暖色 BGM → 交付 mp4 |
| "宠物跳舞 15 秒，竖屏" | 分镜（3 镜）→ 萌宠 turnaround 基准图 → 3 段动态 → 9:16 竖屏拼接 → 欢快电子 BGM |
| "武侠片 60s，刀光剑影" | 分镜（5 镜）→ 主角三视图 + 兵器立绘 → 5 段链式承接 → 概念片节奏 BGM |
| "30s 海边温情" | 自动判断不需要对白 → 海浪原生音 + 钢琴铺底 BGM |

**全程不需要你介入**——它会自己想分镜、自己写 prompt、自己审片不过审就重做、自己判断需不需要 BGM 配什么风格的 BGM。

**你只在两种情况下被打扰**：①brief 实在没说清 ②预算烧到一半还没出片需要确认。

---

## 🔥 凭什么它能"自主"？

我们没用任何工作流编排框架。整套系统就一个 **~100 行的 agent 主循环 + 30 个原子工具 + 一堆经验文档**。
让 agent 自己变聪明的核心是这三件事：

### 1. 「导演式自审」 —— 每个产物 VLM 当导演审一眼

不是 QA 验收题（"是否符合 A+B+C+D"），而是导演审美题（"作为这部片的导演你看上了哪些点 / 你觉得哪里不对"）。

```
✅ 过审 → 进下一步
❌ 不过审 → 给"导演视角的问题诊断+想要的样子" → agent 走 PE 7 步翻译成合规 prompt → 重做（最多 2 轮）
```

按产物类型分 **A 基准图 / B 单镜头 / C 全片成片** 三套模板，每套都有专属的导演关注重心。

### 2. 「Prompt Engineering 7 步 + 5 大死罪」—— prompt 不是 prompt 是工程产物

每次喂给 Seedance/Seedream 之前，agent 必须按 PE checklist 过 7 步：任务类型 / 主体定义 / 动态顺序 / 4 类符号 / BGM 闸门 / 时长比例 / 反例扫描。**5 大死罪一个都不许踩**：

| # | 死罪 | 翻车现场 |
|---|---|---|
| 1 | ≥3 主体未定义 | 三个垃圾桶分不清谁是谁 |
| 2 | 主体特征定后变 | 「红裙女孩」开头红裙结尾蓝裙 |
| 3 | 多素材未绑定 | 「老奶奶 + 小女孩 + 垃圾桶」三视图但 prompt 只写「老奶奶」 |
| 4 | 描述顺序乱 | 主体写在镜头之前，画面歪 |
| 5 ⭐ | **张嘴无声** | 写「老奶奶夸奖」没补 `{真棒！}` → 演员张嘴没声音演哑剧 |

### 3. 「BGM 三道代码闸门」—— Seedance 模型休想脑补 BGM

| 闸门 | 机制 |
|---|---|
| 1 默认值 | `generate_audio=False`，模型完全不出音轨 |
| 2 lint 拦截 | prompt 写`（轻快 BGM）`/`配乐：xxx` → 代码层直接 raise，agent 必须改 |
| 3 兜底追加 | `generate_audio=True` 时工具自动追加"无背景音乐"，留对白和音效 |

**整片 BGM 的唯一入口** = 流水线最后一步的 `gen_audio_bgm`（火山 BigMusic GenBGM v5.0），由 agent 自主判断要不要配 + 配什么风格。

---

## 🚀 三步跑起来

### 1. 装环境

```bash
bash setup.sh
```

脚本会：检查 Python 3.11/3.12 → 建 `.venv` → 装依赖 → 复制 `mykey.example.py` → `mykey.py`。

### 2. 填 API key

编辑 [mykey.py](./mykey.py)：

**必填** —— 豆包 ARK（出图/出视频/VLM 审片）：
```python
'apikey': 'ark-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
```

**可选** —— 火山 BigMusic（自动配 BGM）：
```python
volc_open_api_config = {
    'VOLC_AK': 'AKLT...',
    'VOLC_SK': '...==',
    ...
}
```

不填 BigMusic 也能跑，只是不能自动配 BGM（手动塞 mp3 走 `audio_amix` 也行）。

详细开通流程见 [mykey.example.py](./mykey.example.py) 里的注释。

### 3. 启动

```bash
source .venv/bin/activate
python3 agentmain.py
```

进 REPL 后直接说人话：

```
> 给我做一段关于宠物的温情小视频
> 生成一段 30s 的科幻武侠片
> 帮我剪一个 15 秒夏日海边短片，竖屏，海浪原生音 + 钢琴 BGM
```

退出：`Ctrl+C` 或 `/exit`。

---

## 🎞️ 端到端工作流

```
你的 brief
    ↓
[阶段 1] storyboard_set 设计分镜（agent 自己拍板）
    ↓
[阶段 2] entity-first 出角色/道具/场景基准图
         └─ 每个 entity 必过 vlm_understand（导演审片）
    ↓
[阶段 3] 每个 shot：PE 7 步 → gen_video_t2v → query_video_task
         └─ 每段必过 vlm_understand（不过审就重做，最多 2 轮）
    ↓
[阶段 4] 所有 shot 全过审 → video_concat → final_no_bgm.mp4
    ↓
[阶段 5] 🎵 agent 自主决策要不要 BGM、配什么风格
         └─ gen_audio_bgm → query_audio_task → audio_amix → review_final_with_bgm
    ↓
[阶段 6] 🎁 交付 final.mp4
```

---

## 📁 输出在哪

```
projects/<project_id>/
├── manifest.json          ← 项目元信息 / 预算 / 状态
├── entities/              ← 角色/道具/场景基准图
├── shots/                 ← 每个 shot 的 mp4 + 关键帧
├── composed/
│   └── final_xxx.mp4      ← ⭐ 最终交付
├── audios/                ← BGM mp3
├── reviews/               ← 每次 VLM 导演审片的问答记录（json）
└── logs/
    └── tool_calls.jsonl   ← 完整工具调用日志（含烧钱总账）
```

---

## 🛠️ 工具清单（30+ 原子工具）

| 类别 | 工具 |
|---|---|
| 🗂️ 工作区 | `project_create` / `project_status` / `project_open` / `storyboard_set` |
| 🎭 角色档案 | `entity_register` / `entity_add_view` |
| 🎨 视觉生成 | `gen_image` / `gen_video_t2v` / `query_video_task` |
| ✂️ 视频处理 | `video_concat` / `video_crossfade` / `video_trim` / `video_speed` / `video_overlay` / `video_fade` / `video_portrait` |
| 🎵 音频 | `gen_audio_bgm` ⭐ / `query_audio_task` ⭐ / `audio_amix` / `tts` |
| 👁️ 评估 | `vlm_understand`（导演视角审片，三场景模板）/ `extract_frames` |
| 🔧 工具 | `probe_duration` / `burn_subtitle` / `sleep` |

详细能力见 [memory/film_capabilities.md](./memory/film_capabilities.md)。

---

## 🧠 设计原则

- **导演视角自审**：VLM 不打分、不列维度、不写 QA 报告，按导演审美发散性评判
- **VLM ≠ PE 工程师**：VLM 只出"问题诊断+想要的样子"，agent 走 PE 7 步翻译成工程化 prompt
- **流程不钉死**：没有"必须 P1→P2→P3"的硬流程，agent 根据 review 反馈自己跳回重做 / 跳过 / 换思路
- **代码层硬保障 + 文档层经验沉淀**：能用代码闸门防的（BGM lint / generate_audio 默认值 / entity 必过审）就不用文档约束；只有方法论沉淀才进 skill md
- **小步快跑**：单次只出最小可验证产物，VLM 看一眼再扩张
- **节约预算**：图编辑优先于重画，能并行就并行（链式承接除外）

完整 sys_prompt 见 [assets/sys_prompt_film.txt](./assets/sys_prompt_film.txt)，所有经验沉淀在 [memory/skill_*.md](./memory/)。

---

## ❓ 常见问题

**Q: 报 401 / 403**
A: `mykey.py` 里 apikey 没填对，或对应模型没在火山方舟开通访问权限。

**Q: BGM 报 200028 APINoSource**
A: 火山 BigMusic 服务没开通。去 https://console.volcengine.com/ai-music 开通"音乐生成"服务即可。

**Q: 报 ffmpeg not found**
A: `setup.sh` 装的 `imageio-ffmpeg` 自带 ffmpeg。如还报错：`brew install ffmpeg`（macOS）/ `apt install ffmpeg`（Linux）。

**Q: 视频任务长时间不返回**
A: Seedance 单段 200-300s 是正常的。`query_video_task` 最多阻塞 5 分钟，超时可重试。

**Q: agent 卡住没反应**
A: `Ctrl+C` 重启即可。项目状态都在 `projects/<id>/manifest.json`，不会丢。

**Q: 想换 LLM（不用豆包）**
A: 编辑 [mykey.py](./mykey.py)，通用模板见 [mykey_template.py](./mykey_template.py)。**但生图/生视频/VLM 必须用豆包**（代码里写死了模型 ID）。

---

## 🎮 REPL 控制命令

| 命令 | 说明 |
|---|---|
| `/new` | 开新对话清空上下文（项目文件保留） |
| `/continue` | 列出可恢复的会话快照 |
| `/llm` | 切换 LLM session |
| `/session.temperature=0.3` | 临时调采样温度 |
| `/exit` | 退出 |

---

## 📚 想深入研究？

| 文档 | 内容 |
|---|---|
| [memory/skill_prompt_engineering.md](./memory/skill_prompt_engineering.md) | PE 7 步 + 5 大死罪 + 4 类符号实战 |
| [memory/skill_director_vlm.md](./memory/skill_director_vlm.md) | VLM 当导演的三场景审片模板 |
| [memory/skill_entity_consistency.md](./memory/skill_entity_consistency.md) | 角色一致性 / 三视图 / 防 ID 漂移 |
| [memory/skill_video_chain.md](./memory/skill_video_chain.md) | 链式衔接 / 帧裁剪 / 防画质劣化 |
| [memory/skill_audio.md](./memory/skill_audio.md) | BGM 决策 + BigMusic 接入 + 三道闸门 |
| [memory/skill_storyboard.md](./memory/skill_storyboard.md) | 分镜设计 / entities_planned 必填 |

---

<div align="center">

**🎬 让 AI 当导演，让导演只说一句话。**

⭐ 觉得有用，给个 Star 支持一下

</div>
