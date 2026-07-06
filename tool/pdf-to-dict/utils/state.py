# -*- coding: utf-8 -*-
""".pipeline_state.json 读写 — 子进程向主进程汇报进度的 IPC 机制。

双文件交替 + 指针文件：writer 和 reader 永不操作同一个文件。
"""

import json
import os
import time


def _rotate_write(state_path, data):
    """写入状态：选择另一槽位 → 写 .tmp → rename → 更新指针。"""
    ptr_path = state_path + ".ptr"
    cur = "0"
    try:
        if os.path.exists(ptr_path):
            with open(ptr_path, "r") as f:
                cur = f.read().strip() or "0"
    except Exception:
        pass
    nxt = "1" if cur == "0" else "0"

    target = f"{state_path}.{nxt}.json"
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, target)

    ptr_tmp = ptr_path + ".tmp"
    with open(ptr_tmp, "w") as f:
        f.write(nxt)
    os.replace(ptr_tmp, ptr_path)


def write(state_path, **fields):
    """写入状态文件。字段会被更新，未提供的字段保持不变。"""
    state = read(state_path)
    state.update(fields)
    state["updated_at"] = time.time()
    _rotate_write(state_path, state)


def safewrite(state_path, state_dict):
    """直接写入完整 state dict（替代 inline json.dump + os.replace）。"""
    state_dict["updated_at"] = time.time()
    _rotate_write(state_path, state_dict)


def read(state_path):
    """读取状态文件（通过指针文件定位当前槽位）。"""
    ptr_path = state_path + ".ptr"
    if not os.path.exists(ptr_path):
        return {}
    try:
        with open(ptr_path, "r") as f:
            cur = f.read().strip() or "0"
    except Exception:
        return {}
    target = f"{state_path}.{cur}.json"
    if not os.path.exists(target):
        return {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def remove(state_path):
    """清理所有状态文件。"""
    for suffix in (".0.json", ".1.json", ".0.json.tmp", ".1.json.tmp", ".ptr", ".ptr.tmp",
                   ".json", ".json.tmp", ".state.json", ".state.json.tmp"):
        p = state_path + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
