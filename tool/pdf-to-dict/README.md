# pdf-to-dict：PDF → Rime 词库

从可编辑 PDF 生成 Rime 医学词库，支持批量处理、多后端并发分词、独立子窗口、断点续转。

## 目录结构

```
pdf-to-dict/
├── main.py                          # CLI 入口
├── run.py                           # 向后兼容入口
├── commands/                        # 子命令
│   ├── run.py
│   ├── test.py
│   ├── config_cmd.py
│   └── segment_cmd.py
├── config/
│   ├── manager.py                   # ConfigManager
│   ├── default/                     # 默认配置
│   │   ├── alinlp.json
│   │   ├── text_segment.json
│   │   ├── term_decompose.json
│   │   ├── filter.json
│   │   └── concurrency.json
│   └── user/                        # 用户配置（覆盖默认）
├── pipeline/                        # 五阶段处理 + API 模块
│   ├── orchestrator.py              # 编排器
│   ├── ph1_extract.py               # Phase 1: PDF → TXT
│   ├── ph2_segment.py               # Phase 2: 分词
│   ├── ph3_filter.py                # Phase 3: 过滤
│   ├── ph4_decompose.py             # Phase 4: 拆词
│   ├── ph5_dict.py                  # Phase 5: 词库
│   ├── alinlp_ws.py                 # 阿里 NLP API
│   ├── llm_segment.py               # LLM 分词
│   ├── term_decompose.py            # AI 拆词
│   └── deepseek_controller.py       # API 封装
├── backends/                        # 分词后端（测试用）
│   ├── base.py / factory.py
│   └── alinlp.py / llm.py / ollama.py
├── utils/                           # 共享工具
│   ├── paths.py                     # 路径常量
│   ├── state.py                     # IPC 进度
│   └── text.py                      # 清洗/分块/停用词
├── tokenizer/                       # tokenizer
├── tests/                           # 测试
└── operate/
    ├── in/                          # 输入（PDF + page-range.txt + segment.txt）
    └── out/                         # 输出（词库 + 中间文件）
```

## 快速开始

```bash
cd tool/pdf-to-dict
pip install pdfplumber

# 将 PDF 放入 operate/in/{学科名}/，添加 page-range.txt 和 segment.txt（可选）
python main.py run                    # 全流程（推荐）
python main.py run --phase 2          # 仅分词
python main.py run --phase 5          # 仅生成词库
```

## 命令

```bash
python main.py run                        # 全流程（推荐）
python main.py run --phase {1,2,3,4,5}   # 单阶段
python main.py run --repdf                # 强制重提取 PDF
python main.py test nlp                   # 分词测试
python main.py test decompose             # 拆词测试
python main.py config show                # 查看全部配置
python main.py config set <file> <key> <value>  # 设置配置
python main.py config reset [file]        # 恢复默认
python main.py segment <text>             # 单次分词
python main.py filter terms.json -o out.json  # 独立过滤
```


## 旧式入口 (run.py)

`run.py` 仅向后兼容，支持以下旧式 `--flag` 风格参数：

```bash
# 执行流水线
python run.py                        # 全流程
python run.py --phase 2              # 仅分词
python run.py --phase 5              # 仅生成词库
python run.py --repdf                # 强制重提取 PDF

# 分词后端
python run.py --set-backend llm      # 切换为 LLM 分词

# 交互测试
python run.py --test-nlp             # 测试分词效果
python run.py --test-decompose       # 测试词条分解

# 配置
python run.py --reset-config         # 恢复全部默认配置
```

> 新脚本请用 `python main.py`，支持子命令且帮助完善。

## 配置

### 全局并发

```bash
python main.py config show concurrency
python main.py config set concurrency max_parallel_books 3
python main.py config set concurrency segment.llm 20
python main.py config set concurrency decompose 10
```

### 分词后端

```bash
python main.py config set text_segment backend llm
python main.py config set text_segment backend alinlp
python main.py config set text_segment llm.api_key sk-xxx
python main.py config set text_segment llm.model deepseek-chat
```

## 按学科指定分词工具

在 `operate/in/{学科}/segment.txt` 中写入分词工具名（每行一个）：

```
alinlp
llm
```

- 无此文件 → 使用全局默认后端
- 指定多个 → 并发分词，各自独立子目录：

```
operate/out/药理学/
  药理学.txt
  alinlp/                           # alinlp 产物
    药理学_terms.json
    药理学_decompose.json
    med_药理学.dict.yaml
  llm/                              # llm 产物
    药理学_terms.json
    药理学_decompose.json
    med_药理学.dict.yaml
```

## pipeline_state.json IPC

子进程通过 `.pipeline_state.json` 向主进程汇报进度：

```json
{"phase": 2, "phase_name": "分词", "percent": 45.2, "done": 963, "total": 2130, "terms": 1488}
```

## 分步使用

```bash
# 阶段 1: PDF → TXT
python pipeline/ph1_extract.py operate/in/教材.pdf operate/out/教材/教材.txt

# 阶段 2: TXT → 词频
python pipeline/ph2_segment.py operate/out/教材/教材.txt -o out.json --backend llm

# 阶段 3: 词条过滤
python pipeline/ph3_filter.py out.json -o out.json

# 阶段 4: AI 子词分解
python pipeline/ph4_decompose.py out.json -o decompose.json

# 阶段 5: 词频 → dict.yaml
python pipeline/ph5_dict.py out.json --name med_教材 --out-dir operate/out/教材
```
