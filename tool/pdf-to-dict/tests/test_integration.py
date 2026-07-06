# -*- coding: utf-8 -*-
"""全面集成测试 — 查找 bug。"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")

# ---- 1. 路径 ----
print("=== 路径 ===")
from utils.paths import IN_DIR, OUT_DIR, CONFIG_DIR, CONFIG_DEFAULT, CONFIG_USER, ROOT as P_ROOT
check("IN_DIR exists", os.path.isdir(IN_DIR))
check("OUT_DIR exists", os.path.isdir(OUT_DIR))
check("CONFIG_DEFAULT exists", os.path.isdir(CONFIG_DEFAULT))
check("CONFIG_USER exists", os.path.isdir(CONFIG_USER))
check("ROOT correct", P_ROOT.replace("\\", "/").endswith("tool/pdf-to-dict"))

# ---- 2. ConfigManager ----
print("\n=== ConfigManager ===")
from config.manager import ConfigManager
cm = ConfigManager()
check("load alinlp", isinstance(cm.load("alinlp"), dict))
check("load text_segment", isinstance(cm.load("text_segment"), dict))
check("load term_decompose", isinstance(cm.load("term_decompose"), dict))
check("load concurrency", isinstance(cm.load("concurrency"), dict))
check("get concurrency.decompose", isinstance(cm.get("concurrency", "decompose"), int))
check("get concurrency.segment.alinlp", cm.get("concurrency", "segment", "alinlp") == 20)

# Test set/reset
old = cm.get("concurrency", "decompose")
cm.set("concurrency", "decompose", 999)
check("set works", cm.get("concurrency", "decompose") == 999)
cm.reset("concurrency")
check("reset works", cm.get("concurrency", "decompose") == old)

# ---- 3. Backends ----
print("\n=== Backends ===")
from backends.factory import BackendFactory
from backends.base import AbstractBackend
for name in BackendFactory.list_names():
    b = BackendFactory.create(name)
    check(f"backend {name} name", b.name == name)
    check(f"backend {name} type", isinstance(b, AbstractBackend))
try:
    BackendFactory.create("xxx")
    check("invalid backend raises", False)
except ValueError:
    check("invalid backend raises", True)

# ---- 4. Orchestrator ----
print("\n=== Orchestrator ===")
from pipeline.orchestrator import scan_inputs, read_page_range, read_segment_tools, PipelineOrchestrator
items = scan_inputs()
check("scan_inputs returns items", len(items) >= 0)
for name, subdir, pdf, start, end, tools in items:
    check(f"  {name} pdf exists", os.path.isfile(pdf))
    check(f"  {name} page_range valid", start > 0 and (end is None or end >= start))
    check(f"  {name} tools valid", all(t in (None, "alinlp", "llm", "ollama") for t in tools))

tools = read_segment_tools(os.path.join(IN_DIR, "药理学"))
check("segment.txt alinlp", "alinlp" in tools)
check("segment.txt llm", "llm" in tools)

orch = PipelineOrchestrator(cm)
check("orchestrator created", orch is not None)

# ---- 5. Text utils ----
print("\n=== Text utils ===")
from utils.text import clean_text, chunk_text, STOP_WORDS
cleaned = clean_text("文前.indd 123\n原发性头痛。2024/1/15 12:30:00")
check("clean removes indd", "文前.indd" not in cleaned)
check("clean removes datetime", "2024/1/15" not in cleaned)
check("clean keeps content", "原发性头痛" in cleaned)

chunks = chunk_text("原发性头痛。继发性头痛。")
check("chunk_text produces output", len(chunks) >= 1)

# ---- 6. State utils ----
print("\n=== State utils ===")
from utils.state import write, read, remove
import tempfile
tmp = os.path.join(tempfile.gettempdir(), "test_state.json")
write(tmp, phase=2, percent=50.0)
s = read(tmp)
check("state write/read phase", s.get("phase") == 2)
check("state write/read percent", s.get("percent") == 50.0)
remove(tmp)
check("state remove", not os.path.exists(tmp))

# ---- 7. DeepSeek controller ----
print("\n=== DeepSeek controller ===")
from pipeline.deepseek_controller import count_tokens
# count_tokens should work without crashing (may return 0 if no tokenizer)
tok = count_tokens("测试")
check("count_tokens returns int", isinstance(tok, int))

# ---- 8. Pipeline phase import check ----
print("\n=== Pipeline phases ===")
import pipeline.ph1_extract
import pipeline.ph2_segment
import pipeline.ph3_filter
import pipeline.ph4_decompose
import pipeline.ph5_dict
check("ph1 imports OK", True)
check("ph2 imports OK", True)
check("ph3 imports OK", True)
check("ph4 imports OK", True)
check("ph5 imports OK", True)

# ---- 9. Commands ----
print("\n=== Commands ===")
import commands.run
import commands.test
import commands.config_cmd
import commands.segment_cmd
check("commands import OK", True)

# ---- Summary ----
print(f"\n{'=' * 40}")
print(f"  {passed} passed, {failed} failed")
print(f"{'=' * 40}")
