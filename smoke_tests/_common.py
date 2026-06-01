"""共享配置与工具函数。

凭证读取顺序：
1. 环境变量
2. 仓库根目录下的 mykey.py（已存在的 ARK key 自动复用）
3. 本目录下的 keys_extra.py（可选，用于 TTS/VOD/GenBGM 等）
"""
import os
import sys
import json
import time
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)


def _load_module(path: Path, name: str):
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mykey = _load_module(ROOT / "mykey.py", "mykey")
_extra = _load_module(Path(__file__).resolve().parent / "keys_extra.py", "keys_extra")


def get_ark_key() -> str:
    return (
        os.environ.get("ARK_API_KEY")
        or (getattr(_mykey, "native_oai_config", {}).get("apikey") if _mykey else None)
        or ""
    )


def get_ark_base() -> str:
    return (
        os.environ.get("ARK_API_BASE")
        or (getattr(_mykey, "native_oai_config", {}).get("apibase") if _mykey else None)
        or "https://ark.cn-beijing.volces.com/api/v3"
    )


def get_extra(name: str, default=None):
    """读取额外凭证：先环境变量，再 keys_extra.py"""
    if name in os.environ:
        return os.environ[name]
    if _extra and hasattr(_extra, name):
        return getattr(_extra, name)
    return default


def banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def ok(msg: str):
    print(f"  ✅ {msg}")


def fail(msg: str):
    print(f"  ❌ {msg}")


def info(msg: str):
    print(f"  ℹ️  {msg}")


def save_json(name: str, data):
    p = OUT_DIR / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def save_bytes(name: str, data: bytes):
    p = OUT_DIR / name
    p.write_bytes(data)
    return p
