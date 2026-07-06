# -*- coding: utf-8 -*-
"""python main.py config show|set|reset — 配置管理。"""

from config.manager import ConfigManager


def run(args):
    cm = ConfigManager()

    if args.config_action == "show":
        if args.config_name:
            cm.show(args.config_name)
        else:
            for name in ["alinlp", "text_segment", "term_decompose", "filter", "concurrency"]:
                print(f"\n[{name}]")
                cm.show(name)

    elif args.config_action == "set":
        cm.set(args.config_name, args.key, parse_value(args.value))
        print(f"  {args.config_name}.{args.key} = {args.value}")

    elif args.config_action == "reset":
        if args.config_name:
            cm.reset(args.config_name)
            print(f"  已恢复 {args.config_name} 为默认值")
        else:
            cm.reset_all()
            print(f"  已恢复全部用户配置为默认值")


def parse_value(s):
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s
