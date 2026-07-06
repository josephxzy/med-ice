# -*- coding: utf-8 -*-
"""
DeepSeek 控制器 — 纯 chat 调用 + tokenizer，不读配置。

调用者负责提供全部参数（base_url, api_key, model）。
缺少必须参数时抛出 ValueError。
"""

import json
import os
import urllib.request
import urllib.error

CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CONTROLLER_DIR)
TOKENIZER_DIR = os.path.join(ROOT_DIR, "tokenizer")

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None and os.path.isdir(TOKENIZER_DIR):
        try:
            import transformers
            _tokenizer = transformers.AutoTokenizer.from_pretrained(
                TOKENIZER_DIR, trust_remote_code=True)
        except Exception:
            pass
    return _tokenizer


def count_tokens(text):
    t = _get_tokenizer()
    return len(t.encode(text)) if t else 0


def chat(messages, *, base_url, api_key, model,
         thinking=False, reasoning_effort="high", max_tokens=10240,
         temperature=None):
    """DeepSeek Chat 调用。所有参数由调用者提供。

    Raises:
        ValueError: base_url, api_key 或 model 为空。
    """
    if not base_url:
        raise ValueError("缺少 base_url")
    if not api_key:
        raise ValueError("缺少 api_key")
    if not model:
        raise ValueError("缺少 model")

    url = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }
    if thinking:
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = reasoning_effort
    else:
        payload["thinking"] = {"type": "disabled"}
        if temperature is not None:
            payload["temperature"] = temperature
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        if e.code == 429:
            raise Exception(f"DeepSeek HTTP 429 (rate limit): {body}")
        raise Exception(f"DeepSeek HTTP {e.code}: {body}")
    except Exception as e:
        raise Exception(f"DeepSeek 请求失败: {e}")

    content = data["choices"][0]["message"]["content"].strip()
    if not content:
        raw = data["choices"][0]["message"].get("reasoning_content", "")
        if raw:
            content = raw.strip()
    if not content:
        finish = data["choices"][0].get("finish_reason", "?")
        raise Exception(f"DeepSeek 返回空 (finish_reason={finish})")
    usage = data.get("usage", {})
    return content, usage.get("total_tokens", 0)
