# -*- coding: utf-8 -*-
"""
词条分解工具 — 用 DeepSeek 判断 4+ 字词是否可以拆分为独立子词。
输出可用于 ph5_dict.py 的 decompose_words 替代方案。

用法：
  python ph4_decompose.py terms.json -o decompose.json
  python ph4_decompose.py terms.json -o decompose.json --batch 10
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pdf-to-dict/
from pipeline.term_decompose import decompose
from utils.state import safewrite as state_safewrite


def ask_decompose(word):
    try:
        return decompose(word)
    except Exception as e:
        print(f"  [错误] {word}: {e}", file=sys.stderr)
        return []


def decompose_terms(terms, batch_size=5, state_file=None):
    """对 4+ 字词进行 AI 分解，分批提交避免一次性积压所有 future。"""
    candidates = [(w, c) for w, c in terms if len(w) >= 4]
    if not candidates:
        return {}

    def _report(completed, total, results_count):
        if not state_file:
            return
        state_safewrite(state_file, {
            "phase": 3, "phase_name": "拆词",
            "percent": round(100 * completed / total, 1) if total else 0,
            "done": completed, "total": total,
            "detail": f"{results_count} 可分解",
        })

    total = len(candidates)
    print(f"待分解: {total} 个 4+ 字词")
    _report(0, total, 0)
    results = {}
    completed = 0
    chunk_size = batch_size * 2

    executor = ThreadPoolExecutor(max_workers=batch_size)
    try:
        for start in range(0, total, chunk_size):
            batch = candidates[start:start + chunk_size]
            future_map = {executor.submit(ask_decompose, w): w for w, _ in batch}
            futures_list = list(future_map.keys())
            for fut in as_completed(futures_list):
                word = future_map[fut]
                try:
                    subs = fut.result()
                    if subs:
                        results[word] = subs
                        print(f"  {word} → {' '.join(subs)}")
                except Exception as e:
                    print(f"  [错误] {word}: {e}", file=sys.stderr)
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(f"  进度: {completed}/{total}")
                    _report(completed, total, len(results))
            batch_end = min(start + chunk_size, total)
            print(f"  批次: {batch_end}/{total}")
    finally:
        executor.shutdown(wait=False)

    if completed < total:
        print(f"\n  警告: 仅完成 {completed}/{total}，仍有 {total - completed} 项未处理", file=sys.stderr)

    print(f"\n可分解: {len(results)}/{total}")
    return results


def main():
    parser = argparse.ArgumentParser(description="词条 AI 分解")
    parser.add_argument("input", help="输入 _terms.json 或词频文件")
    parser.add_argument("-o", "--output", required=True, help="输出分解结果 JSON")
    parser.add_argument("--batch", type=int, default=5, help="并发数（默认 5）")
    parser.add_argument("--state-file", default=None,
                        help=".pipeline_state.json 路径（向编排器汇报进度）")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    terms = [(w, c) for w, c in data.get("terms", {}).items()]

    total = len(terms)
    results = decompose_terms(terms, args.batch, args.state_file)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"\n结果: {args.output} ({len(results)}/{total} 项可分解)")


if __name__ == "__main__":
    main()
