# -*- coding: utf-8 -*-
"""LLM 分词后端（DeepSeek / OpenAI 兼容 API）。"""

import json
import urllib.error
import urllib.request

from backends.base import AbstractBackend


class LlmBackend(AbstractBackend):
    name = "llm"

    def segment(self, text, config):
        base_url = config.get("base_url", "https://api.deepseek.com")
        api_key = config.get("api_key", "")
        model = config.get("model", "deepseek-chat")

        if not api_key:
            raise ValueError("缺少 LLM api_key")

        system_prompt = config.get("system_prompt", "你是中文分词器。")
        user_prompt = config.get("user_prompt", "分词：{text}").format(text=text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        content, tokens = self._chat(
            messages,
            base_url=base_url,
            api_key=api_key,
            model=model,
            thinking=config.get("thinking", False),
            reasoning_effort=config.get("reasoning_effort", "high"),
        )
        return content.split(), tokens

    def _chat(self, messages, *, base_url, api_key, model,
              thinking=False, reasoning_effort="high", max_tokens=10240):
        url = f"{base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if thinking:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = reasoning_effort
        else:
            payload["thinking"] = {"type": "disabled"}
            payload["temperature"] = 0.3

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}")
        except Exception as e:
            raise Exception(f"请求失败: {e}")

        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            raw = data["choices"][0]["message"].get("reasoning_content", "")
            if raw:
                content = raw.strip()
        if not content:
            finish = data["choices"][0].get("finish_reason", "?")
            raise Exception(f"返回空 (finish_reason={finish})")
        usage = data.get("usage", {})
        return content, usage.get("total_tokens", 0)
