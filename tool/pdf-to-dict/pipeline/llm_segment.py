# -*- coding: utf-8 -*-
"""
AI 文本分词 — 调用 AI 控制器将医学文本切分为词语。
"""

import importlib
import json
import os

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(SCRIPTS_DIR, "config")
DEFAULT_FILE = os.path.join(CONFIG_DIR, "default", "text_segment.json")
USER_FILE = os.path.join(CONFIG_DIR, "user", "text_segment.json")


def _merge_config():
    cfg = {}
    if os.path.exists(DEFAULT_FILE):
        with open(DEFAULT_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
    llm = cfg.get("llm", {})
    provider = llm.get("provider", "deepseek")
    ctrl = importlib.import_module(f"pipeline.{provider}_controller")
    return ctrl.chat, cfg


def segment(text, llm_config=None):
    """分词一段文本，返回 (词列表, token 用量)。"""
    if llm_config is None:
        _, full_cfg = _merge_config()
        llm_config = full_cfg.get("llm", {})
        sp = full_cfg.get("system_prompt", "你是中文分词器。")
        up = full_cfg.get("user_prompt", "分词：{text}").format(text=text)
    else:
        sp = llm_config.get("system_prompt", "你是中文分词器。")
        up = llm_config.get("user_prompt", "分词：{text}").format(text=text)

    chat_fn, _ = _merge_config()
    content, tokens = chat_fn(
        [{"role": "system", "content": sp}, {"role": "user", "content": up}],
        base_url=llm_config.get("base_url", ""),
        api_key=llm_config.get("api_key", ""),
        model=llm_config.get("model", ""),
        thinking=llm_config.get("thinking", False),
        reasoning_effort=llm_config.get("reasoning_effort", "high"),
        temperature=None if llm_config.get("thinking") else 0.3)
    return content.split(), tokens
