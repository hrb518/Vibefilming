"""Test 5: Seedance 文生视频（异步任务）。

策略：只验证「提交任务 → 拿到 task_id → 查询一次状态」，不阻塞等出片，
出片成本高且耗时长，本 smoke 仅证明链路通。
"""
import json
import time
import urllib.request
from _common import banner, ok, fail, info, get_ark_key, get_ark_base

CANDIDATE_MODELS = [
    "doubao-seedance-2-0-260128",        # 标准（Pro 档质量）
    "doubao-seedance-2-0-fast-260128",   # Fast 档
    "doubao-seedance-1-0-pro-250528",    # 1.0 兜底
    "doubao-seedance-1-0-lite-t2v-250428",
]


def submit(model: str, key: str):
    url = f"{get_ark_base()}/contents/generations/tasks"
    body = {
        "model": model,
        "content": [
            {"type": "text", "text": "一只橘猫慢慢走过窗台 --resolution 480p --duration 5 --ratio 16:9"}
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


def query(task_id: str, key: str):
    url = f"{get_ark_base()}/contents/generations/tasks/{task_id}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    banner("Test 5: Seedance 文生视频（仅验证任务提交 + 一次状态查询）")
    key = get_ark_key()
    if not key:
        fail("缺少 ARK_API_KEY")
        return False

    last_err = None
    for m in CANDIDATE_MODELS:
        info(f"尝试 model = {m}")
        try:
            sub = submit(m, key)
            task_id = sub.get("id") or sub.get("task_id")
            if not task_id:
                info(f"返回里没有 task_id：{sub}")
                continue
            ok(f"任务已提交，task_id = {task_id}")
            time.sleep(2)
            st = query(task_id, key)
            ok(f"状态查询成功：status = {st.get('status')}")
            info("（出片需 1-3 分钟，本 smoke 不等待落地）")
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            last_err = f"HTTP {e.code}: {body[:300]}"
            info(f"失败：{last_err}")
        except Exception as e:
            last_err = str(e)
            info(f"失败：{e}")

    fail(f"Seedance 提交失败：{last_err}")
    info("可能原因：账号未开通视频生成 / 接口路径已变更（参考 Ark 文档『视频生成』）")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
