"""VibeFilming：影视短片 agent 的领域能力模块。

模块结构：
  workspace.py   项目工作区 / manifest.json 读写
  film_sdk.py    所有外部 API 封装（Doubao / Seedream / Seedance / ffmpeg）+ 内置 stub
  tools.py       工具适配层：把 SDK 包装成影视工具并注入运行时 handler

启用方式：
  python agentmain.py
"""
__all__ = ["workspace", "film_sdk", "tools"]
