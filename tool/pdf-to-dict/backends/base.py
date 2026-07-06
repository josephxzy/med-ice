# -*- coding: utf-8 -*-
"""后端抽象基类。"""

from abc import ABC, abstractmethod


class AbstractBackend(ABC):
    """分词后端接口。"""

    @property
    @abstractmethod
    def name(self):
        """后端标识名：alinlp / llm / ollama"""
        ...

    @abstractmethod
    def segment(self, text, config):
        """分词一段文本，返回 (词列表, token 用量)。"""
        ...
