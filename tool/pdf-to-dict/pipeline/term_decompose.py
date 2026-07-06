# -*- coding: utf-8 -*-
"""
AI 词条分解 — 调用 AI 控制器判断 4+ 字词是否可拆分为独立子词。
"""

import importlib
import json
import os
import re

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(SCRIPTS_DIR, "config")
DEFAULT_FILE = os.path.join(CONFIG_DIR, "default", "term_decompose.json")
USER_FILE = os.path.join(CONFIG_DIR, "user", "term_decompose.json")


def _merge_config():
    cfg = {}
    if os.path.exists(DEFAULT_FILE):
        with open(DEFAULT_FILE, "r") as f:
            cfg = json.load(f)
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
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


def decompose(word, llm_config=None):
    chat_fn, full_cfg = _merge_config()
    if llm_config is None:
        llm_config = full_cfg.get("llm", {})
    else:
        full_cfg["llm"].update(llm_config)

    sp = full_cfg.get("system_prompt", "")
    up = full_cfg.get("user_prompt", "判断'{word}'可否拆分。").format(word=word)

    # 将规则合并到单条 user 消息中（小模型关 thinking 后不尊重 system prompt）
    user_content = up
    if sp:
        user_content = f"{sp}\n\n待拆分词语：{up}"
    messages = [{"role": "user", "content": user_content}]

    content, _ = chat_fn(
        messages,
        base_url=llm_config.get("base_url", ""),
        api_key=llm_config.get("api_key", ""),
        model=llm_config.get("model", ""),
        temperature=0.3,
        thinking=False)
    content = content.strip()
    # 剥离括号
    content = re.sub(r'[「」『』"\'<《》>]', '', content)
    # 不可拆分的否定回复（整个或任意 token）
    negations = {"不能", "不可拆分", "不可分割", "否"}
    if content in negations:
        return []
    # 提取所有 ≥2 字纯中文 token，排除否定词和原词
    subs = [w for w in content.split()
            if len(w) >= 2 and re.match(r'^[\u4e00-\u9fff]+$', w)
            and w != word and w not in negations]
    return subs
