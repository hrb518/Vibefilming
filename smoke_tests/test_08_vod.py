"""Test 8: VOD 视频点播（占位）。

VOD 走火山引擎签名 OpenAPI；当前先做凭证存在性检查，建议后续装官方 SDK。
"""
from _common import banner, ok, fail, info, get_extra


def main():
    banner("Test 8: VOD 视频点播")
    ak = get_extra("VOD_AK") or get_extra("VOLC_AK")
    sk = get_extra("VOD_SK") or get_extra("VOLC_SK")

    if not ak or not sk:
        fail("缺少 volc.ak / volc.sk —— VOD 走火山引擎签名（可与 volc.ak/sk 共用）")
        return False

    info("凭证已就绪。建议安装官方 SDK：pip install volcengine")
    info("再调 vod.GetSpaceList / vod.StartExecution 验证。")
    fail("尚未实现签名调用 —— 下一步加")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
