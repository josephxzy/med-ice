# -*- coding: utf-8 -*-
"""
PDF 文本提取器 - pdf-to-dict 流水线第一步

仅处理可编辑 PDF（非扫描件），逐页提取文字后拼接为纯文本。

用法：
  python ph1_extract.py in/input.pdf -o out/dir/output.txt
"""

import argparse
import os
import sys

try:
    import pdfplumber
except ImportError:
    print("缺少 pdfplumber，请先安装：pip install pdfplumber")
    sys.exit(1)


def extract_pdf(pdf_path, start=1, end=None):
    pages = []
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        print(f"  无法打开 PDF: {e}")
        sys.exit(1)
    with pdf:
        total = len(pdf.pages)
        if end is None:
            end = total
        end = min(end, total)

        print(f"  总页数: {total}, 提取: {start}-{end}")
        extracted_pages = end - start + 1

        for i in range(start - 1, end):
            page = pdf.pages[i]
            text = page.extract_text()
            if text:
                pages.append(text)
            current = i + 1 - (start - 1)
            if current % 50 == 0 or i + 1 == end:
                print(f"    页: {current}/{extracted_pages}")

    return "\n\n".join(pages)


def main():
    parser = argparse.ArgumentParser(description="PDF 文本提取")
    parser.add_argument("input", help="输入 PDF 文件")
    parser.add_argument("-o", "--output", required=True, help="输出 txt 路径")
    parser.add_argument("--start", type=int, default=1, help="起始页")
    parser.add_argument("--end", type=int, default=None, help="结束页")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    text = extract_pdf(args.input, args.start, args.end)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  输出: {args.output} ({len(text)} 字符)")


if __name__ == "__main__":
    main()
