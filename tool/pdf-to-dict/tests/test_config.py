# -*- coding: utf-8 -*-
"""ConfigManager 测试。"""

import json
import os
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.manager import ConfigManager


def test_load_defaults():
    cm = ConfigManager()
    assert cm.get("concurrency", "max_parallel_books") == 1
    assert cm.get("concurrency", "segment", "alinlp") == 20
    assert cm.get("text_segment", "backend") in ("alinlp", "llm", "ollama")
    decompose = cm.get("concurrency", "decompose")
    assert isinstance(decompose, int) and decompose > 0
    print("  OK test_load_defaults")


def test_get_set_reset():
    cm = ConfigManager()
    original = cm.get("concurrency", "decompose")

    cm.set("concurrency", "decompose", 99)
    assert cm.get("concurrency", "decompose") == 99

    cm.reset("concurrency")
    assert cm.get("concurrency", "decompose") == original
    print("  OK test_get_set_reset")


def test_dot_notation():
    cm = ConfigManager()
    cm.set("concurrency", "segment.llm", 999)
    assert cm.get("concurrency", "segment", "llm") == 999
    cm.reset("concurrency")
    print("  OK test_dot_notation")


if __name__ == "__main__":
    test_load_defaults()
    test_get_set_reset()
    test_dot_notation()
    print("\n全部通过")
