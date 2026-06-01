"""Test 9: 视频处理（ffmpeg）测试集

包含 4 个子测：
  9a. 准备第二段视频（如果只有一段，先用 reverse 造一段）
  9b. concat：硬拼接
  9c. crossfade：交叉溶解过渡
  9d. probe：取视频信息
  9e. extract_frames：抽帧（给 VLM 评估用）
  9f. burn_subtitles：烧字幕

依赖 imageio-ffmpeg（已装），不需要系统 brew ffmpeg。
"""
import os
import json
import shutil
import subprocess
from pathlib import Path
import imageio_ffmpeg

from _common import banner, ok, fail, info, OUT_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE = OUT_DIR / "seedance_2_0_sample.mp4"
CLIP_A = OUT_DIR / "clip_a.mp4"
CLIP_B = OUT_DIR / "clip_b.mp4"
CONCAT_OUT = OUT_DIR / "joined_concat.mp4"
XFADE_OUT = OUT_DIR / "joined_crossfade.mp4"
SUB_OUT = OUT_DIR / "with_subtitle.mp4"
FRAMES_DIR = OUT_DIR / "frames"


def run(cmd, timeout=120):
    """运行命令，失败时抛异常并把 stderr 带出来。"""
    info(f"$ {' '.join(str(c) for c in cmd[:6])} ...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败：\n{r.stderr[-800:]}")
    return r


def test_prepare():
    banner("Test 9a: 准备两段视频（A=原片，B=反向）")
    if not SAMPLE.exists():
        fail(f"找不到 {SAMPLE}，先跑 test_05b 出片")
        return False
    shutil.copy(SAMPLE, CLIP_A)
    ok(f"clip_a.mp4 ← 复制原片")
    # B 用 reverse 造一段视觉上不同的
    run([FFMPEG, "-y", "-i", str(SAMPLE), "-vf", "reverse", "-af", "areverse",
         "-c:v", "libx264", "-preset", "ultrafast", str(CLIP_B)])
    ok(f"clip_b.mp4 ← 反向版（{CLIP_B.stat().st_size/1024:.0f} KB）")
    return True


def test_probe():
    banner("Test 9b: 探测视频信息（ffprobe 等价）")
    # 用 ffmpeg -i 拿到 stderr 里的信息
    r = subprocess.run([FFMPEG, "-i", str(CLIP_A)], capture_output=True, text=True)
    out = r.stderr
    # 精简提取关键行
    for line in out.splitlines():
        if any(k in line for k in ["Duration", "Stream", "Video:", "Audio:"]):
            info(line.strip())
    ok("信息读取成功")
    return True


def test_concat():
    banner("Test 9c: concat 硬拼接（两段直接拼）")
    list_file = OUT_DIR / "_concat_list.txt"
    list_file.write_text(f"file '{CLIP_A.name}'\nfile '{CLIP_B.name}'\n", encoding="utf-8")
    # concat demuxer 需要在同目录跑
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(CONCAT_OUT)])
    if CONCAT_OUT.exists() and CONCAT_OUT.stat().st_size > 0:
        ok(f"拼接成功 → {CONCAT_OUT.name}（{CONCAT_OUT.stat().st_size/1024/1024:.2f} MB）")
        return True
    fail("产物为空")
    return False


def test_crossfade():
    banner("Test 9d: crossfade 交叉溶解（A 末 1s 与 B 头 1s 渐变）")
    # 假设两段都是 5s，A 在 4s 处开始与 B 渐变 1s
    # xfade filter 用 offset 指定 A 中开始过渡的时间
    run([
        FFMPEG, "-y",
        "-i", str(CLIP_A),
        "-i", str(CLIP_B),
        "-filter_complex",
        "[0:v][1:v]xfade=transition=fade:duration=1:offset=4[v];"
        "[0:a][1:a]acrossfade=d=1[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(XFADE_OUT)
    ], timeout=180)
    if XFADE_OUT.exists() and XFADE_OUT.stat().st_size > 0:
        ok(f"过渡成功 → {XFADE_OUT.name}（{XFADE_OUT.stat().st_size/1024/1024:.2f} MB）")
        return True
    fail("产物为空")
    return False


def test_extract_frames():
    banner("Test 9e: 抽帧（每秒 1 张，给 VLM 评估用）")
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir()
    run([FFMPEG, "-y", "-i", str(CLIP_A),
         "-vf", "fps=1", str(FRAMES_DIR / "frame_%03d.jpg")])
    n = len(list(FRAMES_DIR.glob("*.jpg")))
    if n > 0:
        ok(f"抽出 {n} 帧 → {FRAMES_DIR.name}/")
        return True
    fail("没抽到帧")
    return False


def test_burn_subtitles():
    banner("Test 9f: 烧录字幕（drawtext 直接画文字，无外部 srt）")
    run([
        FFMPEG, "-y", "-i", str(CLIP_A),
        "-vf",
        "drawtext=text='烟雾测试 - smoke test':fontsize=36:fontcolor=white:"
        "x=(w-text_w)/2:y=h-80:box=1:boxcolor=black@0.5:boxborderw=10",
        "-c:a", "copy", "-c:v", "libx264", "-preset", "ultrafast",
        str(SUB_OUT)
    ])
    if SUB_OUT.exists() and SUB_OUT.stat().st_size > 0:
        ok(f"字幕烧录成功 → {SUB_OUT.name}")
        return True
    fail("产物为空")
    return False


SUBTESTS = [
    ("9a 准备",       test_prepare),
    ("9b probe",     test_probe),
    ("9c concat",    test_concat),
    ("9d crossfade", test_crossfade),
    ("9e 抽帧",       test_extract_frames),
    ("9f 烧字幕",      test_burn_subtitles),
]


def main():
    info(f"ffmpeg 路径：{FFMPEG}")
    results = []
    for name, fn in SUBTESTS:
        try:
            r = bool(fn())
        except Exception as e:
            fail(f"异常：{e}")
            r = False
        results.append((name, r))

    print("\n" + "=" * 70)
    print("  视频处理测试汇总")
    print("=" * 70)
    for name, r in results:
        print(f"  {'✅' if r else '❌'}  {name}")
    n_ok = sum(1 for _, r in results if r)
    print(f"\n  {n_ok} / {len(results)} 通过")
    return n_ok == len(results)


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
