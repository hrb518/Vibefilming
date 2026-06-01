"""项目工作区：manifest.json 读写 + 预算状态。

每个项目 = projects/<project_id>/  目录，结构：
  manifest.json          ← 项目状态（budget / entities / 元信息）
  storyboard.json        ← 分镜：title/duration/ratio/shots[]/entities_planned[]
  entities/              ← 角色/物体/场景档案库（每个 entity 一个子目录）
    <entity_name>/
      ref.json           ← entity 元信息：description/canonical_view/views[]
      <view_name>.png    ← 视角/状态图：front / side_left / sheathed / drawn ...
  shots/                 ← 关键帧 + 镜头视频
  audios/                ← BGM / TTS 等音频产物（gen_audio_bgm 落盘到这里）
  composed/              ← 拼接/裁剪/字幕/audio_amix 等后期产物
  reviews/               ← vlm_understand 输出 + 抽帧
  logs/                  ← tool_calls.jsonl（每次调用都按时间戳留痕）
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = ROOT / "projects"
PROJECTS_ROOT.mkdir(exist_ok=True)


def _now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_id(brief: str) -> str:
    """从用户 brief 生成项目 ID：日期 + 简短描述"""
    import re
    short = re.sub(r"[^\w\u4e00-\u9fff]+", "_", brief.strip())[:20]
    return f"p{time.strftime('%Y%m%d_%H%M%S')}_{short}".rstrip("_")


def project_create(brief: str, max_seedance_calls: int = 0) -> dict:
    """创建一个新项目目录 + 初始 manifest。返回 manifest dict。

    max_seedance_calls=0（默认）= **无预算上限**（只记账不阻断），便于 agent 自由迭代。
    需要硬上限时显式传一个正整数。
    """
    pid = _safe_id(brief)
    pdir = PROJECTS_ROOT / pid
    if pdir.exists():
        raise FileExistsError(f"项目已存在：{pdir}")
    for sub in ("entities", "shots", "composed", "reviews", "logs", "audios"):
        (pdir / sub).mkdir(parents=True, exist_ok=True)
    manifest = {
        "project_id": pid,
        "project_dir": str(pdir),
        "brief": brief,
        "created_at": _now_str(),
        "phases": {
            "story":   {"status": "pending"},
            "entity":  {"status": "pending"},
            "asset":   {"status": "pending", "shots_done": 0, "shots_total": 0},
            "animate": {"status": "pending", "shots_done": 0, "shots_total": 0},
            "compose": {"status": "pending"},
            "review":  {"status": "pending"},
        },
        "budget": {
            # 0 = 无上限（仅记账）；正整数 = 硬上限
            "max_seedance_calls": max_seedance_calls,
            "seedance_used": 0,
            "max_vlm_calls": 0,
            "vlm_used": 0,
        },
        "entities": {},
    }
    write_manifest(pid, manifest)
    return manifest


def project_dir(project_id: str) -> Path:
    p = PROJECTS_ROOT / project_id
    if not p.exists():
        raise FileNotFoundError(f"项目不存在：{p}")
    return p


def manifest_path(project_id: str) -> Path:
    return project_dir(project_id) / "manifest.json"


def read_manifest(project_id: str) -> dict:
    return json.loads(manifest_path(project_id).read_text(encoding="utf-8"))


def write_manifest(project_id: str, manifest: dict):
    p = PROJECTS_ROOT / project_id / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def update_phase(project_id: str, phase: str, **kwargs):
    """部分更新某 phase 的状态字段。"""
    m = read_manifest(project_id)
    m.setdefault("phases", {}).setdefault(phase, {}).update(kwargs)
    write_manifest(project_id, m)
    return m


def bump_budget(project_id: str, kind: str, n: int = 1) -> dict:
    """递增预算用量。kind ∈ seedance / vlm。返回更新后的 budget。

    上限为 0（默认）时仅记账不阻断；上限为正整数时超额抛 RuntimeError。
    """
    m = read_manifest(project_id)
    key_used = f"{kind}_used"
    key_max = f"max_{kind}_calls"
    used = m["budget"].get(key_used, 0) + n
    cap = m["budget"].get(key_max, 0)
    if cap and cap > 0 and used > cap:
        raise RuntimeError(f"预算超限：{kind} 已用 {used} > 上限 {cap}")
    m["budget"][key_used] = used
    write_manifest(project_id, m)
    return m["budget"]


# ============== Entity 档案库 ==============
# entity = 跨镜头复用的"主体"（角色/道具/场景），需要多视角/多状态参考图保证一致性。
# 目录：projects/<pid>/entities/<entity_name>/{ref.json, <view>.png ...}
# manifest 里的 entities 字段 = 全项目快照，便于 agent 一次性看到有哪些档案。

VALID_ENTITY_TYPES = ("character", "prop", "scene", "other")


def entity_dir(project_id: str, entity_name: str) -> Path:
    return project_dir(project_id) / "entities" / entity_name


# 不同 entity 类型的默认 views_needed（agent 不传时自动展开）
DEFAULT_VIEWS_NEEDED = {
    # character 默认产 1 张白底三视图（front+side+back 合在一张图里，左→中→右排列）
    # 视频模型只参考这 1 张就够。需要特殊动作（dancing/shooting/squatting）再 add_view 单加
    "character": ["turnaround"],
    "prop":      ["default"],                  # 道具默认 1 张，按剧本再加状态
    "scene":     ["wide"],                     # 场景默认 1 张
    "other":     ["default"],
}


def entity_register(project_id: str, name: str, etype: str,
                    description: str, canonical_view: Optional[str] = None,
                    views_needed: Optional[list] = None) -> dict:
    """登记一个新 entity（不生成图，只建目录 + ref.json + manifest 注册）。
    ref.json 初始 views 为空，后续用 entity_add_view 逐个填充。
    views_needed: 该 entity 计划要做的视角/状态列表。不传时按 etype 默认展开
        （character → 1 张白底 turnaround 三视图）。canonical_view 必须在该列表里。
    canonical_view: 不传时取 views_needed[0]（character 默认 "turnaround"）。
    """
    if etype not in VALID_ENTITY_TYPES:
        raise ValueError(f"entity type 必须是 {VALID_ENTITY_TYPES}，给的是 {etype!r}")
    if views_needed is None:
        views_needed = list(DEFAULT_VIEWS_NEEDED.get(etype, ["default"]))
    if canonical_view is None:
        canonical_view = views_needed[0] if views_needed else "default"
    if canonical_view not in views_needed:
        # canonical 必须在 views_needed 里，否则补到首位
        views_needed = [canonical_view] + [v for v in views_needed if v != canonical_view]
    edir = entity_dir(project_id, name)
    if edir.exists():
        raise FileExistsError(f"entity 已存在：{name}")
    edir.mkdir(parents=True, exist_ok=True)
    ref = {
        "name": name,
        "type": etype,
        "description": description,
        "canonical_view": canonical_view,
        "views_needed": views_needed,
        "views": {},   # view_name -> {"file": "...", "url": "..."}
        "created_at": _now_str(),
    }
    (edir / "ref.json").write_text(
        json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    # 同步到 manifest
    m = read_manifest(project_id)
    m.setdefault("entities", {})[name] = {
        "type": etype, "description": description,
        "canonical_view": canonical_view,
        "views_needed": views_needed,
        "views": [],
    }
    write_manifest(project_id, m)
    return ref


def entity_read(project_id: str, name: str) -> dict:
    """读 entity 的 ref.json。不存在抛异常。"""
    p = entity_dir(project_id, name) / "ref.json"
    if not p.exists():
        raise FileNotFoundError(f"entity 不存在：{name}")
    return json.loads(p.read_text(encoding="utf-8"))


def entity_write(project_id: str, name: str, ref: dict):
    p = entity_dir(project_id, name) / "ref.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    # 同步 manifest 的扁平摘要
    m = read_manifest(project_id)
    m.setdefault("entities", {})[name] = {
        "type": ref.get("type"),
        "description": ref.get("description"),
        "canonical_view": ref.get("canonical_view"),
        "views_needed": ref.get("views_needed", []),
        "views": list(ref.get("views", {}).keys()),
    }
    write_manifest(project_id, m)


def entity_record_view(project_id: str, name: str, view: str,
                        file_path: str, url: str) -> dict:
    """已经生成好 view 图后，把它登记到 ref.json + manifest。"""
    ref = entity_read(project_id, name)
    ref.setdefault("views", {})[view] = {"file": file_path, "url": url}
    entity_write(project_id, name, ref)
    return ref


def entity_list(project_id: str) -> dict:
    """从 manifest 拿到所有 entities 摘要（不解析每个 ref.json）。"""
    m = read_manifest(project_id)
    return m.get("entities", {})


# ============== Storyboard 分镜 ==============
# 分镜 = 项目的"剧本草案"，是后续 entity 登记和 i2v 生成的依据。
# 落到 projects/<pid>/storyboard.json，覆盖式写入；agent 可多次 set 修改。

def storyboard_path(project_id: str) -> Path:
    return project_dir(project_id) / "storyboard.json"


def storyboard_set(project_id: str, board: dict) -> dict:
    """覆盖式写入分镜。同步在 manifest 里登记一个简短摘要。"""
    p = storyboard_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    # 加个时间戳，让多次覆盖可观察
    board = dict(board)
    board["updated_at"] = _now_str()
    p.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    # manifest 摘要
    m = read_manifest(project_id)
    m["storyboard_summary"] = {
        "title": board.get("title", ""),
        "duration_total": board.get("duration_total"),
        "shots_count": len(board.get("shots", [])),
        "entities_planned_count": len(board.get("entities_planned", [])),
        "updated_at": board["updated_at"],
    }
    write_manifest(project_id, m)
    return board


def storyboard_get(project_id: str) -> Optional[dict]:
    """读分镜。没写过返回 None。"""
    p = storyboard_path(project_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_projects() -> list:
    """列出所有项目（按创建时间倒序）。"""
    out = []
    for d in PROJECTS_ROOT.iterdir():
        if not d.is_dir():
            continue
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        try:
            m = json.loads(mp.read_text(encoding="utf-8"))
            out.append({
                "project_id": m["project_id"],
                "brief": m.get("brief", ""),
                "created_at": m.get("created_at", ""),
                "phases": {k: v.get("status") for k, v in m.get("phases", {}).items()},
            })
        except Exception:
            pass
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


def log_tool_call(project_id: Optional[str], tool: str, args: dict, result_brief: str):
    """把每次工具调用都追加到 logs/tool_calls.jsonl。"""
    if not project_id:
        return
    try:
        log_path = project_dir(project_id) / "logs" / "tool_calls.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": _now_str(),
                "tool": tool,
                "args": args,
                "result": result_brief[:300],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_seedance_call(project_id: Optional[str], detail: dict):
    """记录每次 gen_video_* 实际发给 Seedance 的输入清单（已经把 entity 名展开成具体 url）。
    专门用来事后审计：第 N 段视频到底参考了哪几张图、哪段视频。
    写到 logs/seedance_calls.jsonl。
    """
    if not project_id:
        return
    try:
        log_path = project_dir(project_id) / "logs" / "seedance_calls.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now_str(), **detail},
                               ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def log_model_call(project_id: Optional[str], model_kind: str, detail: dict):
    """统一记录所有"调用云端模型"的请求详情，给用户做审计/复盘用。

    model_kind ∈ {seedream, seedance, vlm_video, vlm_image, tts, gen_bgm}
    detail 应包含：name / prompt（完整不截断）/ 关键参数（duration、ratio、ref_*、size、voice、...）
                  + result_brief（task_id 或 url 等）

    写到 logs/model_calls.jsonl。这条日志是**人类可读的全量请求**，跟
    seedance_calls.jsonl（专项 Seedance 审计）和 tool_calls.jsonl（GA 工具调用）互补。
    """
    if not project_id:
        return
    try:
        log_path = project_dir(project_id) / "logs" / "model_calls.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": _now_str(),
                "model_kind": model_kind,
                **detail,
            }, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def get_active_project() -> Optional[str]:
    """读取 .active_project 标记文件，返回当前活跃项目 ID。"""
    f = PROJECTS_ROOT / ".active_project"
    if f.exists():
        pid = f.read_text(encoding="utf-8").strip()
        if (PROJECTS_ROOT / pid).exists():
            return pid
    return None


def set_active_project(project_id: str):
    (PROJECTS_ROOT / ".active_project").write_text(project_id, encoding="utf-8")
