# -*- coding: utf-8 -*-
"""Ollama 本地分词后端。"""

import json
import urllib.request

from backends.base import AbstractBackend


class OllamaBackend(AbstractBackend):
    name = "ollama"

    def segment(self, text, config):
        host = config.get("host", "http://localhost:11434")
        model = config.get("model", "qwen2.5:1.5b")
        prompt_template = config.get("prompt", "将以下医学文本分词，空格分隔，只输出分词结果。\n{text}")

        body = json.dumps({
            "model": model,
            "prompt": prompt_template.format(text=text),
            "stream": False,
            "options": {"temperature": 0},
        }).encode("utf-8")

        req = urllib.request.Request(f"{host}/api/generate", data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise Exception(f"Ollama 请求失败: {e}")

        content = data.get("response", "").strip()
        return content.split(), data.get("eval_count", 0)
