# -*- coding: utf-8 -*-
"""Text 工具测试。"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text import clean_text, chunk_text, STOP_WORDS, CHUNK_CHAR_LIMIT


def test_clean_text():
    raw = "文前.indd 123\n原发性头痛的药物治疗。2024/1/15 12:30:00 患者"
    cleaned = clean_text(raw)
    assert "文前.indd" not in cleaned
    assert "2024/1/15" not in cleaned
    assert "原发性头痛" in cleaned
    print("  OK test_clean_text")


def test_chunk_text():
    text = "原发性头痛的药物治疗。继发性头痛的分类。"
    chunks = chunk_text(text)
    assert len(chunks) >= 1
    assert any("头痛" in c for c in chunks)
    print("  OK test_chunk_text")


def test_stopwords():
    assert "的" in STOP_WORDS
    assert "是" in STOP_WORDS
    assert "结合" in STOP_WORDS
    assert "hello" not in STOP_WORDS
    print("  OK test_stopwords")


if __name__ == "__main__":
    test_clean_text()
    test_chunk_text()
    test_stopwords()
    print("\n全部通过")
