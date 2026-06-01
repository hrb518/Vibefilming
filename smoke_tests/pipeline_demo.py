"""6 阶段 pipeline 演示（带详细日志）

  Phase 1  Story   ── Doubao-Pro  → 写出 3 个分镜的 JSON
  Phase 2  Entity  ── Seedream    → 生成 1 张「橘猫主角」参考图（角色一致性锚点）
  Phase 3  Asset   ── Seedream    → 每个分镜出 1 张关键帧图
  Phase 4  Animate ── Seedance    → 每张关键帧 → 1 段 5s 视频（默认走 stub）
  Phase 5  Compose ── ffmpeg      → crossfade 串接 + 字幕 + BGM
  Phase 6  Review  ── Doubao VLM  → 抽帧打分

运行：
  python pipeline_demo.py             # 默认：阶段 4 用已有视频做 stub（快）
  python pipeline_demo.py --full      # 阶段 4 真跑 Seedance（慢，每段 ~4 分钟）
  python pipeline_demo.py --skip 4 5  # 跳过指定阶段
"""
import argparse
import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import imageio_ffmpeg

from _common import banner, ok, fail, info, get_ark_key, get_ark_base, OUT_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
WORK = OUT_DIR / "pipeline"
WORK.mkdir(exist_ok=True)


# ===================== 日志小工具 =====================
def log(stage: str, msg: str):
    """统一格式：[Phase X | 经过秒数 | 当前阶段名] 消息"""
    t = time.time() - START
    print(f"  [{t:7.2f}s] {stage:<14} ▶ {msg}")


def step(name: str, n: int, total: int):
    info(f"   ↳ ({n}/{total}) {name}")


def dump(label: str, obj, max_chars: int = 200):
    """简短预览复杂对象"""
    s = json.dumps(obj, ensure_ascii=False) if not isinstance(obj, str) else obj
    if len(s) > max_chars:
        s = s[:max_chars] + f"... ({len(s)} chars)"
    info(f"   {label}: {s}")


def http_post(url: str, body: dict, key: str, timeout: int = 120) -> dict:
    log("HTTP", f"POST {url.split('/api/v3')[-1]}  body~{len(json.dumps(body))}B")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        log("HTTP", f"  ← {resp.status} OK ({time.time()-t0:.2f}s)")
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        log("HTTP", f"  ← {e.code} FAIL: {body[:200]}")
        raise


def http_get(url: str, key: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_ffmpeg(cmd: list, label: str, timeout: int = 180):
    log("ffmpeg", f"{label}  args~{len(' '.join(cmd))}B")
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log("ffmpeg", f"  ❌ FAIL: {r.stderr[-300:]}")
        raise RuntimeError(r.stderr[-300:])
    log("ffmpeg", f"  ✅ {time.time()-t0:.2f}s")


# ===================== Phase 1: Story =====================
def phase1_story(key: str) -> dict:
    banner("Phase 1 / Story  ── Doubao-Pro 编 3 个分镜")
    log("P1.in", "用户原始 brief：'橘猫日常 vlog 三段，每段 5s'")
    sys_prompt = "你是一个专业的短片导演。输出严格的 JSON。"
    user_prompt = (
        "为一只橘猫拍 3 个短镜头，每个 5 秒。返回 JSON："
        '{"shots":[{"id":"s01","desc":"...","camera":"..."},...]}。'
        "shots 必须正好 3 项；desc 是镜头内容，camera 是镜头运动。只输出 JSON。"
    )
    log("P1.req", f"system={sys_prompt[:30]}... | user={user_prompt[:60]}...")

    data = http_post(
        f"{get_ark_base()}/chat/completions",
        {
            "model": "doubao-seed-2-0-pro-260215",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 600,
        },
        key,
    )
    text = data["choices"][0]["message"]["content"].strip()
    # 防御性剥离 ```json
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    log("P1.out", f"模型返回 {len(text)} 字符")
    storyboard = json.loads(text.strip())

    if "shots" not in storyboard or len(storyboard["shots"]) != 3:
        raise ValueError(f"分镜结构异常：{storyboard}")

    for i, s in enumerate(storyboard["shots"], 1):
        info(f"   ↳ Shot {i}: {s.get('desc', '')[:60]}")

    out = WORK / "01_storyboard.json"
    out.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"分镜落盘 → {out.relative_to(OUT_DIR.parent.parent)}")
    return storyboard


# ===================== Phase 2: Entity =====================
def phase2_entity(key: str) -> str:
    banner("Phase 2 / Entity ── Seedream 出 1 张主角参考图")
    prompt = "一只可爱的橘色虎斑猫，绿色眼睛，圆脸，特写正面照，纯白背景，写实风格"
    log("P2.in", f"角色 prompt：{prompt}")
    data = http_post(
        f"{get_ark_base()}/images/generations",
        {
            "model": "doubao-seedream-4-0-250828",
            "prompt": prompt,
            "size": "1024x1024",
            "response_format": "url",
            "n": 1,
        },
        key,
    )
    url = data["data"][0]["url"]
    log("P2.out", f"参考图 URL（{len(url)} 字符）")

    # 下载到本地，后续阶段可以引用
    img_path = WORK / "02_entity_cat.png"
    img_path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    ok(f"主角参考图 → {img_path.name}（{img_path.stat().st_size/1024:.0f} KB）")
    return url


