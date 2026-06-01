"""轮询上次提交的 Seedance 任务，等出片落地。"""
import json
import time
import urllib.request
from _common import banner, ok, fail, info, get_ark_key, get_ark_base, save_bytes

CANDIDATE_MODELS = [
    "doubao-seedance-2-0-260128",
    "doubao-seedance-2-0-fast-260128",
]


def submit(model, key):
    url = f"{get_ark_base()}/contents/generations/tasks"
    body = {
        "model": model,
        "content": [
            {"type": "text", "text": "一只橘猫在阳光下的窗台上慢慢回头看向镜头，电影感"}
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def query(task_id, key):
    url = f"{get_ark_base()}/contents/generations/tasks/{task_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    banner("Seedance 2.0 文生视频 - 完整轮询出片")
    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return False

    model = CANDIDATE_MODELS[0]
    info(f"使用 model = {model}")
    sub = submit(model, key)
    task_id = sub.get("id")
    ok(f"任务提交：{task_id}")

    deadline = time.time() + 480
    start = time.time()
    while time.time() < deadline:
        time.sleep(15)
        st = query(task_id, key)
        status = st.get("status")
        info(f"  status={status}  elapsed={int(time.time() - start)}s")
        if status == "succeeded":
            content = st.get("content") or {}
            video_url = content.get("video_url") or st.get("video_url")
            ok(f"出片成功：{video_url}")
            try:
                vid = urllib.request.urlopen(video_url, timeout=120).read()
                p = save_bytes("seedance_2_0_sample.mp4", vid)
                ok(f"已下载 → {p}（{len(vid)/1024/1024:.2f} MB）")
            except Exception as e:
                info(f"下载失败（不影响验证）：{e}")
            return True
        if status == "failed":
            fail(f"任务失败：{st}")
            return False

    fail("轮询超时（480s 仍未出片）")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
