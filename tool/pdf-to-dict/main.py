# -*- coding: utf-8 -*-
"""
pdf-to-dict — PDF → Rime 医学词库

五阶段流水线：
  1. 提取文本 — PDF → TXT
  2. 分词     — TXT → 词频 JSON
  3. 过滤     — 应用正则规则清洗词表
  4. 短语拆词 — 4+ 字词 AI 拆分为短词（可选）
  5. 生成词库 — 输出 .dict.yaml

用法：
  python main.py run                         # 全流程（1→5）
  python main.py run --phase 3               # 仅过滤
  python main.py run --phase 2-4             # 分词 → 拆词
  python main.py test nlp                    # 测试分词效果
  python main.py test decompose              # 测试词条分解
  python main.py config show                 # 查看全部配置
  python main.py config set filter stop_words '["是在","各种"]'
"""

import argparse
import sys


PHASE_HELP = {
    1: "提取文本 – PDF → TXT",
    2: "分词 – TXT → 词频 JSON（支持 alinlp/llm/ollama）",
    3: "过滤 – 正则规则清洗（config/filter.json）",
    4: "短语拆词 – LLM 拆分 4+ 字词为短词（可选）",
    5: "生成词库 – 输出 Rime .dict.yaml",
}


def main():
    parser = argparse.ArgumentParser(
        description="pdf-to-dict — PDF → Rime 医学词库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="配置:    config/default/*.json  →  config/user/*.json 覆盖\n"
               "输入:    operate/in/{学科}/  →  教材.pdf + page-range.txt + segment.txt\n"
               "输出:    operate/out/{学科}/{backend}/  →  .dict.yaml",
    )
    sub = parser.add_subparsers(dest="command", metavar="命令")

    # ---- run ----
    run_parser = sub.add_parser(
        "run", help="执行流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="五阶段流水线，默认全流程执行。\n\n" +
                     "\n".join(f"  {i}. {desc}" for i, desc in PHASE_HELP.items()),
    )
    run_parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3, 4, 5], default=None,
        metavar="N",
        help="执行指定阶段（默认全流程）",
    )
    run_parser.add_argument(
        "--repdf", action="store_true",
        help="强制重新提取 PDF（忽略已有 TXT）",
    )

    # ---- test ----
    test_parser = sub.add_parser("test", help="交互式测试")
    test_parser.add_argument("test_mode", choices=["nlp", "decompose"],
                             help="nlp=分词测试, decompose=拆词测试")
    test_parser.add_argument("--backend", choices=["alinlp", "llm", "ollama"])
    test_parser.add_argument("--url")
    test_parser.add_argument("--api-key")
    test_parser.add_argument("--model")

    # ---- config ----
    config_parser = sub.add_parser("config", help="配置管理")
    config_parser.add_argument(
        "config_action", choices=["show", "set", "reset"],
        help="show=查看, set=设置, reset=恢复默认",
    )
    config_parser.add_argument(
        "config_name", nargs="?", default=None,
        help="配置名（alinlp / text_segment / term_decompose / filter / concurrency）",
    )
    config_parser.add_argument("key", nargs="?", default=None,
                               help="配置项键名")
    config_parser.add_argument("value", nargs="?", default=None,
                               help="配置项值")

    # ---- filter ----
    filter_parser = sub.add_parser(
        "filter", help="独立运行词条过滤",
        description="对已有词频 JSON 文件应用 config/filter.json 规则",
    )
    filter_parser.add_argument("input", help="词频 JSON 文件 (_terms.json)")
    filter_parser.add_argument("-o", "--output", required=True, help="输出文件")
    filter_parser.add_argument("--config", default=None, help="自定义过滤规则 JSON")

    # ---- segment ----
    seg_parser = sub.add_parser("segment", help="单次分词 CLI")
    seg_parser.add_argument("--backend", choices=["alinlp", "llm", "ollama"], default=None)
    seg_parser.add_argument("segment_args", nargs="*", help="传给 ph2_segment.py 的参数")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "run":
        from commands.run import run as run_cmd
        run_cmd(args)
    elif args.command == "test":
        from commands.test import run as test_cmd
        test_cmd(args)
    elif args.command == "config":
        from commands.config_cmd import run as config_cmd
        config_cmd(args)
    elif args.command == "filter":
        from pipeline.ph3_filter import filter_terms
        stats = filter_terms(args.input, args.output, args.config)
        print(f"  {stats['total']} → {stats['passed']} 条")
    elif args.command == "segment":
        from commands.segment_cmd import run as seg_cmd
        seg_cmd(args)


if __name__ == "__main__":
    main()
