"""Test 2: Doubao VLM 多模态 —— 给一张公开图片让模型描述。"""
import json
import urllib.request
from _common import banner, ok, fail, info, get_ark_key, get_ark_base

# 用本地 Test 3 出的图（火山自己的 TOS），最稳；没有则用一张公开图
import base64
import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "outputs"
PUBLIC_FALLBACK = "https://ark-project.tos-cn-beijing.volces.com/doc_image/seed_i2v.png"


def _load_image_inline():
    """优先把本地图片转 base64 data URL，避免外网图被墙。"""
    for f in OUT_DIR.glob("seedream_*.png"):
        b = f.read_bytes()
        return "data:image/png;base64," + base64.b64encode(b).decode()
    return PUBLIC_FALLBACK


def main():
    banner("Test 2: Doubao VLM 视觉理解")
    key = get_ark_key()
    if not key:
        fail("缺少 ark.api_key")
        return False

    image_url = _load_image_inline()
    info(f"图源：{'本地 base64' if image_url.startswith('data:') else image_url}")

    url = f"{get_ark_base()}/chat/completions"
    body = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": "请用一句中文描述这张图。"},
            ],
        }],
        "max_tokens": 128,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]["content"]
        ok(f"VLM 描述：{msg.strip()[:120]}")
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        fail(f"HTTP {e.code}: {body[:300]}")
        info("可能原因：当前 model 不支持视觉 / 需要切换到 doubao-1.5-vision 或 doubao-vision 系")
        return False
    except Exception as e:
        fail(f"调用失败：{e}")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
