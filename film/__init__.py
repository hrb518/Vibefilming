"""VibeFilming：基于 GenericAgent 的影视编辑 agent 扩展。

模块结构：
  workspace.py   项目工作区 / manifest.json 读写
  film_sdk.py    所有外部 API 封装（Doubao / Seedream / Seedance / ffmpeg）+ 内置 stub
  tools.py       GA 工具适配层：把 SDK 包装成 do_xxx 方法挂到 GenericAgentHandler

启用方式：
  python agentmain.py --mode=film     # CLI
  GA_MODE=film python frontends/tuiapp_v2.py  # TUI
"""
__all__ = ["workspace", "film_sdk", "tools"]
