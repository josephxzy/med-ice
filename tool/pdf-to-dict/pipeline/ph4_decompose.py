# -*- coding: utf-8 -*-
"""
词条分解工具 — 用 DeepSeek 批量判断 4+ 字词是否可拆分为独立子词。
每批 N 个词合并为一次 LLM 请求，降低 prompt token 占比。并发数控制并行请求量。

用法：
  python ph4_decompose.py terms.json -o decompose.json
  python ph4_decompose.py terms.json -o decompose.json --batch 10 --workers 3
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pdf-to-dict/
from pipeline.term_decompose import decompose, decompose_batch
from utils.state import safewrite as state_safewrite

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2


def ask_batch(words):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return decompose_batch(words)
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"  [重试{MAX_RETRIES}次失败] 降级为单条请求...", file=sys.stderr)
                results = {}
                for w in words:
                    try:
                        r = decompose(w)
                        results[w] = r
                    except Exception as e2:
                        print(f"  [放弃] {w}: {e2}", file=sys.stderr)
                return results
            delay = RETRY_BASE_DELAY * attempt
            print(f"  [重试 {attempt}/{MAX_RETRIES}] {delay}s 后重试...", file=sys.stderr)
            time.sleep(delay)


def decompose_terms(terms, words_per_batch=10, workers=3, state_file=None):
    """对 4+ 字词进行批量 AI 分解。words_per_batch 控制每请求词数，workers 控制并行请求数。"""
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
    print(f"待分解: {total} 个 4+ 字词（每批 {words_per_batch} 词, {workers} 并行）")
    _report(0, total, 0)

    # 分批
    batches = []
    for i in range(0, total, words_per_batch):
        batch = candidates[i:i + words_per_batch]
        batches.append([w for w, _ in batch])

    results = {}
    completed = 0

    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        future_map = {executor.submit(ask_batch, b): b for b in batches}
        for fut in as_completed(future_map):
            batch_results = fut.result()
            for word, result in batch_results.items():
                subs = result.get("subs", [])
                if subs:
                    results[word] = result
                    prefix = "[DROP] " if result.get("drop") else ""
                    print(f"  {prefix}{word} → {' '.join(subs)}")
            batch_words = future_map[fut]
            completed += len(batch_words)
            if completed % 50 == 0 or completed == total:
                print(f"  进度: {completed}/{total}")
                _report(completed, total, len(results))
    finally:
        executor.shutdown(wait=False)

    print(f"\n可分解: {len(results)}/{total}")
    return results


def main():
    parser = argparse.ArgumentParser(description="词条 AI 批量分解")
    parser.add_argument("input", help="输入 _terms.json 或词频文件")
    parser.add_argument("-o", "--output", required=True, help="输出分解结果 JSON")
    parser.add_argument("--batch", type=int, default=10, help="每请求词数（默认 10）")
    parser.add_argument("--workers", type=int, default=3, help="并行请求数（默认 3）")
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
    results = decompose_terms(terms, args.batch, args.workers, args.state_file)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"\n结果: {args.output} ({len(results)}/{total} 项可分解)")


if __name__ == "__main__":
    main()
