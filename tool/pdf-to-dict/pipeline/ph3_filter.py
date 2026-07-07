# -*- coding: utf-8 -*-
"""
词条过滤器 - pdf-to-dict 词库质量控制

读取词频 JSON，按 config/default/filter.json（可被 config/user/filter.json 覆盖）的规则过滤后输出。

过滤规则按顺序执行：
  1. 长度限制（min / max）
  2. 停用词排除
  3. 正则排除规则（exclude）
  4. 正则包含规则（include）
  5. require_cjk：必须包含至少一个汉字

用法：
  python ph3_filter.py terms.json -o filtered_terms.json
  python ph3_filter.py terms.json -o filtered_terms.json --config my_rules.json
"""

import argparse
import json
import os
import re
import sys

FILTER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(FILTER_DIR)
DEFAULT_FILTER = os.path.join(PROJECT_DIR, "config", "default", "filter.json")
USER_FILTER = os.path.join(PROJECT_DIR, "config", "user", "filter.json")


def load_filter_config(custom_path=None):
    """加载过滤规则：默认配置 + 用户覆盖。"""
    cfg = {}
    if os.path.exists(DEFAULT_FILTER):
        with open(DEFAULT_FILTER, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    if custom_path and os.path.exists(custom_path):
        with open(custom_path, "r", encoding="utf-8") as f:
            user = json.load(f)
            for key, val in user.items():
                if isinstance(val, dict) and isinstance(cfg.get(key), dict):
                    cfg[key].update(val)
                elif isinstance(val, list) and isinstance(cfg.get(key), list):
                    cfg[key] = val
                else:
                    cfg[key] = val
    elif os.path.exists(USER_FILTER):
        with open(USER_FILTER, "r", encoding="utf-8") as f:
            user = json.load(f)
            for key, val in user.items():
                if isinstance(val, dict) and isinstance(cfg.get(key), dict):
                    cfg[key].update(val)
                elif isinstance(val, list) and isinstance(cfg.get(key), list):
                    cfg[key] = val
                else:
                    cfg[key] = val
    return cfg


def compile_rules(rules):
    """编译 include / exclude 规则列表中的正则表达式。"""
    compiled = []
    for rule in rules:
        try:
            rx = re.compile(rule["pattern"])
        except re.error as e:
            print(f"  警告: 正则编译失败 '{rule.get('description', rule['pattern'])}': {e}")
            continue
        compiled.append({
            "pattern": rule["pattern"],
            "regex": rx,
            "description": rule.get("description", ""),
        })
    return compiled


def filter_terms(input_path, output_path, config_path=None):
    """读取词频文件，按规则过滤，输出过滤后的词频文件。"""
    cfg = load_filter_config(config_path)

    length_cfg = cfg.get("length", {})
    min_len = length_cfg.get("min", 2)
    max_len = length_cfg.get("max", 15)

    stop_words = set(cfg.get("stop_words", []))
    require_cjk = cfg.get("require_cjk", True)
    min_freq = cfg.get("min_freq", 0)

    exclude_rules = compile_rules(cfg.get("exclude", []))
    include_rules = compile_rules(cfg.get("include", []))

    # 加载词频
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    terms = data.get("terms", {})
    total_before = len(terms)
    filtered = {}
    rejected = []  # (word, count, reason)
    stats = {"total": total_before, "length": 0, "stop_words": 0,
             "exclude": 0, "include": 0, "cjk": 0, "freq": 0, "passed": 0}

    for word, count in terms.items():
        # 1. 频次
        if min_freq > 0 and count < min_freq:
            stats["freq"] += 1
            rejected.append((word, count, f"freq: {count} < min({min_freq})"))
            continue

        # 2. 长度
        wlen = len(word)
        if wlen < min_len:
            stats["length"] += 1
            rejected.append((word, count, f"length: {wlen} < min({min_len})"))
            continue
        if wlen > max_len:
            stats["length"] += 1
            rejected.append((word, count, f"length: {wlen} > max({max_len})"))
            continue

        # 2. 停用词
        if word in stop_words:
            stats["stop_words"] += 1
            rejected.append((word, count, "stop_word"))
            continue

        # 3. 正则排除
        excluded = False
        for rule in exclude_rules:
            if rule["regex"].search(word):
                stats["exclude"] += 1
                rejected.append((word, count, f"exclude: {rule['description']}"))
                excluded = True
                break
        if excluded:
            continue

        # 4. 正则包含
        if include_rules:
            included = False
            for rule in include_rules:
                if rule["regex"].search(word):
                    included = True
                    break
            if not included:
                stats["include"] += 1
                rejected.append((word, count, "include: 未匹配任何包含规则"))
                continue

        # 5. 必须含汉字
        if require_cjk:
            if not re.search(r'[\u4e00-\u9fff]', word):
                stats["cjk"] += 1
                rejected.append((word, count, "cjk: 不含汉字"))
                continue

        stats["passed"] += 1
        filtered[word] = count

    data["terms"] = filtered
    if "_filter_stats" not in data:
        data["_filter_stats"] = {}
    data["_filter_stats"]["before"] = total_before
    data["_filter_stats"]["after"] = stats["passed"]
    data["_filter_stats"]["detail"] = stats

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 写入排除记录
    rejected_path = output_path.rsplit(".", 1)[0] + "_rejected.txt"
    with open(rejected_path, "w", encoding="utf-8") as f:
        f.write("# 过滤排除记录 — 词条\t频次\t原因\n")
        for word, count, reason in sorted(rejected, key=lambda x: -x[1]):
            f.write(f"{word}\t{count}\t{reason}\n")
    print(f"  排除记录: {rejected_path} ({len(rejected)} 条)")

    return stats


def main():
    parser = argparse.ArgumentParser(description="词条过滤器")
    parser.add_argument("input", help="词频 JSON 文件 (_terms.json)")
    parser.add_argument("-o", "--output", required=True, help="输出过滤后的词频文件")
    parser.add_argument("--config", default=None, help="自定义过滤规则 JSON（覆盖默认）")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    stats = filter_terms(args.input, args.output, args.config)

    passed = stats["passed"]
    total = stats["total"]
    print(f"  过滤: {total} → {passed} ({100*passed/max(total,1):.0f}%)")
    print(f"    频次过低: {stats.get('freq', 0)}")
    print(f"    长度超限: {stats['length']}")
    print(f"    停用词:   {stats['stop_words']}")
    print(f"    正则排除: {stats['exclude']}")
    print(f"    正则包含: {stats['include']}")
    print(f"    不含汉字: {stats['cjk']}")


if __name__ == "__main__":
    main()
