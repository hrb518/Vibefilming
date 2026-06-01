"""VLM 闭环优化 Demo：让 VLM 当导演，连续两轮反复打磨同一个镜头

  Round 0  ── 用户原始 prompt → Seedream 关键帧 → Seedance 出片 → VLM 评分 + 改进建议
  Round 1  ── 把 VLM 的改进建议合并进 prompt → 重新出片 → VLM 再次评分
  对比     ── 把两轮的所有中间产物 + 模型原始返回都落到 txt，方便人工 diff

特点
  - 每个模型的**原始返回 JSON** 都完整保存（不解析、不截断）
  - 每一轮的 keyframe / video 都独立目录
  - 最后生成 summary.txt 对比两轮的得分变化和 prompt 演进
  - 默认用 Seedance Fast 档（约 30-90s/段），整轮 ~3-5 分钟

用法
  python pipeline_vlm_optimize.py
  python pipeline_vlm_optimize.py --rounds 3
  python pipeline_vlm_optimize.py --model standard   # 用标准 Seedance（更慢但更好）
"""
import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

from _common import banner, ok, fail, info, get_ark_key, get_ark_base, OUT_DIR

WORK = OUT_DIR / "vlm_optimize"
WORK.mkdir(exist_ok=True)

# 初始用户 prompt（故意写得模糊一点，这样有改进空间）
USER_BRIEF = "拍一只橘猫在晨光中跳上窗台"

# 模型 ID
MODEL_TEXT = "doubao-seed-2-0-pro-260215"     # 文本 + VLM 同一模型
MODEL_IMG  = "doubao-seedream-4-0-250828"
SEEDANCE_FAST = "doubao-seedance-2-0-fast-260128"
SEEDANCE_STD  = "doubao-seedance-2-0-260128"


# ============== 工具：HTTP + 落盘 ==============
START = time.time()


def log(tag: str, msg: str):
    print(f"  [{time.time()-START:7.2f}s] {tag:<14} ▶ {msg}")


def http_post(url: str, body: dict, key: str, timeout: int = 180) -> dict:
    log("HTTP", f"POST {url.split('/api/v3')[-1]}  body~{len(json.dumps(body))}B")
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        log("HTTP", f"  ← {r.status} OK ({time.time()-t0:.2f}s)")
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        log("HTTP", f"  ← {e.code} FAIL: {body[:300]}")
        raise