# ===================== Phase 3: Asset =====================
def phase3_assets(key: str, storyboard: dict, entity_url: str) -> list:
    banner("Phase 3 / Asset  ── Seedream 给每个分镜出 1 张关键帧")
    shots = storyboard["shots"]
    keyframes = []
    for i, s in enumerate(shots, 1):
        step(f"Shot {s['id']}：{s['desc'][:40]}", i, len(shots))
        prompt = f"{s['desc']}。主角是一只橘色虎斑猫，绿色眼睛，写实风格，电影感构图"
        data = http_post(
            f"{get_ark_base()}/images/generations",
            {
                "model": "doubao-seedream-4-0-250828",
                "prompt": prompt,
                "image": entity_url,        # 引用主角参考图，做角色一致性
                "size": "1024x1024",
                "response_format": "url",
            },
            key,
        )
        url = data["data"][0]["url"]
        path = WORK / f"03_keyframe_{s['id']}.png"
        path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        log("P3.out", f"  shot[{i}] → {path.name}（{path.stat().st_size/1024:.0f} KB）")
        keyframes.append({"shot": s, "url": url, "path": str(path)})
    ok(f"全部 {len(keyframes)} 个关键帧生成完毕")
    return keyframes


# ===================== Phase 4: Animate =====================
def phase4_animate(key: str, keyframes: list, full: bool) -> list:
    banner("Phase 4 / Animate ── Seedance 把图变成视频")
    if not full:
        info("⚠️  当前是 stub 模式：复用已有 seedance_2_0_sample.mp4 充当全部 3 段")
        info("    要真跑 Seedance（每段 ~4 分钟）请加 --full")
        clips = []
        src = OUT_DIR / "seedance_2_0_sample.mp4"
        if not src.exists():
            raise RuntimeError("缺少 seedance_2_0_sample.mp4，先跑 test_05b 出片")
        for kf in keyframes:
            dst = WORK / f"04_clip_{kf['shot']['id']}.mp4"
            shutil.copy(src, dst)
            log("P4.stub", f"复制 → {dst.name}")
            clips.append(str(dst))
        ok(f"stub 完成 {len(clips)} 段")
        return clips

    clips = []
    for i, kf in enumerate(keyframes, 1):
        step(f"Animate shot {kf['shot']['id']}", i, len(keyframes))
        prompt = f"{kf['shot']['desc']}。{kf['shot'].get('camera', '')}"
        data = http_post(
            f"{get_ark_base()}/contents/generations/tasks",
            {
                "model": "doubao-seedance-2-0-260128",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": kf["url"]}},
                ],
            },
            key,
        )
        task_id = data["id"]
        log("P4.task", f"  task_id = {task_id}，开始轮询...")

        # 轮询出片
        deadline = time.time() + 600
        last_status = ""
        while time.time() < deadline:
            time.sleep(15)
            st = http_get(f"{get_ark_base()}/contents/generations/tasks/{task_id}", key)
            if st.get("status") != last_status:
                log("P4.poll", f"  status: {last_status} → {st.get('status')}")
                last_status = st.get("status")
            if st.get("status") == "succeeded":
                vurl = st.get("content", {}).get("video_url") or st.get("video_url")
                dst = WORK / f"04_clip_{kf['shot']['id']}.mp4"
                dst.write_bytes(urllib.request.urlopen(vurl, timeout=180).read())
                log("P4.dl", f"  下载完成 → {dst.name}（{dst.stat().st_size/1024/1024:.2f} MB）")
                clips.append(str(dst))
                break
            if st.get("status") == "failed":
                raise RuntimeError(f"Seedance 任务失败：{st}")
        else:
            raise TimeoutError(f"shot {kf['shot']['id']} 轮询超时")

    ok(f"实拍完成 {len(clips)} 段视频")
    return clips


