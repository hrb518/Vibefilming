"""VibeFilming 命令行入口。"""
import os, sys, subprocess, argparse

# Windows GBK 终端兼容
if sys.platform == "win32" and sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "gb2312"):
    sys.stdout.reconfigure(errors="replace") if hasattr(sys.stdout, "reconfigure") else None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def run_command(cmd, extra=None):
    full_cmd = [part.replace("{PROJECT_DIR}", PROJECT_DIR) for part in cmd]
    if extra:
        full_cmd.extend(extra)
    print(f"🚀 {' '.join(full_cmd)}")
    sys.stdout.flush()
    os.chdir(PROJECT_DIR)
    proc = subprocess.Popen(full_cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        sys.exit(0)


def cmd_status():
    """检查进程状态"""
    import psutil
    running = [p for p in psutil.process_iter(['pid', 'name', 'cmdline'])
               if p.info['cmdline'] and any('agentmain' in c for c in p.info['cmdline'])]
    if running:
        print(f"🟢 运行中: {len(running)} 个进程")
        for p in running:
            print(f"   PID {p.info['pid']} — {' '.join(p.info['cmdline'][:3])}")
    else:
        print("⚫ VibeFilming 进程未运行")


def cmd_update():
    """git pull + pip install"""
    os.chdir(PROJECT_DIR)
    print("🔄 git pull...")
    r = subprocess.run(["git", "pull"], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
    print("📦 pip install...")
    r2 = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."],
                        capture_output=True, text=True)
    print(r2.stdout[-500:] if r2.stdout else "")
    if r2.returncode != 0:
        print(r2.stderr[-500:])


def main():
    parser = argparse.ArgumentParser(
        prog="vibefilming",
        description="VibeFilming 命令行入口",
    )
    parser.add_argument("command", nargs="?", choices=["run", "feishu", "status", "update"],
                        help="run=启动 CLI；feishu=启动飞书机器人；status=检查进程；update=更新依赖")
    parser.add_argument("args", nargs="*", help="子命令参数")
    parser.add_argument("-v", "--version", action="store_true", help="显示版本")

    args, unknown = parser.parse_known_args()

    if args.version:
        print("VibeFilming v0.1.0")
        return

    cmd = args.command or "run"
    if cmd == "help":
        parser.print_help()
        return

    if cmd == "status":
        cmd_status()
        return

    if cmd == "update":
        cmd_update()
        return

    extra = list(args.args) + unknown
    if cmd == "feishu":
        run_command([sys.executable, "{PROJECT_DIR}/frontends/fsapp.py"], extra)
    else:
        run_command([sys.executable, "{PROJECT_DIR}/agentmain.py"], extra)


if __name__ == "__main__":
    main()
