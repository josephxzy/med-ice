# -*- coding: utf-8 -*-
"""
文本分词器 - pdf-to-dict 流水线第二步

调用阿里云 NLP 分词，输出词频列表。支持断点续转和配额感知。

用法：
  python ph2_segment.py input.txt -o out/terms_freq.txt -p out/progress.json
  python ph2_segment.py input.txt --resume -p out/progress.json
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutTimeout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pdf-to-dict/
from pipeline.alinlp_ws import call_api, load_config, save_config
from pipeline.llm_segment import segment as segment_llm
from utils.text import clean_text, chunk_text, CHUNK_CHAR_LIMIT
from utils.state import safewrite

SEGMENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SEGMENT_DIR)
DEFAULT_DIR = os.path.join(PROJECT_DIR, "config", "default")
USER_DIR = os.path.join(PROJECT_DIR, "config", "user")
SEGMENT_CONFIG = os.path.join(USER_DIR, "text_segment.json")
SEGMENT_DEFAULT = os.path.join(DEFAULT_DIR, "text_segment.json")

BATCH_SIZE = 20
DISPATCH_INTERVAL = 0.05
DISPATCH_INTERVAL_LLM = 0  # LLM 无 QPS 限制，不等待
EXIT_OK = 0
EXIT_QUOTA = 2
MAX_RETRIES = 1
RETRY_BASE_DELAY = 2
MAX_RETRY_ROUNDS = 3

# 重试由 MAX_RETRY_ROUNDS 集中处理，单块不原地重试


def check_quota():
    cfg = load_config()
    cfg.setdefault("limit", 500000)
    return cfg


def segment_chunk(chunk, cfg):
    """根据 cfg.backend 选择分词后端，返回 (词列表, token 用量, 后端名)。"""
    backend = cfg.get("backend", "alinlp")
    if backend == "alinlp":
        words, tokens = call_api(chunk, cfg["access_key_id"], cfg["access_key_secret"],
                        cfg.get("out_type", "1"))
    elif backend == "llm":
        llm = cfg.get("llm", {})
        words, tokens = call_llm(chunk, llm)
    elif backend == "ollama":
        ollama = cfg.get("ollama", {})
        words, tokens = call_ollama(chunk, ollama)
    else:
        raise Exception(f"未知后端: {backend}")
    return words, tokens, backend


def call_llm(text, llm):
    """LLM 分词，委托 ai_application.text_segment。"""
    return segment_llm(text, llm)


def call_ollama(text, ollama):
    """本地 Ollama 分词。"""
    import urllib.request, json
    prompt = ollama.get("prompt", "将以下医学文本分词，空格分隔，只输出分词结果。\n{text}").format(text=text)
    body = json.dumps({"model": ollama.get("model", ""), "prompt": prompt, "stream": False,
                        "options": {"temperature": 0}}).encode("utf-8")
    req = urllib.request.Request(f"{ollama.get('host', '')}/api/generate", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise Exception(f"Ollama 请求失败: {e}")
    content = data.get("response", "").strip()
    return content.split(), data.get("eval_count", 0)


def count_tokens(text):
    try:
        from pipeline.deepseek_controller import count_tokens as ct
        return ct(text)
    except Exception:
        return -1


def add_words(counter, words):
    for w in words:
        if len(w) >= 2:
            counter[w] += 1


def add_words_from_text(counter, text, words):
    """LLM 只返回不重复的词，频率从原文检索。"""
    for w in words:
        if len(w) >= 2:
            counter[w] += text.count(w)


def run_batch(batch, counter, cfg, batch_start_idx, batch_size=BATCH_SIZE,
              state_file=None, total_chunks=0, state_backend=None):
    """处理一批块。返回 (成功数, 失败块列表, token 用量, 尝试数)。"""
    valid = [c for c in batch if c.strip()]
    if not valid:
        return 0, [], 0, 0

    use_concurrency = batch_size > 1 and len(valid) > 1
    success = 0
    failed = []
    total_tokens = 0

    def _report_state(completed_in_batch):
        if not state_file:
            return
        import time as _t
        _state = {
            "phase": 2, "phase_name": "分词",
            "percent": round(100 * (batch_start_idx + completed_in_batch) / total_chunks, 1) if total_chunks else 0,
            "done": batch_start_idx + completed_in_batch, "total": total_chunks,
            "terms": len(counter),
            "backend": state_backend or "",
            "updated_at": _t.time(),
        }
        safewrite(state_file, _state)

    def _show(chunk, words, be):
        preview = chunk[:50].replace("\n", " ")
        if be == "alinlp":
            # alinlp 直接输出完整分词结果
            shown = words[:30]
            tail = f" ...(+{len(words)-30})" if len(words) > 30 else ""
            print(f"  [{preview}] → {' '.join(shown)}{tail}")
        else:
            # LLM / Ollama 标注原文：「词」= 有效词汇，（词）= 不满足过滤条件
            # 逐字符占位法：每字只标注一次，长词优先，杜绝嵌套
            is_valid = lambda w: len(w) >= 2
            text = chunk[:300].replace("\n", " ")
            n = len(text)
            occupied = [False] * n
            annotations = []  # (start, end, marker)

            for w in sorted(words, key=lambda x: (-len(x), not is_valid(x))):
                v = is_valid(w)
                marker = f"「{w}」" if v else f"（{w}）"
                idx = 0
                while True:
                    pos = text.find(w, idx)
                    if pos == -1:
                        break
                    if not any(occupied[p] for p in range(pos, pos + len(w))):
                        annotations.append((pos, pos + len(w), marker))
                        for p in range(pos, pos + len(w)):
                            occupied[p] = True
                    idx = pos + 1

            annotations.sort(key=lambda x: x[0])
            buf = []
            cursor = 0
            for start, end, marker in annotations:
                buf.append(text[cursor:start])
                buf.append(marker)
                cursor = end
            buf.append(text[cursor:])
            annotated = "".join(buf)
            print(f"  {annotated}")

    if use_concurrency:
        backend = cfg.get("backend", "alinlp")
        interval = 0 if backend in ("llm", "ollama") else DISPATCH_INTERVAL
        executor = ThreadPoolExecutor(max_workers=min(batch_size, len(valid)))
        try:
            futures = {}
            futures_list = []
            for chunk in valid:
                future = executor.submit(segment_chunk, chunk, cfg)
                futures[future] = chunk
                futures_list.append(future)
                if interval:
                    time.sleep(interval)

            # as_completed 逐条完成即汇报进度，不等人齐
            try:
                for future in as_completed(futures_list, timeout=60):
                    chunk = futures[future]
                    try:
                        words, tokens, backend = future.result()
                        if backend == "alinlp":
                            add_words(counter, words)
                        else:
                            add_words_from_text(counter, chunk, words)
                        success += 1
                        total_tokens += tokens
                        _show(chunk, words, backend)
                        _report_state(success)
                    except Exception:
                        failed.append(chunk)
            except FutTimeout:
                for future in futures_list:
                    if not future.done():
                        future.cancel()
                        failed.append(futures[future])
        finally:
            executor.shutdown(wait=False)
    else:
        for chunk in valid:
            try:
                words, tokens, backend = segment_chunk(chunk, cfg)
                if backend == "alinlp":
                    add_words(counter, words)
                else:
                    add_words_from_text(counter, chunk, words)
                success += 1
                total_tokens += tokens
                _show(chunk, words, backend)
                if success % 5 == 0:
                    _report_state(success)
            except Exception:
                failed.append(chunk)

    return success, failed, total_tokens, len(valid)


def _apply_seg_config(cfg, seg_cfg):
    """将 text_segment 配置合并到运行时 cfg 中（backend、llm 参数等）。并发数由 --batch 控制，不在这里设置。"""
    cfg["backend"] = seg_cfg.get("backend", cfg.get("backend", "alinlp"))
    cfg.setdefault("llm", {}).update(seg_cfg.get("llm", {}))
    cfg["llm"]["system_prompt"] = seg_cfg.get("system_prompt", cfg["llm"].get("system_prompt", ""))
    cfg["llm"]["user_prompt"] = seg_cfg.get("user_prompt", cfg["llm"].get("user_prompt", ""))
    cfg.setdefault("ollama", {}).update(seg_cfg.get("ollama", {}))
    return cfg


def load_failed_chunks(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("chunks", []), data.get("round", 0)
    return [], 0


def save_failed_chunks(path, chunks, round_num):
    if chunks:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"chunks": chunks, "round": round_num}, f, ensure_ascii=False)
    elif os.path.exists(path):
        os.remove(path)


def load_progress(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"offset": 0, "terms": {}}


def save_progress(path, offset, counter):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"offset": offset, "terms": dict(counter.most_common())}, f, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="文本分词")
    parser.add_argument("input", help="输入 txt 文件")
    parser.add_argument("-o", "--output", required=True, help="输出词频文件")
    parser.add_argument("-p", "--progress", default=None, help="进度文件（断点续转）")
    parser.add_argument("--resume", action="store_true", help="从上次中断处继续")
    parser.add_argument("--backend", choices=["alinlp", "llm", "ollama"], default=None,
                        help="覆盖配置文件中的分词后端")
    parser.add_argument("--batch", type=int, default=None,
                        help="并发数（覆盖 text_segment.json 中的 *_batch）")
    parser.add_argument("--state-file", default=None,
                        help=".pipeline_state.json 路径（向编排器汇报进度）")
    args = parser.parse_args()

    def _fail(msg):
        print(msg, file=sys.stderr)
        if args.state_file:
            safewrite(args.state_file, {"error": msg})
        sys.exit(1)

    if not os.path.exists(args.input):
        _fail(f"文件不存在: {args.input}")

    progress_path = args.progress or (args.output + ".progress")

    with open(args.input, "r", encoding="utf-8") as f:
        raw = f.read()

    cleaned = clean_text(raw)
    print(f"  文本: {len(raw)} → {len(cleaned)} 字符（清洗后）")

    chunks = chunk_text(cleaned)
    print(f"  分块: {len(chunks)}")

    prog = load_progress(progress_path) if args.resume else {"offset": 0, "terms": {}}
    offset = prog.get("offset", 0)
    counter = Counter(prog.get("terms", {}))

    if offset > 0:
        print(f"  恢复: 已完成 {offset}/{len(chunks)}，已收集 {len(counter)} 个词")

    cfg = check_quota()
    # 合并默认 + 用户配置
    seg_cfg = {}
    if os.path.exists(SEGMENT_DEFAULT):
        with open(SEGMENT_DEFAULT, "r", encoding="utf-8") as f:
            seg_cfg = json.load(f)
    if os.path.exists(SEGMENT_CONFIG):
        with open(SEGMENT_CONFIG, "r", encoding="utf-8") as f:
            user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(seg_cfg.get(k), dict):
                    seg_cfg[k].update(v)
                else:
                    seg_cfg[k] = v
    if args.backend:
        seg_cfg["backend"] = args.backend
    cfg = _apply_seg_config(cfg, seg_cfg)
    backend = cfg.get("backend", "alinlp")
    if backend == "alinlp" and (not cfg.get("access_key_id") or not cfg.get("access_key_secret")):
        _fail("请编辑 config/user/alinlp.json 填入 access_key_id")
    if backend == "llm" and not cfg.get("llm", {}).get("api_key"):
        _fail("请配置 LLM api_key（python main.py config set text_segment llm.api_key sk-xxx）")

    backend = cfg.get("backend", "alinlp")
    batch_size = args.batch or BATCH_SIZE
    failed_path = progress_path + ".failed.json"

    # 写入初始 0% 状态，让进度条立即可见
    if args.state_file:
        safewrite(args.state_file, {
            "phase": 2, "phase_name": "分词",
            "percent": 0, "done": offset, "total": len(chunks),
            "terms": len(counter), "backend": backend,
        })

    # ---------- 主流程：逐批处理 ----------
    i = offset
    while i < len(chunks):
        quota_cfg = load_config()
        today = time.strftime("%Y-%m-%d")
        if quota_cfg.get("date") != today:
            quota_cfg["date"] = today
            quota_cfg["count"] = 0
            quota_cfg["total_tokens"] = 0
            save_config(quota_cfg)
        if quota_cfg.get("count", 0) >= quota_cfg.get("limit", 500000):
            print(f"\n  配额耗尽: {quota_cfg['count']}/{quota_cfg['limit']}")
            save_progress(progress_path, i, counter)
            print(f"  进度已保存，明日加 --resume 继续")
            sys.exit(EXIT_QUOTA)

        cfg = _apply_seg_config(quota_cfg, seg_cfg)
        batch = chunks[i:i + batch_size]
        success, failed, tokens, attempted = run_batch(batch, counter, cfg, i, batch_size,
                                                       state_file=args.state_file, total_chunks=len(chunks),
                                                       state_backend=backend)

        if attempted > 0:
            quota_cfg = load_config()
            quota_cfg["count"] += attempted
            quota_cfg["total_tokens"] = quota_cfg.get("total_tokens", 0) + tokens
            save_config(quota_cfg)

        if failed:
            prev, _ = load_failed_chunks(failed_path)
            prev.extend(failed)
            save_failed_chunks(failed_path, prev, 0)
            print(f"\n  本批失败 {len(failed)} 个块，已累计 {len(prev)} 个")

        i += len(batch)
        save_progress(progress_path, i, counter)
        cfg_now = load_config()
        tk = cfg_now.get("total_tokens", 0)
        tk_str = f" - Tokens: {tk}" if tk else ""

        if backend == "alinlp":
            quota_str = f" - API: {cfg_now['count']}/{cfg_now.get('limit', 500000)}"
            print(f"  {i}/{len(chunks)} ({100*i/len(chunks):.0f}%) - {len(counter)} 词{quota_str}", flush=True)
        elif backend == "llm":
            print(f"  {i}/{len(chunks)} ({100*i/len(chunks):.0f}%) - {len(counter)} 词{tk_str}", flush=True)
        else:
            print(f"  {i}/{len(chunks)} ({100*i/len(chunks):.0f}%) - {len(counter)} 词", flush=True)

    save_progress(progress_path, len(chunks), counter)

    # 检查是否有失败块需要重试
    failed_chunks, prev_round = load_failed_chunks(failed_path)
    if failed_chunks:
        print(f"\n  主流程结束: {len(counter)} 词, {len(failed_chunks)} 块失败待重试")
    else:
        print(f"\n  完成: {len(counter)} 个词，总出现 {sum(counter.values())} 次")

    # ---------- 失败块集中重试 ----------
    if failed_chunks:
        print(f"\n{'=' * 40}")
        print(f"  集中重试: {len(failed_chunks)} 个失败块")
        print(f"{'=' * 40}")

        round_num = prev_round
        while failed_chunks and round_num < MAX_RETRY_ROUNDS:
            quota_cfg = load_config()
            today = time.strftime("%Y-%m-%d")
            if quota_cfg.get("date") != today:
                quota_cfg["date"] = today
                quota_cfg["count"] = 0
                quota_cfg["total_tokens"] = 0
                save_config(quota_cfg)
            if quota_cfg.get("count", 0) >= quota_cfg.get("limit", 500000):
                print(f"\n  配额耗尽: {quota_cfg['count']}/{quota_cfg['limit']}")
                print(f"  剩余 {len(failed_chunks)} 块未处理，明日加 --resume 继续")
                sys.exit(EXIT_QUOTA)

            cfg = _apply_seg_config(quota_cfg, seg_cfg)
            round_num += 1
            remaining = []

            for batch_start in range(0, len(failed_chunks), batch_size):
                batch = failed_chunks[batch_start:batch_start + batch_size]
                success, failed, tokens, attempted = run_batch(batch, counter, cfg, batch_start, batch_size)
                if attempted > 0:
                    quota_cfg = load_config()
                    quota_cfg["count"] += attempted
                    quota_cfg["total_tokens"] = quota_cfg.get("total_tokens", 0) + tokens
                    save_config(quota_cfg)
                remaining.extend(failed)
                if remaining != failed_chunks:
                    save_failed_chunks(failed_path, remaining, round_num)
                    save_progress(progress_path, len(chunks), counter)

            recovered = len(failed_chunks) - len(remaining)
            failed_chunks = remaining
            print(f"\n  第 {round_num} 轮: 救回 {recovered}, 剩余 {len(failed_chunks)}")

        if failed_chunks:
            save_failed_chunks(failed_path, failed_chunks, round_num)
            print(f"\n  最终放弃 {len(failed_chunks)} 个块")
        else:
            save_failed_chunks(failed_path, [], round_num)
            print(f"\n  全部重试成功")

    # 最终 100% 确认
    if args.state_file:
        safewrite(args.state_file, {
            "phase": 2, "phase_name": "分词",
            "percent": 100.0,
            "done": len(chunks), "total": len(chunks),
            "terms": len(counter),
            "backend": backend,
        })

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    if os.path.exists(args.output):
        os.remove(args.output)
    os.rename(progress_path, args.output)
    print(f"  输出: {args.output} ({len(counter)} 条)")


if __name__ == "__main__":
    main()
