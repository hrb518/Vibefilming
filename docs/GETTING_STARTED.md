# 🚀 新手上手指南

> 完全没接触过编程也没关系，跟着做就行。Mac / Windows 都适用。
>
> 如果你已经有 Python 环境，直接跳到[第 2 步](#2-配置-api-key)。

---

## 1. 安装 Python

### Mac

打开「终端」（启动台搜索 "终端" 或 "Terminal"），粘贴这行命令然后回车：

```bash
brew install python
```

如果提示 `brew: command not found`，说明还没装 Homebrew，先粘贴这行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

装完后再执行 `brew install python`。

### Windows

1. 打开 [python.org/downloads](https://www.python.org/downloads/)，点黄色大按钮下载
2. 运行安装包，**底部的 "Add Python to PATH" 一定要勾上**
3. 点 "Install Now"

### 验证

终端 / 命令提示符里输入：

```bash
python3 --version
```

看到 `Python 3.x.x` 就 OK。Windows 上也可以试 `python --version`。

> ⚠️ **版本提示**：推荐 **Python 3.11 或 3.12**。不要使用 3.14（与 pywebview 等依赖不兼容）。

---

## 2. 配置 API Key

### 获取项目

从发布包或内部仓库获取 VibeFilming 项目，解压或 clone 到你喜欢的位置。

### 创建配置文件

进入项目文件夹，把 `vibefilming.config.example.json` 复制一份，重命名为 `vibefilming.config.json`。

用任意文本编辑器打开 `vibefilming.config.json`，填入你的 API 信息。VibeFilming 默认使用豆包 ARK 作为 Agent 思考模型、VLM 审片模型、Seedream 生图和 Seedance 生视频入口。

> 💡 详细字段说明见 `vibefilming.config.example.json`。

### 配置示例

**最常见的用法：**

```json
{
  "ark": {
    "api_key": "ark-你的密钥",
    "models": {
      "text": "doubao-seed-2-0-pro-260215",
      "vlm": "doubao-seed-2-0-pro-260215",
      "image": "doubao-seedream-4-5-251128",
      "video": "doubao-seedance-2-0-260128"
    }
  }
}
```

```json
{
  "volc": {
    "ak": "AKLT...",
    "sk": "..."
  }
}
```

> 💡 想把 Seedream 4.5 换成 5.0 lite，就改 `ark.models.image` 为你已开通的模型 ID。

### 关键规则

必须开通的 ARK 模型：

| 模型 | 用途 |
|---|---|
| `doubao-seed-2-0-pro-260215` | Agent 思考、文本、VLM 图片/视频理解 |
| `doubao-seedream-4-5-251128` | 文生图 / 图编辑 |
| `doubao-seedance-2-0-260128` | 文生视频 |

---

## 3. 初次启动

终端里进入项目文件夹，运行：

```bash
cd 你的解压路径
python3 agentmain.py
```

这就是**命令行模式**，已经可以用了。你会看到一个输入提示符，直接打字发送任务即可。

试试你的第一个任务：

```
生成一段 30 秒的宠物公益小视频
```

> 💡 Windows 上如果 `python3` 不识别，换成 `python agentmain.py`。

---

## 4. 安装依赖

先安装基础依赖：

```bash
pip install -e .
```

如果要使用飞书机器人入口，再安装飞书依赖：

```bash
pip install -e ".[feishu]"
```

> ⚠️ 如果遇到网络问题导致 Agent 无法调用 API，可能需要先手动装一个包：
> ```bash
> pip install requests
> ```

### 可选：飞书机器人入口

飞书入口配置见 [SETUP_FEISHU.md](./SETUP_FEISHU.md)。桌面端暂不作为发布入口。

## 5. 能力解锁

环境跑起来之后，你可以逐步解锁更多能力。每一项都只需要**对 Agent 说一句话**：

### 基础能力

| 能力 | 对 Agent 说 | 说明 |
|------|-----------|------|
| **PowerShell 脚本执行** | `帮我解锁当前用户的 PowerShell ps1 执行权限` | Windows 默认禁止运行 .ps1 脚本 |
| **全局文件搜索** | `安装并配置 Everything 命令行工具进 PATH` | 毫秒级全盘文件搜索 |

### 浏览器自动化

| 能力 | 对 Agent 说 | 说明 |
|------|-----------|------|
| **Web 工具解锁** | `执行 web setup sop，解锁 web 工具` | 注入浏览器插件，使 Agent 能直接操控网页 |

解锁后，Agent 可以在**保留你登录态**的真实浏览器中操作：

```
打开淘宝，搜索 iPhone 16，按价格排序
去 B 站，查看我最近看过的历史视频
```

### 进阶能力

| 能力 | 对 Agent 说 | 说明 |
|------|-----------|------|
| **OCR** | `用rapidocr配置你的ocr能力并存入记忆` | 让 Agent 能"看到"屏幕文字 |
| **屏幕视觉** | `仿造你的llmcore，写个调用vision的能力并存入记忆` | 让 Agent 能"看到"屏幕内容 |
| **移动端控制** | `配置 ADB 环境，准备连接安卓设备` | 通过 USB/WiFi 控制 Android 手机 |

### 聊天平台接入（可选）

接入后可以随时随地通过手机给电脑上的 Agent 发指令。

对 Agent 说：`看你的代码，帮我配置 XX 平台的机器人接入`

支持的平台：**微信个人Bot** / QQ / 飞书 / 企业微信 / 钉钉 / Telegram

> Agent 会自动读取代码、引导你完成配置。

### 高级模式

以下模式全部**自文档化**——不用查手册，直接问 Agent 即可：

| 模式 | 对 Agent 说 |
|------|------------|
| **Reflect（反射）** | `查看你的代码，告诉我你的 reflect 模式怎么启用` |
| **计划任务** | `查看你的代码，告诉我你的计划任务模式怎么启用` |
| **Plan（规划）** | `查看你的代码，告诉我你的 plan 模式怎么启用` |
| **SubAgent（子代理）** | `查看你的代码，告诉我你的 subagent 模式怎么启用` |
| **自主探索** | `查看你的代码，告诉我你的自主探索模式怎么启用` |

> 💡 这就是 VibeFilming 的核心设计理念：**代码即文档**。Agent 能读懂自己的源码，所以任何功能你都可以直接问它。

---

## 💡 使用越久越强

VibeFilming 不预设技能，而是**靠使用进化**。每完成一个新任务，它会自动将执行路径固化为 Skill，下次遇到类似任务直接调用。

你不需要管理这些 Skill，Agent 会自动处理。使用时间越长，积累的技能越多，最终形成一棵完全属于你的专属技能树。

> 💡 如果你觉得某些重要信息 Agent 没有记住，可以直接告诉它：`把这个记到你的记忆里`，它会主动记忆。

**其他 Claw 的 Skill 也可以直接复用：**

- 让 Agent 搜索：`帮我找个做 XXX 的 skill` → 完成后 → `加入你的记忆中`
- 直接指定来源：`访问 XXX 文件夹/URL，按照这个 skill 做 XXX`

**保持更新：**

对 Agent 说：`git 更新你的代码，然后看看 commit 有什么新功能`

> Agent 会自动 pull 最新代码并解读 commit log，告诉你新增了什么能力。

> 更多细节请参阅 [README.md](../README.md) 或 [详细版图文教程](https://my.feishu.cn/wiki/CGrDw0T76iNFuskmwxdcWrpinPb)。
