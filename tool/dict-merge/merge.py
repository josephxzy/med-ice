import os
import sys
from pathlib import Path


def parse_dict(filepath):
    entries = {}
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_data = False
    for line in lines:
        line = line.rstrip("\n")
        if not in_data:
            if line.strip() == "...":
                in_data = True
            continue
        if not line.strip() or line.strip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 1 and parts[0]:
            text = parts[0]
            weight = 0
            if len(parts) >= 3 and parts[2].strip().isdigit():
                weight = int(parts[2].strip())
            entries[text] = weight
    return entries


def main():
    script_dir = Path(__file__).resolve().parent
    in_dir = script_dir / "in"
    out_dir = script_dir / "out"

    out_dir.mkdir(parents=True, exist_ok=True)

    dict_files = sorted(in_dir.glob("*.dict.yaml"))
    if not dict_files:
        print("错误：in 目录中没有找到 .dict.yaml 文件")
        sys.exit(1)

    merged = {}
    file_names = []
    total_entries = 0

    for fp in dict_files:
        entries = parse_dict(fp)
        file_names.append(fp.name)
        total_entries += len(entries)
        for text, weight in entries.items():
            if text not in merged or weight > merged[text]:
                merged[text] = weight

    sorted_entries = sorted(merged.items(), key=lambda x: (-x[1], x[0]))

    source_list = "\n".join(f"#   - {fn}" for fn in file_names)
    output_path = out_dir / "merged.dict.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Rime dictionary\n")
        f.write(f"# encoding: utf-8\n")
        f.write(f"#\n")
        f.write(f"# 合并医学词典\n")
        f.write(f"# 源文件:\n")
        f.write(f"{source_list}\n")
        f.write(f"#\n")
        f.write(f"---\n")
        f.write(f"name: med_merged\n")
        f.write(f"version: \"1\"\n")
        f.write(f"sort: by_weight\n")
        f.write(f"columns:\n")
        f.write(f"  - text\n")
        f.write(f"  - code\n")
        f.write(f"  - weight\n")
        f.write(f"\n...\n")
        f.write(f"# +_+\n")
        for text, weight in sorted_entries:
            f.write(f"{text}\t\t{weight}\n")

    dup_count = total_entries - len(merged)
    print(f"已合并 {len(dict_files)} 个字典文件")
    print(f"总条目: {total_entries} → 去重后: {len(merged)} (重复 {dup_count} 条)")
    print(f"输出: {output_path}")


if __name__ == "__main__":
    main()