def http_get(url: str, key: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def save_text(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    log("save", f"→ {path.relative_to(WORK)}  ({len(content)} chars)")


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    log("save", f"→ {path.relative_to(WORK)}  ({path.stat().st_size} bytes)")


def save_bytes(path: Path, data: bytes):
    path.write_bytes(data)
    log("save", f"→ {path.relative_to(WORK)}  ({len(data)/1024:.0f} KB)")


# ============== Phase: 生成关键帧 ==============
def gen_keyframe(key: str, prompt: str, round_dir: Path, idx: str = "01"):
    save_text(round_dir / f"{idx}a_keyframe_prompt.txt", prompt)
    data = http_post(
        f"{get_ark_base()}/images/generations",
        {"model": MODEL_IMG, "prompt": prompt, "size": "1024x1024", "response_format": "url"},
        key,
    )
    save_json(round_dir / f"{idx}b_keyframe_api_raw.json", data)
    img_url = data["data"][0]["url"]
    img_bytes = urllib.request.urlopen(img_url, timeout=60).read()
    save_bytes(round_dir / f"{idx}c_keyframe.png", img_bytes)
    return img_url


# ============== Phase: 生成视频 ==============
def gen_video(key: str, prompt: str, image_url: str, round_dir: Path, model: str, idx: str = "02"):
    save_text(round_dir / f"{idx}a_video_prompt.txt", prompt)
    submit = http_post(
        f"{get_ark_base()}/contents/generations/tasks",
        {
            "model": model,
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
        key,
    )
    save_json(round_dir / f"{idx}b_video_submit_raw.json", submit)
    task_id = submit["id"]
    log("Seedance", f"task_id={task_id}，开始轮询...")

    deadline = time.time() + 600
    last_status = ""
    final_st = None
    while time.time() < deadline:
        time.sleep(10)
        st = http_get(f"{get_ark_base()}/contents/generations/tasks/{task_id}", key)
        if st.get("status") != last_status:
            log("Seedance", f"  status: {last_status or '(submitted)'} → {st.get('status')}")
            last_status = st.get("status")
        if st.get("status") in ("succeeded", "failed"):
            final_st = st
            break
    if not final_st:
        raise TimeoutError("Seedance 轮询超时")
    save_json(round_dir / f"{idx}c_video_final_raw.json", final_st)
    if final_st.get("status") != "succeeded":
        raise RuntimeError(f"Seedance 失败：{final_st}")

    video_url = (
        final_st.get("content", {}).get("video_url")
        or final_st.get("video_url")
    )
    if not video_url:
        raise RuntimeError(f"找不到 video_url：{final_st}")
    video_bytes = urllib.request.urlopen(video_url, timeout=180).read()
    save_bytes(round_dir / f"{idx}d_video.mp4", video_bytes)
    return round_dir / f"{idx}d_video.mp4"


# ============== Phase: VLM 复审（结构化打分 + 改进建议）==============
def vlm_review(key: str, video_path: Path, original_brief: str, current_prompt: str, round_dir: Path):
    """抽帧 + 让 VLM 输出严格 JSON"""
    import subprocess
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    frames_dir = round_dir / "03_review_frames"
    if frames_dir.exists():
        import shutil
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()
    log("ffmpeg", f"抽帧 fps=1 → {frames_dir.name}")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path), "-vf", "fps=1",
         str(frames_dir / "f_%02d.jpg")],
        capture_output=True, check=True,
    )
    frames = sorted(frames_dir.glob("*.jpg"))
    pick = frames[: min(5, len(frames))]
    log("ffmpeg", f"  共 {len(frames)} 帧，取 {len(pick)} 帧给 VLM")

    image_msgs = []
    for fp in pick:
        b64 = base64.b64encode(fp.read_bytes()).decode()
        image_msgs.append({"type": "image_url",
                           "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    review_prompt = f"""你是一名严格的影视审片导演。下面是一段短视频的若干关键帧。

【用户原始诉求】{original_brief}

【实际生成时使用的 prompt】{current_prompt}

请你：
1. 从下面 4 个维度各打 1-5 分（5=很好，1=很差）：
   - character_consistency: 主角外观一致性
   - motion_quality: 运动自然度（结合多帧）
   - prompt_fidelity: 与 prompt 的贴合度
   - cinematography: 镜头语言/构图/光影
2. 指出这一版**最主要的 1-3 条问题**
3. 给出**针对下一轮 prompt 的具体改进建议**（要可执行的描述短语，比如"低角度仰拍"/"晨光金色"，不要空话）

严格按 JSON 输出，不要任何额外文字：
{{
  "scores": {{
    "character_consistency": <int>,
    "motion_quality": <int>,
    "prompt_fidelity": <int>,
    "cinematography": <int>
  }},
  "overall": <float, 4个维度平均>,
  "issues": ["问题1", "问题2"],
  "prompt_additions": ["改进短语1", "改进短语2"],
  "prompt_negatives": ["要避免的问题描述1"]
}}"""

    save_text(round_dir / "04a_vlm_request_prompt.txt", review_prompt)

    data = http_post(
        f"{get_ark_base()}/chat/completions",
        {
            "model": MODEL_TEXT,
            "messages": [{
                "role": "user",
                "content": image_msgs + [{"type": "text", "text": review_prompt}],
            }],
            "max_tokens": 800,
            "temperature": 0.2,
        },
        key,
    )
    save_json(round_dir / "04b_vlm_api_raw.json", data)

    raw_text = data["choices"][0]["message"]["content"].strip()
    save_text(round_dir / "04c_vlm_response_raw.txt", raw_text)

    # 尝试解析 JSON
    parsed_text = raw_text
    if parsed_text.startswith("```"):
        parsed_text = parsed_text.split("```")[1]
        if parsed_text.startswith("json"):
            parsed_text = parsed_text[4:]
    parsed_text = parsed_text.strip()

    try:
        review = json.loads(parsed_text)
    except json.JSONDecodeError as e:
        log("VLM", f"  ⚠️ JSON 解析失败：{e}，已保存 raw 文本")
        # 兜底：构造一个空结构
        review = {
            "scores": {}, "overall": 0,
            "issues": ["VLM 返回非 JSON，需重试"],
            "prompt_additions": [], "prompt_negatives": [],
            "_parse_error": str(e),
            "_raw": raw_text,
        }

    save_json(round_dir / "04d_vlm_parsed.json", review)
    return review


# ============== 把 VLM 反馈合进新 prompt ==============
def refine_prompt(prev_prompt: str, review: dict) -> str:
    additions = review.get("prompt_additions") or []
    negatives = review.get("prompt_negatives") or []
    parts = [prev_prompt]
    if additions:
        parts.append("，" + "，".join(additions))
    if negatives:
        parts.append("。避免：" + "；".join(negatives))
    return "".join(parts)


# ============== 一轮完整流程 ==============
def run_round(round_idx: int, prompt: str, key: str, model: str) -> dict:
    banner(f"Round {round_idx}：用当前 prompt 出片 + VLM 评分")
    rd = WORK / f"round_{round_idx}"
    rd.mkdir(exist_ok=True)
    save_text(rd / "00_brief_and_prompt.txt",
              f"=== USER BRIEF ===\n{USER_BRIEF}\n\n=== ROUND {round_idx} PROMPT ===\n{prompt}\n")

    log("Round", f"开始 Round {round_idx}")
    img_url = gen_keyframe(key, prompt, rd)
    video_path = gen_video(key, prompt, img_url, rd, model)
    review = vlm_review(key, video_path, USER_BRIEF, prompt, rd)

    scores = review.get("scores", {})
    overall = review.get("overall", 0)
    log("Round", f"  Round {round_idx} 总分 {overall} | scores={scores}")
    if review.get("issues"):
        for issue in review["issues"]:
            info(f"   ✗ {issue}")
    if review.get("prompt_additions"):
        for add in review["prompt_additions"]:
            info(f"   + {add}")

    return {"round": round_idx, "prompt": prompt, "video": str(video_path), "review": review}


# ============== 主流程 ==============
def main():
    global START
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=2, help="轮数（默认 2）")
    p.add_argument("--model", choices=["fast", "standard"], default="fast",
                   help="Seedance 档位")
    args = p.parse_args()

    model_id = SEEDANCE_FAST if args.model == "fast" else SEEDANCE_STD
    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return 1

    START = time.time()
    info(f"=== VLM 闭环优化 · {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    info(f"USER_BRIEF: {USER_BRIEF}")
    info(f"轮数: {args.rounds} | Seedance 档位: {args.model} ({model_id})")
    info(f"工作目录: {WORK}")

    history = []
    current_prompt = USER_BRIEF
    for i in range(args.rounds):
        try:
            result = run_round(i, current_prompt, key, model_id)
        except Exception as e:
            fail(f"Round {i} 失败：{e}")
            return 2
        history.append(result)
        # 给下一轮提炼 prompt
        if i < args.rounds - 1:
            current_prompt = refine_prompt(current_prompt, result["review"])
            log("Refine", f"下一轮新 prompt（{len(current_prompt)} chars）")

    # ============== 汇总报告 ==============
    banner("Summary：两轮对比")
    summary_lines = []
    summary_lines.append(f"USER_BRIEF: {USER_BRIEF}")
    summary_lines.append(f"轮数: {args.rounds} | model: {args.model} ({model_id})")
    summary_lines.append(f"总耗时: {time.time()-START:.1f}s")
    summary_lines.append("")
    summary_lines.append("=" * 70)
    for h in history:
        summary_lines.append(f"\n>>> Round {h['round']}")
        summary_lines.append(f"PROMPT: {h['prompt']}")
        summary_lines.append(f"VIDEO:  {Path(h['video']).relative_to(WORK)}")
        scores = h["review"].get("scores", {})
        summary_lines.append(f"SCORES: {scores}")
        summary_lines.append(f"OVERALL: {h['review'].get('overall', 0)}")
        if h["review"].get("issues"):
            summary_lines.append("ISSUES:")
            for it in h["review"]["issues"]:
                summary_lines.append(f"  - {it}")
        if h["review"].get("prompt_additions"):
            summary_lines.append("ADDITIONS:")
            for it in h["review"]["prompt_additions"]:
                summary_lines.append(f"  + {it}")
    summary_lines.append("\n" + "=" * 70)

    # 计算变化
    if len(history) >= 2:
        s0 = history[0]["review"].get("overall", 0) or 0
        sn = history[-1]["review"].get("overall", 0) or 0
        delta = sn - s0
        summary_lines.append(f"\nOVERALL Δ: {s0} → {sn}  ({'+' if delta>=0 else ''}{delta:.2f})")

    summary_text = "\n".join(summary_lines)
    save_text(WORK / "summary.txt", summary_text)
    print("\n" + summary_text)
    print(f"\n✅ 全部产物在 {WORK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
