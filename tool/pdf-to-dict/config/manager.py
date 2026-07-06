# -*- coding: utf-8 -*-
"""ConfigManager — 统一的配置加载、合并、保存。

用法：
    cm = ConfigManager()
    backend = cm.get("text_segment", "backend")
    cm.set("text_segment", "backend", "llm")
    cm.reset("text_segment")
"""

import json
import os

from utils.paths import CONFIG_DEFAULT, CONFIG_USER


class ConfigManager:
    """管理 config/default/ 和 config/user/ 的合并读写。"""

    def __init__(self):
        self._cache = {}

    # ---- 内部 ----

    def _default_path(self, name):
        return os.path.join(CONFIG_DEFAULT, f"{name}.json")

    def _user_path(self, name):
        return os.path.join(CONFIG_USER, f"{name}.json")

    def _read_json(self, path):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _deep_merge(self, base, override):
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def _diff(self, user, default):
        """只保留与默认不同的字段。"""
        if not isinstance(user, dict) or not isinstance(default, dict):
            return user if user != default else None
        result = {}
        for k, v in user.items():
            if k not in default:
                result[k] = v
            else:
                r = self._diff(v, default[k])
                if r is not None:
                    result[k] = r
        return result if result else None

    # ---- 公共 API ----

    def load(self, name):
        """加载合并后的配置（default + user）。带缓存。"""
        if name in self._cache:
            return self._cache[name]

        default = json.loads(json.dumps(self._read_json(self._default_path(name))))
        user = self._read_json(self._user_path(name))
        self._deep_merge(default, user)
        self._cache[name] = default
        return default

    def get(self, name, *keys):
        """便捷取值：cm.get('text_segment', 'llm', 'model')"""
        cfg = self.load(name)
        for k in keys:
            if isinstance(cfg, dict):
                cfg = cfg.get(k)
            else:
                return None
        return cfg

    def set(self, name, key, value):
        """设置用户配置项（写入 config/user/）。"""
        cfg = self.load(name)
        default = self._read_json(self._default_path(name))

        # 读现有用户配置
        user = self._read_json(self._user_path(name))

        # 按路径设置
        keys = key.split(".")
        target = user
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

        # 写 delta
        delta = self._diff(user, default)
        user_path = self._user_path(name)
        os.makedirs(os.path.dirname(user_path), exist_ok=True)
        if delta:
            with open(user_path, "w", encoding="utf-8") as f:
                json.dump(delta, f, ensure_ascii=False, indent=2)
        else:
            if os.path.exists(user_path):
                os.remove(user_path)

        # 刷新缓存
        self._cache.pop(name, None)

    def reset(self, name):
        """删除用户配置，恢复默认。"""
        user_path = self._user_path(name)
        if os.path.exists(user_path):
            os.remove(user_path)
        self._cache.pop(name, None)

    def reset_all(self):
        """删除全部用户配置。"""
        for f in os.listdir(CONFIG_USER):
            if f.endswith(".json"):
                os.remove(os.path.join(CONFIG_USER, f))
        self._cache.clear()

    def show(self, name):
        """打印合并后的配置。"""
        cfg = self.load(name)
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
