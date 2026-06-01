"""Test 1: Doubao 纯文本对话 —— 最基础健康检查。"""
import json
import urllib.request
from _common import banner, ok, fail, info, get_ark_key, get_ark_base


def main():
    banner("Test 1: Doubao 文本对话 (doubao-seed-2-0-pro)")
    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return False

    url = f"{get_ark_base()}/chat/completions"
    body = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [
            {"role": "user", "content": "用一句中文回答：你好。"}
        ],
        "max_tokens": 64,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]["content"]
        ok(f"模型回复：{msg.strip()[:80]}")
        return True
    except Exception as e:
        fail(f"调用失败：{e}")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
