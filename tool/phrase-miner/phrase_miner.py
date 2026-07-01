# -*- coding: utf-8 -*-
"""
中文短语挖掘工具
从语料中自动发现高频短语（NLP 新词发现简化版）

原理：统计 2-8 字 N-gram 频率，过滤低频和单字词，按频率排序输出

用法：
  python phrase_miner.py <input.txt> [output.txt]
  python phrase_miner.py medical_terms.txt phrases.txt
"""

import sys
import re
from collections import Counter


def count_ngrams(text, min_len=2, max_len=8):
    """统计一段文本中的所有 N-gram"""
    grams = []
    chars = list(text)
    n = len(chars)
    for length in range(min_len, min(max_len + 1, n + 1)):
        for i in range(n - length + 1):
            gram = "".join(chars[i:i + length])
            grams.append(gram)
    return grams


def is_valid_phrase(phrase):
    """过滤无效短语：纯符号、含空格等"""
    if not phrase.strip():
        return False
    if re.match(r'^[\d\s\.\-\+/\(\)%%,，、。；;：:！!？?""''（）【】《》〈〉]+$', phrase):
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python phrase_miner.py <input.txt> [output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "phrases.txt"

    print(f"读取: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # 跳过 YAML 头（... 之前的内容）和权重列
    data_started = False
    lines = []
    for line in raw_lines:
        if line == "...":
            data_started = True
            continue
        if not data_started:
            continue
        if line.startswith("#"):
            continue
        # 取 text 列（tab 前的内容）
        text = line.split("\t")[0].strip()
        if text:
            lines.append(text)

    print(f"  语料行数: {len(lines)}")

    # 统计 N-gram 频率
    counter = Counter()
    for line in lines:
        grams = count_ngrams(line)
        counter.update(g for g in grams if is_valid_phrase(g))

    total = counter.total()
    print(f"  N-gram 种类: {len(counter)}, 总出现: {total}")

    # 过滤：最少出现 3 次，最少 2 字
    threshold = max(3, len(lines) // 5000)
    phrases = [(w, c) for w, c in counter.items()
               if len(w) >= 2 and c >= threshold]
    phrases.sort(key=lambda x: -x[1])

    print(f"  筛选后（词频 >= {threshold}）: {len(phrases)} 个短语")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 从 {input_file} 自动发现短语，词频 >= {threshold}\n")
        f.write(f"# 格式: 短语\t频率\n")
        for word, count in phrases:
            f.write(f"{word}\t{count}\n")

    print(f"输出: {output_file}")

    # 展示 top 20
    print("\nTop 20:")
    for word, count in phrases[:20]:
        print(f"  {word}\t{count}")


if __name__ == "__main__":
    main()
