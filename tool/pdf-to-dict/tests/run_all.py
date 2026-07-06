# -*- coding: utf-8 -*-
"""运行全部测试。"""

import subprocess
import sys
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

tests = [
    "test_config.py",
    "test_text.py",
    "test_backends.py",
    "test_orchestrator.py",
]

failed = 0
for t in tests:
    path = os.path.join(TESTS_DIR, t)
    print(f"\n{'=' * 40}\n  {t}\n{'=' * 40}")
    rc = subprocess.run([sys.executable, path]).returncode
    if rc != 0:
        failed += 1

print(f"\n{'=' * 40}")
print(f"  {'全部通过' if failed == 0 else f'{failed} 个失败'}")
