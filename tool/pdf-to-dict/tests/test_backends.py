# -*- coding: utf-8 -*-
"""Backend 工厂测试。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backends.factory import BackendFactory
from backends.base import AbstractBackend


def test_list_names():
    names = BackendFactory.list_names()
    assert "alinlp" in names
    assert "llm" in names
    assert "ollama" in names
    print("  OK test_list_names")


def test_create():
    for name in BackendFactory.list_names():
        b = BackendFactory.create(name)
        assert isinstance(b, AbstractBackend)
        assert b.name == name
    print("  OK test_create")


def test_invalid():
    try:
        BackendFactory.create("invalid")
        assert False, "should raise"
    except ValueError:
        pass
    print("  OK test_invalid")


if __name__ == "__main__":
    test_list_names()
    test_create()
    test_invalid()
    print("\n全部通过")
