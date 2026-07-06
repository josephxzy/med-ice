# -*- coding: utf-8 -*-
"""python main.py test nlp|decompose — 纯测试，不保存配置。"""

import json
import os
import re
import sys

from config.manager import ConfigManager
from backends.factory import BackendFactory
from utils.text import clean_text, chunk_text
from utils.paths import IN_DIR, OUT_DIR


def run(args):
    if args.test_mode == "nlp":
        _test_nlp(args)
    elif args.test_mode == "decompose":
        _test_decompose(args)


def _test_nlp(args):
    cm = ConfigManager()
    backend_name = args.backend or cm.get("text_segment", "backend") or "alinlp"

    if backend_name == "alinlp":
        cfg = cm.load("alinlp")
        ak_id = cfg.get("access_key_id") or input("Access Key ID: ")
        ak_secret = cfg.get("access_key_secret") or input("Access Key Secret: ")
        out_type = input("粒度 (0/1/2, 默认 1): ") or "1"
        config = {"access_key_id": ak_id, "access_key_secret": ak_secret, "out_type": out_type}
    elif backend_name == "llm":
        cfg = cm.load("text_segment")
        llm = cfg.get("llm", {})
        base_url = args.url or llm.get("base_url") or input("Base URL: ") or "https://api.deepseek.com"
        api_key = args.api_key or llm.get("api_key") or input("API Key: ")
        model = args.model or llm.get("model") or input("Model: ") or "deepseek-chat"
        config = {"base_url": base_url, "api_key": api_key, "model": model,
                   "system_prompt": llm.get("system_prompt", ""),
                   "user_prompt": llm.get("user_prompt", ""),
                   "thinking": llm.get("thinking", False)}
    elif backend_name == "ollama":
        cfg = cm.load("text_segment")
        ollama = cfg.get("ollama", {})
        host = ollama.get("host", "http://localhost:11434")
        model = ollama.get("model", "qwen2.5:1.5b")
        config = {"host": host, "model": model,
                   "prompt": ollama.get("prompt", "")}
    else:
        print(f"未知后端: {backend_name}")
        return

    backend = BackendFactory.create(backend_name)
    print(f"\n后端: {backend_name}")
    print("输入文本测试（回车退出）:")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            break
        try:
            words, tokens = backend.segment(text, config)
            valid = [w for w in words if len(w) >= 2]
            print(f"  {' '.join(valid)}")
            if tokens:
                print(f"  Token: {tokens}")
        except Exception as e:
            print(f"  错误: {e}")


def _test_decompose(args):
    cm = ConfigManager()
    cfg = cm.load("term_decompose")
    llm = cfg.get("llm", {})

    base_url = args.url or llm.get("base_url") or input("Base URL: ") or "https://api.deepseek.com"
    api_key = args.api_key or llm.get("api_key") or input("API Key: ")
    model = args.model or llm.get("model") or input("Model: ") or "deepseek-chat"

    # Import decompose logic
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pdf-to-dict/
    from pipeline.term_decompose import decompose

    llm_config = {"base_url": base_url, "api_key": api_key, "model": model,
                   "system_prompt": cfg.get("system_prompt", ""),
                   "user_prompt": cfg.get("user_prompt", "{}")}

    print(f"\n词条分解测试")
    print("输入 4+ 字中文词条测试（回车退出）:")

    while True:
        try:
            word = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not word:
            break
        if len(word) < 4:
            print("  需要 4 个字以上")
            continue
        try:
            subs = decompose(word, llm_config=llm_config)
            if subs:
                print(f"  可拆分: {' '.join(subs)}")
            else:
                print(f"  不可拆分")
        except Exception as e:
            print(f"  错误: {e}")
