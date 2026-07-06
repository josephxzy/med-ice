# 开发指南

## 项目架构

```
src/                           # 源文件（按功能分类）
├── schema/*.schema.yaml       # 输入方案
├── dict/
│   ├── cn/*.dict.yaml         # 中文词库源文件
│   ├── en/*.yaml / *.txt      # 英文词库源文件
│   └── *.dict.yaml            # 词库索引（声明 import_tables）
├── opencc/                    # OpenCC 映射（Emoji 等）
├── lua/                       # Lua 扩展脚本
├── config/                    # 全局配置文件
├── recipes/                   # Plum 安装配方
└── patches/                   # 定制补丁

tool/
├── build/                     # 构建脚本 & 工具（Go）
│   ├── main.go                # 构建入口
│   ├── rime/                  # 核心模块
│   └── smoke/                 # 冒烟测试
├── pdf-to-dict/               # PDF → 词库工具
├── sogou-med-dict/            # 搜狗医学词库工具
└── dict-merge/                # 词库合并工具
```

## 快速开始

```bash
# 完整构建（需 Go 1.24+，约 90 秒）
make -C tool/build build

# 代码检查（需 yamllint + luacheck）
make -C tool/build lint

# 冒烟测试（Linux，需要 librime 运行环境）
SMOKE_ALLOW_DESTRUCTIVE=1 make -C tool/build smoke
```

## 构建流程

`make -C tool/build build` 执行以下步骤：

| 步骤 | 说明 |
|------|------|
| 1. 复制 | `src/` → `tool/build/out/`，schema、dict、config、lua、opencc 等直接复制 |
| 2. Emoji | `src/opencc/emoji-map.txt` → 生成 `out/opencc/emoji.txt` |
| 3. 中英混合 | `src/dict/en/cn_en.txt` → 生成 8 种双拼方案的 `en_dicts/cn_en_*.txt` |
| 4. 注音 | 为 `NeedPinyin` 标记的词库（ext + 所有 med_\*）自动补充拼音 |
| 5. 权重 | 为 `NeedWeight` 标记的词库统一设置默认权重 |
| 6. 检查 | 校验词库格式、注音正确性、错别字、多音字 |
| 7. 排序去重 | 按拼音排序、去重，重写 `fixColumnsHeader` |

### 构建产物处理方式

| 处理方式 | 文件 |
|----------|------|
| 直接复制 | `src/schema/*`、`src/config/*`、`src/lua/**`、`src/dict/*.dict.yaml`、OpenCC 数据 |
| 排序 + 去重 | 8105、base、ext、tencent、med_\* 等词库 |
| 注音 | ext、med_\* 词库（自动补全拼音） |
| 源文件生成 | Emoji 映射、中英混合词库 |

## 词库制作工具

med-ice 提供了一套从原始数据到 Rime 词库的完整工具链。

### pdf-to-dict：PDF 教材 → 医学词库

从可编辑 PDF 提取医学术语，支持批量处理、多后端并发分词、断点续转。

```bash
cd tool/pdf-to-dict
python run.py                    # 交互式运行
python main.py run --help        # CLI 查看选项
python main.py test --help       # 测试命令
```

**五阶段流水线**（`pipeline/`）：

| 阶段 | 模块 | 功能 |
|------|------|------|
| Phase 1 | `ph1_extract.py` | PDF → TXT 文本提取 |
| Phase 2 | `ph2_segment.py` | 分词（支持阿里 NLP、Ollama LLM 等多后端） |
| Phase 3 | `ph3_filter.py` | 基于词性、词长、停用词等规则过滤 |
| Phase 4 | `ph4_decompose.py` | 长词拆解为子术语 |
| Phase 5 | `ph5_dict.py` | 自动注音并输出 Rime .dict.yaml 格式 |

**多后端支持**（`backends/`）：阿里云 NLP、本地 LLM（Ollama）。

### sogou-med-dict：搜狗医学细胞词库

```bash
cd tool/sogou-med-dict
```

| 工具 | 功能 |
|------|------|
| `sogou-downloader/` | 从搜狗官网批量下载医学分类细胞词库（`.scel`） |
| `scel2txt/` | 将 `.scel` 格式转换为纯文本词条，供构建工具进一步处理 |

### dict-merge：多词库合并去重

将多个 `.dict.yaml` 词库合并为一个，去重时保留较高权重。

```bash
cd tool/dict-merge
# 1. 将要合并的词库文件放入 in/ 目录
# 2. 运行合并
python merge.py
# 3. 合并结果输出到 out/merged.dict.yaml
```

