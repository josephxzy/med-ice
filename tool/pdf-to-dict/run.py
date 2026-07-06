# -*- coding: utf-8 -*-
"""向后兼容入口。仅支持旧式 --flag 参数，新用法请使用 python main.py。

  python run.py                    →  python main.py run
  python run.py --phase 5          →  python main.py run --phase 5
  python run.py --repdf            →  python main.py run --repdf
  python run.py --set-backend X    →  python main.py config set text_segment backend X
  python run.py --test-nlp         →  python main.py test nlp
  python run.py --test-decompose   →  python main.py test decompose
  python run.py --reset-config     →  python main.py config reset
"""

import os
import subprocess
import sys

MAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")


def main():
    args = sys.argv[1:]

    if not args:
        subprocess.run([sys.executable, MAIN, "run"])
        return

    first = args[0]

    # --help / -h
    if first in ("--help", "-h"):
        print(__doc__)
        subprocess.run([sys.executable, MAIN, "--help"])
        return

    # --phase N
    if first == "--phase":
        cmd = [sys.executable, MAIN, "run", "--phase", args[1]]
        if "--repdf" in args:
            cmd.append("--repdf")
        subprocess.run(cmd)
        return

    # --repdf
    if first == "--repdf":
        subprocess.run([sys.executable, MAIN, "run", "--repdf"])
        return

    # --set-backend X
    if first == "--set-backend" and len(args) >= 2:
        subprocess.run([sys.executable, MAIN, "config", "set", "text_segment", "backend", args[1]])
        return

    # --test-nlp
    if first == "--test-nlp":
        subprocess.run([sys.executable, MAIN, "test", "nlp"])
        return

    # --test-decompose
    if first == "--test-decompose":
        subprocess.run([sys.executable, MAIN, "test", "decompose"])
        return

    # --reset-config
    if first == "--reset-config":
        subprocess.run([sys.executable, MAIN, "config", "reset"])
        return

    print(f"不支持: {args}")
    print("python run.py 仅支持 --flag 风格旧参数，新用法请使用 python main.py")
    sys.exit(1)


if __name__ == "__main__":
    main()
