"""Test 7: 豆包·音乐 GenBGM（占位）。

走火山引擎签名 OpenAPI（AK/SK），不是 ARK Bearer。
当前未实现完整签名版本，先做凭证存在性检查 + 给出 TODO。
"""
from _common import banner, ok, fail, info, get_extra


def main():
    banner("Test 7: 豆包·音乐 GenBGM")
    ak = get_extra("VOLC_AK")
    sk = get_extra("VOLC_SK")

    if not ak or not sk:
        fail("缺少 VOLC_AK / VOLC_SK —— GenBGM 走火山引擎签名（AK/SK），需到「访问控制」生成密钥")
        info("文档：https://www.volcengine.com/docs/6489/")
        return False

    info("凭证已就绪。此测试需要实现 Volcengine V4 签名（HMAC-SHA256），TODO 中。")
    info("可走以下方式快速验证：")
    info("  a) 用官方 SDK（pip install volcengine） + GenBGMService")
    info("  b) 用 awscurl-volc / 自写签名")
    fail("尚未实现签名调用 —— 下一步加")
    return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
