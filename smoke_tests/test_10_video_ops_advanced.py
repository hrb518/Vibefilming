"""Test 10: 视频高级处理（ffmpeg）

子测：
  10a. trim     —— 裁剪视频第 1-3 秒
  10b. setpts   —— 2 倍速 + 0.5 倍速
  10c. overlay  —— 画中画：clip_b 缩到右下角叠在 clip_a 上
  10d. fade     —— 头尾黑场（fade in 0.5s + fade out 0.5s）
  10e. amix     —— 双音轨混音：原片人声 + 生成的正弦波 BGM
  10f. portrait —— 横转竖（16:9 → 9:16，crop+scale 到 720x1280）

依赖：clip_a.mp4 / clip_b.mp4（test_09 产物）
"""
import shutil
import subprocess
from pathlib import Path
import imageio_ffmpeg

from _common import banner, ok, fail, info, OUT_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CLIP_A = OUT_DIR / "clip_a.mp4"
CLIP_B = OUT_DIR / "clip_b.mp4"

OUT_TRIM     = OUT_DIR / "adv_trim.mp4"
OUT_FAST     = OUT_DIR / "adv_fast2x.mp4"
OUT_SLOW     = OUT_DIR / "adv_slow0p5x.mp4"
OUT_PIP      = OUT_DIR / "adv_pip.mp4"
OUT_FADE     = OUT_DIR / "adv_fade.mp4"
OUT_BGM      = OUT_DIR / "adv_bgm_sine.aac"
OUT_AMIX     = OUT_DIR / "adv_amix.mp4"
OUT_PORTRAIT = OUT_DIR / "adv_portrait.mp4"


def run(cmd, timeout=180):
    info(f"$ ffmpeg {' '.join(str(c) for c in cmd[1:7])} ...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败：\n{r.stderr[-800:]}")
    return r


def _ensure_clips():
    if not (CLIP_A.exists() and CLIP_B.exists()):
        raise RuntimeError(f"缺少 clip_a/clip_b，请先跑 test_09_video_ops.py")


# ---------- 10a: trim ----------
def test_trim():
    banner("Test 10a: trim 裁剪（取 1-3 秒）")
    _ensure_clips()
    run([
        FFMPEG, "-y", "-ss", "1", "-to", "3", "-i", str(CLIP_A),
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
        str(OUT_TRIM)
    ])
    ok(f"裁剪成功 → {OUT_TRIM.name}（{OUT_TRIM.stat().st_size/1024:.0f} KB）")
    return True


# ---------- 10b: setpts 变速 ----------
def test_speed():
    banner("Test 10b: setpts 变速（2x 与 0.5x）")
    _ensure_clips()
    # 2x：视频 setpts=0.5*PTS，音频 atempo=2
    run([
        FFMPEG, "-y", "-i", str(CLIP_A),
        "-filter_complex", "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(OUT_FAST)
    ])
    ok(f"2 倍速 → {OUT_FAST.name}")
    # 0.5x：setpts=2*PTS，atempo=0.5
    run([
        FFMPEG, "-y", "-i", str(CLIP_A),
        "-filter_complex", "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(OUT_SLOW)
    ])
    ok(f"0.5 倍速 → {OUT_SLOW.name}")
    return True


# ---------- 10c: overlay 画中画 ----------
def test_overlay():
    banner("Test 10c: overlay 画中画（B 缩到 1/3 叠在 A 右下角）")
    _ensure_clips()
    run([
        FFMPEG, "-y", "-i", str(CLIP_A), "-i", str(CLIP_B),
        "-filter_complex",
        "[1:v]scale=iw/3:ih/3[pip];"
        "[0:v][pip]overlay=W-w-20:H-h-20[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "copy",
        str(OUT_PIP)
    ])
    ok(f"画中画成功 → {OUT_PIP.name}（{OUT_PIP.stat().st_size/1024/1024:.2f} MB）")
    return True


# ---------- 10d: fade 黑场 ----------
def test_fade():
    banner("Test 10d: fade 头尾黑场（0.5s in + 0.5s out）")
    _ensure_clips()
    # 视频 5s，淡出从 4.5s 开始
    run([
        FFMPEG, "-y", "-i", str(CLIP_A),
        "-vf", "fade=t=in:st=0:d=0.5,fade=t=out:st=4.5:d=0.5",
        "-af", "afade=t=in:st=0:d=0.5,afade=t=out:st=4.5:d=0.5",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(OUT_FADE)
    ])
    ok(f"黑场成功 → {OUT_FADE.name}")
    return True


# ---------- 10e: amix 多路混音 ----------
def test_amix():
    banner("Test 10e: amix 混音（原片对白 + 正弦波 BGM，BGM 音量 0.2）")
    _ensure_clips()
    # 1) 先生成一段 5s 的正弦波当 BGM
    run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=44100:duration=5",
        "-c:a", "aac", str(OUT_BGM)
    ])
    info(f"模拟 BGM → {OUT_BGM.name}")
    # 2) 把 BGM 混到 clip_a 的音轨上
    run([
        FFMPEG, "-y", "-i", str(CLIP_A), "-i", str(OUT_BGM),
        "-filter_complex",
        "[1:a]volume=0.2[bgm];"
        "[0:a][bgm]amix=inputs=2:duration=longest:dropout_transition=0[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac",
        str(OUT_AMIX)
    ])
    ok(f"混音成功 → {OUT_AMIX.name}")
    return True


# ---------- 10f: 横转竖 ----------
def test_portrait():
    banner("Test 10f: 横转竖（1280x720 → 720x1280，居中裁剪+缩放）")
    _ensure_clips()
    # 思路：从 16:9 中间裁出 9:16 区域（高度全用，宽度 = h*9/16 = 405），再缩到 720x1280
    run([
        FFMPEG, "-y", "-i", str(CLIP_A),
        "-vf", "crop=ih*9/16:ih,scale=720:1280,setsar=1",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "copy",
        str(OUT_PORTRAIT)
    ])
    ok(f"横转竖成功 → {OUT_PORTRAIT.name}")
    return True


SUBTESTS = [
    ("10a trim",     test_trim),
    ("10b 变速",      test_speed),
    ("10c 画中画",     test_overlay),
    ("10d 黑场",      test_fade),
    ("10e 混音",      test_amix),
    ("10f 横转竖",     test_portrait),
]


def main():
    info(f"ffmpeg 路径：{FFMPEG}")
    if not (CLIP_A.exists() and CLIP_B.exists()):
        fail(f"缺少前置素材，先跑 test_09_video_ops.py 生成 clip_a/clip_b")
        return False

    results = []
    for name, fn in SUBTESTS:
        try:
            r = bool(fn())
        except Exception as e:
            fail(f"异常：{e}")
            r = False
        results.append((name, r))

    print("\n" + "=" * 70)
    print("  视频高级处理测试汇总")
    print("=" * 70)
    for name, r in results:
        print(f"  {'✅' if r else '❌'}  {name}")
    n_ok = sum(1 for _, r in results if r)
    print(f"\n  {n_ok} / {len(results)} 通过")
    return n_ok == len(results)


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
