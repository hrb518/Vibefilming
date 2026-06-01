"""Test 4: SeedEdit 图编辑（依赖 Test 3 的产出图，没有则用公开图）。"""
import json
import urllib.request
from pathlib import Path
from _common import banner, ok, fail, info, get_ark_key, get_ark_base, OUT_DIR

# 多个候选名 + 兜底：用 Seedream-4 自身做"image2image"
CANDIDATE_MODELS = [
    "doubao-seededit-3-0-i2i-250628",
    "doubao-seededit-3-0-i2i",
    "doubao-seedream-4-0-250828",  # 4.0 自带图编辑能力，作为兜底
]

FALLBACK_IMAGE = "https://ark-project.tos-cn-beijing.volces.com/doc_image/seed_i2v.png"


def main():
    banner("Test 4: SeedEdit 图编辑")
    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return False

    # 优先使用 Test 3 缓存的 Seedream URL（在火山 TOS 上，最稳）
    ref_url = None
    cache = OUT_DIR / "last_seedream_url.txt"
    if cache.exists():
        u = cache.read_text(encoding="utf-8").strip()
        if u:
            ref_url = u
    if not ref_url:
        info("未找到 Test 3 出的图，先跑 test_03_seedream_t2i.py 再来。")
        fail("无可用参考图")
        return False
    info(f"参考图：{ref_url[:80]}...")

    url = f"{get_ark_base()}/images/generations"
    last_err = None
    for m in CANDIDATE_MODELS:
        info(f"尝试 model = {m}")
        body = {
            "model": m,
            "prompt": "把背景改成蓝天白云",
            "image": ref_url,
            "size": "1024x1024",
            "response_format": "url",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            out = data["data"][0].get("url")
            ok(f"编辑成功：{out}")
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            last_err = f"HTTP {e.code}: {body[:300]}"
            info(f"失败：{last_err}")
        except Exception as e:
            last_err = str(e)
            info(f"失败：{e}")

    fail(f"SeedEdit 失败：{last_err}")
    info("可能原因：模型未开通 / 参数名变化")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
