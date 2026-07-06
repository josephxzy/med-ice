# -*- coding: utf-8 -*-
"""文本清洗、分块、停用词。"""

import re

STOP_WORDS = {
    "是在", "各种", "分为", "包括", "称为", "相关", "以及", "两者",
    "位于", "具有", "可以", "参与", "形成", "经过", "主要",
    "一个", "这个", "它的", "它们", "一些", "这些", "一般",
    "所谓", "发生", "特别", "出现", "进行", "产生", "引起",
    "由于", "所以", "因此", "另外", "并且", "还有",
    "或", "和", "的", "是", "在", "有", "为", "与", "及", "等",
    "之间", "分布", "构成", "发出", "结构", "系统", "部分",
    "两侧", "作用", "功能", "器官", "通过", "不同",
    "结合", "保护",
}

CHUNK_CHAR_LIMIT = 300


def clean_text(text):
    text = re.sub(r'文前\.indd\s*\d+', '', text)
    text = re.sub(r'\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2}', '', text)
    text = re.sub(r'[\u2000-\u200f\u2028-\u202f\u205f\u3000\ufeff\x0c]', '', text)
    text = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffefa-zA-Z0-9]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def chunk_text(text):
    sentences = re.split(r'[。，；！？、：\n]', text)
    chunks = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        while len(s) > CHUNK_CHAR_LIMIT:
            chunks.append(s[:CHUNK_CHAR_LIMIT])
            s = s[CHUNK_CHAR_LIMIT:]
        if not s:
            continue
        if len(current + " " + s) <= CHUNK_CHAR_LIMIT:
            current += " " + s if current else s
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks
