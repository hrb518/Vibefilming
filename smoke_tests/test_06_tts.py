"""Test 6: 豆包大模型 TTS（HTTP 一次性接口）。

需要在 vibefilming.config.json 中填 tts.app_id / tts.access_token。
没填则跳过并报告"缺凭证"。
"""
import json
import uuid
import base64
import urllib.request
from _common import banner, ok, fail, info, get_extra, save_bytes


def main():
    banner("Test 6: 豆包 TTS 语音合成")
    app_id = get_extra("TTS_APP_ID")
    token = get_extra("TTS_ACCESS_TOKEN")
    cluster = get_extra("TTS_CLUSTER", "volcano_tts")
    voice = get_extra("TTS_VOICE", "BV001_streaming")

    if not app_id or not token:
        fail("缺少 tts.app_id / tts.access_token —— 请到「火山引擎控制台 → 语音技术 → 大模型语音合成」开通后，填到 vibefilming.config.json")
        return False

    url = "https://openspeech.bytedance.com/api/v1/tts"
    body = {
        "app": {"appid": app_id, "token": token, "cluster": cluster},
        "user": {"uid": "smoke_test"},
        "audio": {
            "voice_type": voice,
            "encoding": "mp3",
            "speed_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": "你好，这是一次冒烟测试。",
            "operation": "query",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer; {token}",  # 注意分号，是官方格式
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") == 3000 and data.get("data"):
            audio = base64.b64decode(data["data"])
            p = save_bytes("tts_sample.mp3", audio)
            ok(f"合成成功：{p}（{len(audio)} bytes）")
            return True
        fail(f"返回非成功：{data}")
        return False
    except Exception as e:
        fail(f"调用失败：{e}")
        info("可能原因：appid/token 无效 / 该音色未授权 / cluster 名错误")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
