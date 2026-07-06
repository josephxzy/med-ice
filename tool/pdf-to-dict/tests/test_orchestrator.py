# -*- coding: utf-8 -*-
"""Orchestrator 测试。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.orchestrator import scan_inputs, read_page_range, read_segment_tools


def test_scan_inputs():
    items = scan_inputs()
    assert len(items) >= 0
    for name, subdir, pdf, start, end, tools in items:
        assert os.path.exists(pdf)
        assert start > 0
    print("  OK test_scan_inputs")


def test_read_segment_tools():
    # 药理学 has segment.txt with alinlp + llm
    subdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "operate", "in", "药理学")
    tools = read_segment_tools(subdir)
    assert "alinlp" in tools
    assert "llm" in tools
    print("  OK test_read_segment_tools")

    # 不存在的目录应该返回 [None]
    tools = read_segment_tools("/nonexistent")
    assert tools == [None]
    print("  OK test_read_segment_tools_nonexistent")


if __name__ == "__main__":
    test_scan_inputs()
    test_read_segment_tools()
    print("\n全部通过")