# ===================== Phase 5: Compose =====================
def phase5_compose(clips: list, storyboard: dict) -> Path:
    banner("Phase 5 / Compose ── ffmpeg 串接 + 字幕")
    # 5.1 用 xfade 把 3 段串起来（每段假设 5s，过渡 0.5s）
    log("P5.plan", f"串接 {len(clips)} 段 5s 视频，0.5s crossfade")

    # 用临时方法：先把所有 clip concat 重编码（保证编码一致），再 xfade 太麻烦
    # 简化：用 concat demuxer 硬拼
    list_file = WORK / "_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{Path(c).name}'" for c in clips),
        encoding="utf-8",
    )
    log("P5.list", f"concat 列表 → {list_file.name}")

    raw_concat = WORK / "05a_concat.mp4"
    run_ffmpeg(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(raw_concat)],
        f"concat → {raw_concat.name}",
    )

    # 5.2 烧分镜字幕（每段开头 1.5s 显示 desc）
    # 简化：只显示一个总标题
    titled = WORK / "05b_titled.mp4"
    title = storyboard["shots"][0]["desc"][:24].replace("'", "")
    run_ffmpeg(
        [FFMPEG, "-y", "-i", str(raw_concat),
         "-vf",
         f"drawtext=text='{title}':fontsize=32:fontcolor=white:"
         "x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.5:boxborderw=8:"
         "enable='between(t,0,3)'",
         "-c:a", "copy", "-c:v", "libx264", "-preset", "ultrafast",
         str(titled)],
        f"烧字幕 → {titled.name}",
    )

    # 5.3 加 BGM（这里用 sine 模拟，将来换成 GenBGM）
    bgm = WORK / "05c_bgm.aac"
    run_ffmpeg(
        [FFMPEG, "-y", "-f", "lavfi",
         "-i", "sine=frequency=330:sample_rate=44100:duration=20",
         "-c:a", "aac", str(bgm)],
        "生成模拟 BGM",
    )
    final = WORK / "05_final.mp4"
    run_ffmpeg(
        [FFMPEG, "-y", "-i", str(titled), "-i", str(bgm),
         "-filter_complex",
         "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac",
         str(final)],
        f"BGM 混音 → {final.name}",
    )
    ok(f"成片 → {final.relative_to(OUT_DIR.parent.parent)}（{final.stat().st_size/1024/1024:.2f} MB）")
    return final


# ===================== Phase 6: Review =====================
def phase6_review(key: str, final: Path, storyboard: dict) -> str:
    banner("Phase 6 / Review ── 抽帧 + Doubao VLM 打分")
    frames_dir = WORK / "06_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()
    run_ffmpeg(
        [FFMPEG, "-y", "-i", str(final), "-vf", "fps=0.5",
         str(frames_dir / "f_%02d.jpg")],
        "抽帧（每 2s 一张）",
    )
    frames = sorted(frames_dir.glob("*.jpg"))
    log("P6.frames", f"抽出 {len(frames)} 帧")
    # 取最多 4 张做 VLM 评价（避免单请求过大）
    pick = frames[: min(4, len(frames))]

    # 把图转 base64 内嵌
    image_messages = []
    for fp in pick:
        b64 = base64.b64encode(fp.read_bytes()).decode()
        image_messages.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    prompt = (
        "下面是一段短片的若干帧画面。原本的剧本目标是：" +
        json.dumps(storyboard, ensure_ascii=False) +
        "。请从「角色一致性 / 镜头衔接 / 整体观感」三个维度各给 1-5 分，并用一句话总结。"
    )
    log("P6.req", f"VLM 评估，{len(pick)} 帧 + 文本")

    data = http_post(
        f"{get_ark_base()}/chat/completions",
        {
            "model": "doubao-seed-2-0-pro-260215",
            "messages": [{
                "role": "user",
                "content": image_messages + [{"type": "text", "text": prompt}],
            }],
            "max_tokens": 400,
        },
        key,
    )
    review = data["choices"][0]["message"]["content"].strip()
    log("P6.out", f"VLM 评价：")
    for ln in review.split("\n"):
        if ln.strip():
            info(f"   │ {ln.strip()[:120]}")

    (WORK / "06_review.txt").write_text(review, encoding="utf-8")
    ok(f"评价落盘 → 06_review.txt")
    return review


# ===================== Main =====================
START = time.time()


def main():
    global START
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="阶段 4 真跑 Seedance（慢）")
    parser.add_argument("--skip", nargs="*", default=[], help="跳过的阶段编号，如 --skip 4 6")
    args = parser.parse_args()
    skip = set(args.skip)

    START = time.time()
    info(f"=== Pipeline Demo · {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    info(f"工作目录：{WORK}")
    info(f"模式：{'FULL（真跑 Seedance）' if args.full else 'STUB（复用已有视频）'}")
    info(f"跳过：{skip or '无'}")

    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return 1

    storyboard, entity_url, keyframes, clips, final, review = (None,) * 6
    try:
        if "1" not in skip:
            storyboard = phase1_story(key)
        if "2" not in skip and storyboard:
            entity_url = phase2_entity(key)
        if "3" not in skip and storyboard and entity_url:
            keyframes = phase3_assets(key, storyboard, entity_url)
        if "4" not in skip and keyframes:
            clips = phase4_animate(key, keyframes, args.full)
        if "5" not in skip and clips:
            final = phase5_compose(clips, storyboard)
        if "6" not in skip and final:
            review = phase6_review(key, final, storyboard)
    except Exception as e:
        fail(f"流水线中断：{e}")
        return 2

    print("\n" + "=" * 70)
    print("  ✅ 全部完成")
    print("=" * 70)
    print(f"  总耗时：{time.time() - START:.1f}s")
    print(f"  产物目录：{WORK}")
    if final:
        print(f"  成片：{final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
