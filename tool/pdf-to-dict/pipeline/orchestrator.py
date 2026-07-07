# -*- coding: utf-8 -*-
"""Pipeline 编排器。遍历学科 → 后端 → 阶段，管理子进程和 Dashboard。"""

import atexit
import glob
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.paths import IN_DIR, OUT_DIR, ROOT
from utils.state import read as state_read, remove as state_remove


class ProgressDisplay:
    """多行并行进度条 — 重定向 stdout，独占终端控制权。"""

    def __init__(self):
        self._registry = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._real_stdout = sys.stdout
        self._buffer = None

    def register(self, label, state_path):
        with self._lock:
            self._registry[label] = {"state_path": state_path, "percent": 0, "done": 0, "total": 0}

    def unregister(self, label):
        with self._lock:
            self._registry.pop(label, None)

    def start(self):
        self._buffer = io.StringIO()
        sys.stdout = self._buffer
        self._stop.clear()
        if sys.platform == "win32":
            self._enable_ansi()
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        # 恢复 stdout，拿到缓冲的日志
        sys.stdout = self._real_stdout
        pending = self._buffer.getvalue()
        self._buffer.close()
        self._buffer = None
        # 清除进度条区域
        with self._lock:
            count = len(self._registry)
        if count > 0:
            self._real_stdout.write(f"\033[{count}A")
            for _ in range(count):
                self._real_stdout.write("\033[K\n")
            self._real_stdout.write(f"\033[{count}A")
        # 输出缓冲日志
        if pending:
            self._real_stdout.write(pending)
        self._real_stdout.flush()

    def _render(self):
        prev_count = 0
        while not self._stop.is_set():
            with self._lock:
                items = list(self._registry.items())

            count = len(items)

            if count == 0:
                prev_count = 0
                time.sleep(0.5)
                continue

            # 读取各后端进度
            for label, info in items:
                s = state_read(info["state_path"])
                if s and not s.get("error"):
                    info["percent"] = s.get("percent", 0)
                    info["done"] = s.get("done", 0)
                    info["total"] = s.get("total", 0)

            # 构建所有进度行
            line_buf = []
            for label, info in items:
                pct = info["percent"]
                done = info["done"]
                total = info["total"]
                bar_filled = int(pct / 5)
                bar = "█" * bar_filled + "░" * (20 - bar_filled)
                line = f"  {label}  {bar}  {pct:.0f}%"
                if done and total:
                    line += f"  {done}/{total}"
                line_buf.append(f"\r{line}\033[K")

            # 输出进度行（每个以 \n 结束）
            for l in line_buf:
                self._real_stdout.write(l + "\n")

            # 如果数量减少，擦除多余旧行
            if prev_count > count:
                for _ in range(prev_count - count):
                    self._real_stdout.write("\033[K\n")

            # 光标回到进度区顶部
            self._real_stdout.write(f"\033[{max(count, prev_count)}A")
            self._real_stdout.flush()
            prev_count = count
            time.sleep(0.5)

    @staticmethod
    def _enable_ansi():
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

SEGMENT_SCRIPT = os.path.join(ROOT, "pipeline", "ph2_segment.py")
FILTER_SCRIPT = os.path.join(ROOT, "pipeline", "ph3_filter.py")
DECOMPOSE_SCRIPT = os.path.join(ROOT, "pipeline", "ph4_decompose.py")
DICT_GEN_SCRIPT = os.path.join(ROOT, "pipeline", "ph5_dict.py")
PDF_TXT_SCRIPT = os.path.join(ROOT, "pipeline", "ph1_extract.py")

EXIT_QUOTA = 2


def read_page_range(subdir, dir_name=""):
    path = os.path.join(subdir, "page-range.txt")
    if not os.path.exists(path):
        return 1, None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    m = re.match(r'(\d+)\s*[-–—]\s*(\d+)', content)
    if not m:
        return 1, None
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        return end, start
    return start, end


def read_segment_tools(subdir):
    path = os.path.join(subdir, "segment.txt")
    if not os.path.exists(path):
        return [None]
    with open(path, "r", encoding="utf-8") as f:
        tools = [line.strip().lower() for line in f if line.strip()]
    valid = [t for t in tools if t in ("alinlp", "llm", "ollama")]
    return valid if valid else [None]


