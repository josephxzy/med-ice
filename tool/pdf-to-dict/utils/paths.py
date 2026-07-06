# -*- coding: utf-8 -*-
"""全局路径常量，所有模块统一引用。"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IN_DIR = os.path.join(ROOT, "operate", "in")
OUT_DIR = os.path.join(ROOT, "operate", "out")

CONFIG_DIR = os.path.join(ROOT, "config")
CONFIG_DEFAULT = os.path.join(CONFIG_DIR, "default")
CONFIG_USER = os.path.join(CONFIG_DIR, "user")

TOKENIZER_DIR = os.path.join(ROOT, "tokenizer")