合并规则：同一词条在多个文件中出现时，取最大权重。最终结果按权重降序、文本升序排列。

## 冒烟测试

冒烟测试通过 `rime_deployer` + `rime_api_console` 验证输入方案的正确性。

### 测试用例

测试用例定义在 `tool/build/smoke/cases/` 下，格式为 TSV：

```
case_id	schema_id	key_sequence	expected_text
基础：中文输入	rime_ice	wusongpinyin{space}	雾凇拼音
```

按键序列使用 Rime 标准语法：`{space}`、`{Return}`、`{Down}`、`{Control+Shift+Return}` 等。

### 运行测试

```bash
# 本地运行（需先执行 make build 生成 out/ 目录）
SMOKE_ALLOW_DESTRUCTIVE=1 make -C tool/build smoke

# 单独测试某个输入案例
cd tool/build/out
rime_deployer --build . .
RIME_SHARED_DATA_DIR=. RIME_USER_DATA_DIR=. rime_api_console
# > select schema rime_ice
# > wusongpinyin{space}
# > exit
```

### CI 中的冒烟测试

CI 不使用外部预编译包，而是从源码构建整个测试环境：

1. 安装编译依赖（cmake、boost、leveldb、marisa、opencc、yaml-cpp 等）
2. 从 `github.com/rime/librime` 克隆源码
3. `patch_api_console.py` 注入两个关键修复：
    - 将已废弃的 `simulate_key_sequence` 替换为 `process_key` 调用
    - 在 `traits` 中设置 `shared_data_dir` / `user_data_dir`（librime 不读取环境变量）
4. 加载 Debian 预编译的 `librime-lua.so` 插件（外部插件模式）
5. 编译 → 运行 smoke

## 新增词库

1. 在 `src/dict/cn/` 下创建 `mywords.dict.yaml`：

```yaml
# Rime dictionary
# encoding: utf-8
---
name: mywords
version: "1"
sort: by_weight
columns:
  - text
  - code
  - weight
...
# +_+
词汇	ci hui	100
```

2. 如需挂载到输入方案，在 `src/dict/med_ice.dict.yaml` 或 `rime_ice.dict.yaml` 的 `import_tables` 中添加：

```yaml
import_tables:
  - cn_dicts/mywords
```

3. 运行构建：

```bash
make -C tool/build build
```

构建脚本会自动发现、复制、注音、排序、去重新文件。

## 新增输入方案

1. 在 `src/schema/` 下创建 `my_schema.schema.yaml`
2. 在 `src/config/default.yaml` 的 `schema_list` 中添加
3. 如果是新词库，在方案或词库索引中声明 `import_tables`
4. 运行构建

## 新增 Lua 脚本

1. 在 `src/lua/` 下创建 `.lua` 文件
2. 在 schema 中引用：
   - `lua_translator@*文件名` — 翻译器（产生候选）
   - `lua_filter@*文件名` — 过滤器（修改候选）
   - `lua_processor@*文件名` — 处理器（响应按键）
3. 运行 `make -C tool/build build`

## 构建核心库

`tool/build/rime/` 下的 Go 模块：

| 文件 | 功能 |
|------|------|
| `config.go` | 解析 YAML，从 schema/dict 自动发现文件依赖（无需硬编码文件名） |
| `rime.go` | 路径管理、词库词集加载、全局变量 |
| `check.go` | 词库校验：格式、注音、错别字、多音字 |
| `sort.go` | 排序、去重、columns header 自动修正 |
| `pinyin.go` | 半自动注音（基于 gojieba 分词 + 结巴词库拼音映射） |
| `cn_en.go` | 中英混输词库生成（8 种双拼方案） |
| `emoji.go` | Emoji 映射生成与校验 |
| `polyphone.go` | 多音字检查 |

### 配置文件引用链

构建脚本沿以下链自动发现依赖：

```
default.yaml → schema → dict 索引 → import_tables → 实际词库文件
```

## CI/CD

| 工作流 | 触发条件 | 功能 |
|--------|----------|------|
| `test.yml` | PR / workflow_dispatch | Lint → Build → Smoke |
| `release.yml` | push main / tag / workflow_dispatch | Lint → Build → Smoke → 打包 → Release/Nightly |

CI 中冒烟测试的 rime 工具链（deployer + api_console + lua 插件）全部从源码构建，缓存 `/opt/rime-cli` 加速后续运行。Lua 插件通过将 `librime-lua` 源码放入 `plugins/lua/` 由 cmake 自动发现并同步编译，避免版本不兼容。