def scan_inputs():
    items = []
    for entry in sorted(os.listdir(IN_DIR)):
        subdir = os.path.join(IN_DIR, entry)
        if not os.path.isdir(subdir):
            continue
        pdfs = sorted(glob.glob(os.path.join(subdir, "*.pdf")))
        if len(pdfs) != 1:
            if len(pdfs) == 0:
                print(f"  [错误] {entry}/ - 无 PDF 文件")
            else:
                print(f"  [错误] {entry}/ - 多于 1 个 PDF ({len(pdfs)} 个)")
            continue
        start, end = read_page_range(subdir, entry)
        tools = read_segment_tools(subdir)
        items.append((entry, subdir, pdfs[0], start, end, tools))
    return items


class PipelineOrchestrator:
    """编排流水线，管理 Dashboard 和各阶段子进程。"""

    def __init__(self, cm, start_phase=1, stop_phase=5, repdf=False):
        self.cm = cm
        self.start_phase = start_phase
        self.stop_phase = stop_phase
        self.repdf = repdf
        self.default_backend = cm.get("text_segment", "backend") or "alinlp"
        self._children = []       # 追踪所有子进程
        self._monitors = []       # 追踪监控线程的 stop 事件
        self._display = None      # 多后端并行时使用的共享进度显示器

    def _cleanup(self):
        """主窗口关闭时终止所有子进程和监控线程。"""
        for stop in self._monitors:
            stop.set()
        for proc in self._children:
            try:
                proc.terminate()
            except Exception:
                pass
        self._children.clear()
        self._monitors.clear()
        print("\n  已终止所有子进程")

    def run(self):
        # 注册退出清理
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, lambda s, f: (self._cleanup(), sys.exit(1)))
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, lambda s, f: (self._cleanup(), sys.exit(1)))

        inputs = scan_inputs()
        if not inputs:
            print("in/ 下无有效子目录")
            return

        labels = {1: "提取文本", 2: "分词", 3: "过滤", 4: "短语拆词", 5: "生成词库"}
        phases = range(self.start_phase, self.stop_phase + 1)
        desc = " → ".join(labels[p] for p in phases)
        print(f"\n{'=' * 50}")
        print(f"  {desc}")
        print(f"{'=' * 50}")

        max_books = self.cm.get("concurrency", "max_parallel_books") or 1

        if max_books <= 1 or len(inputs) <= 1:
            for item in inputs:
                self._process_book(item)
        else:
            with ThreadPoolExecutor(max_workers=min(max_books, len(inputs))) as ex:
                futures = {ex.submit(self._process_book, item): item[0] for item in inputs}
                for fut in as_completed(futures):
                    result = fut.result()
                    if result == "quota":
                        for f in futures:
                            f.cancel()
                        print(f"\n  配额耗尽，明日继续")
                        return

    # ---- 单书处理 ----

    def _process_book(self, item):
        dir_name, _subdir, pdf_path, start, end, tools = item
        pdf_out = os.path.join(OUT_DIR, dir_name)
        os.makedirs(pdf_out, exist_ok=True)
        txt_file = os.path.join(pdf_out, f"{dir_name}.txt")

        backends = [self.default_backend if t is None else t for t in tools]
        backends = list(dict.fromkeys(backends))

        print(f"\n{'─' * 40}")
        print(f"  {dir_name}/  |  {os.path.basename(pdf_path)}")
        print(f"  分词工具: {', '.join(backends)}")
        if start > 1 or end:
            print(f"  页码: {start}-{end or '末'}")
        print(f"{'─' * 40}")

        # Phase 1: TXT（共享）
        phases = range(self.start_phase, self.stop_phase + 1)
        need_txt = (2 in phases or 3 in phases or 4 in phases) and not os.path.exists(txt_file)
        if 1 in phases or need_txt:
            if os.path.exists(txt_file) and not (1 in phases and self.repdf):
                print(f"  [Phase 1/{self.stop_phase}] 提取文本 → 跳过")
            else:
                tag = " [补齐]" if 1 not in phases else ""
                print(f"  [Phase 1/{self.stop_phase}] 提取文本{tag}")
                rc = subprocess.run([
                    sys.executable, PDF_TXT_SCRIPT, pdf_path,
                    "-o", txt_file, "--start", str(start),
                ] + (["--end", str(end)] if end else [])).returncode
                if rc != 0:
                    print(f"    ✗ 失败")
                    return "failed"

        if len(backends) == 1:
            return self._process_backend(dir_name, pdf_out, txt_file, pdf_path, start, end, backends[0])
        else:
            return self._run_parallel_backends(dir_name, pdf_out, txt_file, pdf_path, start, end, backends)

    # ---- 多后端并发 ----

    def _run_parallel_backends(self, dir_name, pdf_out, txt_file, pdf_path, start, end, backends):
        """多后端并发：各自线程跑，共享 ProgressDisplay 同时展示进度。"""
        results = {}
        lock = threading.Lock()

        self._display = ProgressDisplay()
        self._display.start()

        def _worker(b):
            result = self._process_backend(dir_name, pdf_out, txt_file, pdf_path, start, end, b)
            with lock:
                results[b] = result
            return result

        try:
            with ThreadPoolExecutor(max_workers=len(backends)) as ex:
                futures = {ex.submit(_worker, b): b for b in backends}
                for fut in as_completed(futures):
                    b = futures[fut]
                    result = fut.result()
                    if result == "quota":
                        for f in futures:
                            f.cancel()
                        self._cleanup()
                        return "quota"
        finally:
            self._display.stop()
            self._display = None

        return "done"

    # ---- 单后端完整流水线 ----

    def _process_backend(self, dir_name, pdf_out, txt_file, pdf_path, start, end, backend):
        backend_dir = os.path.join(pdf_out, backend)
        os.makedirs(backend_dir, exist_ok=True)
        terms_file = os.path.join(backend_dir, f"{dir_name}_terms.json")
        progress_file = os.path.join(backend_dir, f"{dir_name}.progress")

        # Phase 2
        if 2 in range(self.start_phase, self.stop_phase + 1):
            if not self._phase2(txt_file, terms_file, progress_file, backend):
                return "failed"

        # 补齐 Phase 2
        elif any(p in range(self.start_phase, self.stop_phase + 1) for p in (3, 4, 5)):
            if not os.path.exists(terms_file):
                if not self._phase2(txt_file, terms_file, progress_file, backend):
                    return "failed"

        # Phase 3: 词条过滤
        if 3 in range(self.start_phase, self.stop_phase + 1):
            self._run_filter(terms_file)
        elif any(p in range(self.start_phase, self.stop_phase + 1) for p in (4, 5)):
            self._run_filter(terms_file)

        # Phase 4: 拆词（可选）
        if 4 in range(self.start_phase, self.stop_phase + 1):
            self._phase4(terms_file, backend_dir)

        # Phase 5: 生成词库
        if 5 in range(self.start_phase, self.stop_phase + 1):
            self._phase5(terms_file, dir_name, backend_dir, backend)

        return "done"

    # ---- Phase 2: 分词 ----

    def _phase2(self, txt_file, terms_file, progress_file, backend):
        print(f"\n  [Phase 2/{self.stop_phase}] [{backend}] 分词")
        if os.path.exists(terms_file):
            print(f"    → 跳过")
            return True

        has_progress = os.path.exists(progress_file)
        if has_progress:
            print(f"    ↻ 续转")

        state_path = progress_file + ".state.json"

        # 从 concurrency.segment.{backend} 读取并发数
        seg_concurrency = self.cm.get("concurrency", "segment", backend)
        batch_size = seg_concurrency if seg_concurrency is not None else None

        step_args = [
            sys.executable, SEGMENT_SCRIPT, txt_file,
            "-o", terms_file, "-p", progress_file,
            "--backend", backend,
            "--state-file", state_path,
        ]
        if batch_size is not None:
            step_args.extend(["--batch", str(batch_size)])
        if has_progress:
            step_args.append("--resume")

        rc = self._run_phase_subprocess(step_args, state_path, f"Phase 2 [{backend}]", backend)
        if rc is None:
            return False

        if rc == EXIT_QUOTA:
            print(f"  [{backend}] 配额耗尽")
            return "quota"
        if rc != 0:
            print(f"  [{backend}] ✗ 失败")
            return False
        return True

    # ---- Phase 3: 词条过滤 ----

    def _run_filter(self, terms_file):
        """在生成词库前应用可配置的正则过滤规则（config/filter.json）。
        过滤结果覆盖 terms 文件，排除详情写入 _rejected.txt。"""
        if not os.path.exists(terms_file):
            return
        # 检测是否已过滤（_filter_stats 标记）
        try:
            with open(terms_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "_filter_stats" in data:
                return
        except Exception:
            pass

        print(f"\n  [Phase 3/{self.stop_phase}] 词条过滤")
        rc = subprocess.run([
            sys.executable, FILTER_SCRIPT, terms_file,
            "-o", terms_file,
        ]).returncode
        if rc != 0:
            print(f"    ✗ 过滤失败，跳过")
        else:
            try:
                with open(terms_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stats = data.get("_filter_stats", {})
                print(f"    ✓ {stats.get('before', '?')} → {stats.get('after', '?')} 条")
            except Exception:
                pass

    # ---- Phase 4: 拆词 ----

    def _phase4(self, terms_file, backend_dir):
        backend = os.path.basename(backend_dir)
        print(f"\n  [Phase 4/{self.stop_phase}] [{backend}] 短语拆词")
        decompose_file = terms_file[:-len("_terms.json")] + "_decompose.json"
        if os.path.exists(decompose_file):
            print(f"    → 跳过")
            return

        words_per_batch = self.cm.get("concurrency", "decompose", "batch") or 10
        workers = self.cm.get("concurrency", "decompose", "workers") or 3
        state_path = decompose_file + ".state.json"

        step_args = [
            sys.executable, DECOMPOSE_SCRIPT, terms_file,
            "-o", decompose_file,
            "--batch", str(words_per_batch),
            "--workers", str(workers),
            "--state-file", state_path,
        ]

        self._run_phase_subprocess(step_args, state_path, f"Phase 4 [{backend}]", backend)

    # ---- 子进程启动 + 监控 ----

    def _run_phase_subprocess(self, step_args, state_path, label, backend):
        """启动子进程（Windows 独立窗口），监控进度，阻塞等待完成。"""
        if sys.platform == "win32":
            proc = subprocess.Popen(
                step_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            proc = subprocess.Popen(step_args)

        self._children.append(proc)
        if self._display:
            self._display.register(label, state_path)
        else:
            t, stop = self._monitor_state(state_path, label)
            self._monitors.append(stop)
        proc.wait()
        if self._display:
            self._display.unregister(label)
        else:
            stop.set()
            t.join(timeout=2)
            self._monitors.remove(stop)
        self._children.remove(proc)

        if proc.returncode != 0:
            self._log_subprocess_error(state_path, backend)

        return proc.returncode

    def _log_subprocess_error(self, state_path, backend):
        s = state_read(state_path)
        if s.get("error"):
            print(f"\n  [{backend}] 错误: {s['error'][:200]}")
        else:
            failed_log = state_path.replace(".state.json", ".failed.json")
            if os.path.exists(failed_log):
                try:
                    with open(failed_log, "r", encoding="utf-8") as f:
                        fl = json.load(f)
                    if isinstance(fl, dict) and fl.get("error"):
                        print(f"\n  [{backend}] 错误: {fl['error'][:200]}")
                except Exception:
                    pass

    # ---- Phase 5: 生成词典 ----

    def _phase5(self, terms_file, dir_name, backend_dir, backend):
        print(f"\n  [Phase 5/{self.stop_phase}] [{backend}] 生成词库")
        dict_name = f"med_{dir_name}.dict.yaml"
        if os.path.exists(os.path.join(backend_dir, dict_name)):
            print(f"    → 跳过")
            return

        decompose_file = terms_file[:-len("_terms.json")] + "_decompose.json"
        if os.path.exists(decompose_file):
            with open(terms_file, "r", encoding="utf-8") as f:
                terms_data = json.load(f)
            with open(decompose_file, "r", encoding="utf-8") as f:
                decomp = json.load(f)
            for word, result in decomp.items():
                subs = result.get("subs", [])
                if not subs:
                    continue
                count = terms_data["terms"].get(word, 1)
                for sub in subs:
                    terms_data["terms"][sub] = terms_data["terms"].get(sub, 0) + count
                if result.get("drop"):
                    terms_data["terms"].pop(word, None)
            merged = terms_file[:-len("_terms.json")] + "_decomposed_terms.json"
            with open(merged, "w", encoding="utf-8") as f:
                json.dump(terms_data, f, ensure_ascii=False)
            name = f"med_{dir_name}"
            subprocess.run([
                sys.executable, DICT_GEN_SCRIPT, merged,
                "--name", name, "--out-dir", backend_dir,
            ])
            os.remove(merged)
        else:
            name = f"med_{dir_name}"
            subprocess.run([
                sys.executable, DICT_GEN_SCRIPT, terms_file,
                "--name", name, "--out-dir", backend_dir,
            ])
        print(f"    ✓ {dict_name}")

    # ---- Dashboard ----

    def _monitor_state(self, state_path, label, interval=1.0, line_offset=1):
        """轮询状态文件，刷新进度条（\r 单行）。返回 (thread, stop_event)。"""
        stop = threading.Event()

        def _poll():
            last_line = ""
            while not stop.is_set():
                state = state_read(state_path)
                if state and not state.get("error"):
                    pct = state.get("percent", 0)
                    done = state.get("done", 0)
                    total = state.get("total", 0)
                    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                    line = f"\r  {label}  {bar}  {pct:.0f}%"
                    if done and total:
                        line += f"  {done}/{total}"
                    if line != last_line:
                        sys.stdout.write(line + " " * 30)
                        sys.stdout.flush()
                        last_line = line
                time.sleep(interval)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()
        return t, stop
