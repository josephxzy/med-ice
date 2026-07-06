# -*- coding: utf-8 -*-
"""后端工厂。"""

from backends.alinlp import AlinlpBackend
from backends.llm import LlmBackend
from backends.ollama import OllamaBackend

_registry = {
    "alinlp": AlinlpBackend,
    "llm": LlmBackend,
    "ollama": OllamaBackend,
}


class BackendFactory:
    @staticmethod
    def create(name):
        cls = _registry.get(name)
        if not cls:
            raise ValueError(f"未知后端: {name}")
        return cls()

    @staticmethod
    def list_names():
        return list(_registry.keys())
