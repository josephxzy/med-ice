# -*- coding: utf-8 -*-
"""
词库生成器 - pdf-to-dict 流水线最后一步

读取已过滤的词频文件，生成 Rime 词库（.dict.yaml）。

用法：
  python ph5_dict.py filtered_terms.json --name med_anatomy --out-dir out/pdf_name/
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_terms(path):
    """从 _terms.json 或 _freq.txt 加载词频（含子词增强）。"""
    if path.endswith(".json"):
        terms = load_from_json(path)
    else:
        terms = load_from_txt(path)
    return decompose_words(terms)


def load_from_json(path):
    terms = []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for word, count in data.get("terms", {}).items():
        terms.append((word, count))
    return sorted(terms, key=lambda x: -x[1])


def decompose_words(terms):
    """子词增强：4+字词的 2-3 字片段若独立存在，累加频率。
    例如 '面赤身热'→'面赤'+'身热' 都在词表里，则三者同时保留，子词加权。"""
    word_map = {w: c for w, c in terms}
    for word, count in list(word_map.items()):
        if len(word) < 4:
            continue
        for i in range(len(word) - 1):
            sub = word[i:i + 2]
            if sub in word_map:
                word_map[sub] += count
        for i in range(len(word) - 2):
            sub = word[i:i + 3]
            if sub in word_map:
                word_map[sub] += count
    return sorted(word_map.items(), key=lambda x: -x[1])


def load_from_txt(path):
    terms = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            word, count = parts[0], int(parts[1])
            terms.append((word, count))
    return terms


def generate_dict(terms, dict_name, display_name, output_dir):
    out_path = os.path.join(output_dir, f"{dict_name}.dict.yaml")
    os.makedirs(output_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Rime dictionary\n")
        f.write("# encoding: utf-8\n")
        f.write("#\n")
        f.write(f"# {display_name} - 自动提取\n")
        f.write("#\n")
        f.write("---\n")
        f.write(f"name: {dict_name}\n")
        f.write('version: "1"\n')
        f.write("sort: by_weight\n")
        f.write("columns:\n")
        f.write("  - text\n")
        f.write("  - code\n")
        f.write("  - weight\n")
        f.write("\n")
        f.write("...\n")
        f.write("# +_+\n")
        for word, weight in terms:
            f.write(f"{word}\t\t{weight}\n")

    return out_path


def main():
    parser = argparse.ArgumentParser(description="词库生成")
    parser.add_argument("input", help="词频文件 (_freq.txt)")
    parser.add_argument("--name", required=True, help="词库名称（含 med_ 前缀）")
    parser.add_argument("--dict-name", default="", help="词典显示名称")
    parser.add_argument("--out-dir", required=True, help="输出目录")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    display = args.dict_name or args.name

    terms = load_terms(args.input)
    print(f"  收集: {len(terms)} 条术语")

    # 输出到目标目录
    out_path = generate_dict(terms, args.name, display, args.out_dir)
    print(f"  输出: {out_path}")


if __name__ == "__main__":
    main()
