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
    up = f"待拆分词语：{word}"
    user_content = f"{sp}\n\n{up}" if sp else up
    messages = [{"role": "user", "content": user_content}]

    content, _ = chat_fn(
        messages,
        base_url=llm_config.get("base_url", ""),
        api_key=llm_config.get("api_key", ""),
        model=llm_config.get("model", ""),
        temperature=0.3,
        thinking=False)
    return _parse_decompose_result(content, word)


def decompose_batch(words, llm_config=None):
    """批量分解多个词条，单次 LLM 请求处理整批。"""
    if len(words) == 0:
        return {}
    if len(words) == 1:
        result = decompose(words[0], llm_config)
        return {words[0]: result} if result else {}

    chat_fn, full_cfg = _merge_config()
    if llm_config is None:
        llm_config = full_cfg.get("llm", {})
    else:
        full_cfg["llm"].update(llm_config)

    sp = full_cfg.get("system_prompt", "")
    items = "\n".join(f"{i+1}. {w}" for i, w in enumerate(words))
    up = f"对以下每个词条逐行回复结果（按编号顺序，每行一条）：\n{items}"
    user_content = f"{sp}\n\n{up}" if sp else up
    messages = [{"role": "user", "content": user_content}]

    content, _ = chat_fn(
        messages,
        base_url=llm_config.get("base_url", ""),
        api_key=llm_config.get("api_key", ""),
        model=llm_config.get("model", ""),
        temperature=0.3,
        thinking=False)

    # 按行解析
    results = {}
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    for line in lines:
        # 期望格式：编号: 结果  或  编号. 结果  或  编号 结果
        m = re.match(r'^(\d+)[:.\s]+(.+)$', line)
        if m:
            idx = int(m.group(1)) - 1
            rest = m.group(2).strip()
            if 0 <= idx < len(words):
                results[words[idx]] = _parse_decompose_result(rest, words[idx])

    # 补漏：未匹配的编号行，尝试按顺序映射
    if len(results) < len(words) and len(lines) == len(words):
        for i, line in enumerate(lines):
            w = words[i]
            if w not in results:
                results[w] = _parse_decompose_result(line, w)

    # 最终兜底：仍未覆盖的词条单独请求
    for w in words:
        if w not in results:
            results[w] = decompose(w, llm_config)

    return results


def _parse_decompose_result(content, word):
    content = content.strip()
    content = re.sub(r'[「」『』"\'<《》>]', '', content)

    drop = False
    if content.upper().startswith("DROP"):
        drop = True
        content = content[4:].strip()

    negations = {"不能", "不可拆分", "不可分割", "否"}
    if content in negations:
        return {"subs": [], "drop": False}

    subs = [w for w in content.split()
            if len(w) >= 2 and re.match(r'^[\u4e00-\u9fff]+$', w)
            and w != word and w not in negations]
    return {"subs": subs, "drop": drop}
