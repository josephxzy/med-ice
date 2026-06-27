# Med-Ice (med-ice)

> 本项目基于 **[雾凇拼音 (rime-ice)](https://github.com/iDvel/rime-ice)** 改编，按照 LGPL-3.0 许可证重新分发。
> 原始作者：**[Dvel](https://github.com/iDvel)**
> 上游项目：<https://github.com/iDvel/rime-ice>

Med-Ice 是一份开箱即用的简体中文 Rime 输入法配置，采用现代化目录结构，词库长期维护，功能齐全。

## 项目结构

```
med-ice/
├── README.md                   # 项目说明（本文件）
├── LICENSE                     # 开源许可证 (LGPL-3.0)
├── go.work                     # Go workspace 配置
├── .gitignore
├── AGENTS.md                   # 贡献者 & AI Agent 约定
│
├── src/                        # 源文件目录
│   ├── schema/                 # 输入方案 (.schema.yaml)
│   │   ├── med_ice.schema.yaml         # 全拼主方案
│   │   ├── double_pinyin.schema.yaml   # 自然码双拼
│   │   ├── double_pinyin_abc.schema.yaml
│   │   ├── double_pinyin_flypy.schema.yaml
│   │   ├── double_pinyin_jiajia.schema.yaml
│   │   ├── double_pinyin_mspy.schema.yaml
│   │   ├── double_pinyin_sogou.schema.yaml
│   │   ├── double_pinyin_ziguang.schema.yaml
│   │   ├── t9.schema.yaml              # 九宫格方案
│   │   ├── melt_eng.schema.yaml        # 英文混输方案
│   │   └── radical_pinyin.schema.yaml  # 拆字反查方案
│   │
│   ├── dict/                   # 词库文件
│   │   ├── med_ice.dict.yaml           # 主词库索引（导入 cn/ 下词库）
│   │   ├── melt_eng.dict.yaml          # 英文词库索引
│   │   ├── radical_pinyin.dict.yaml    # 拆字词库
│   │   ├── cn/                         # 中文词库
│   │   │   ├── 8105.dict.yaml          # 常用汉字字表 (8105 字)
│   │   │   ├── 41448.dict.yaml         # 大字表（默认不启用）
│   │   │   ├── base.dict.yaml          # 核心词库（两字词 + 常用词）
│   │   │   ├── ext.dict.yaml           # 扩展词库（多字词，含注音）
│   │   │   ├── tencent.dict.yaml       # 腾讯大词库（无注音，自动生成）
│   │   │   └── others.dict.yaml        # 容错音、方言等
│   │   └── en/                         # 英文 & 中英混合词库
│   │       ├── en.dict.yaml            # 核心英文词库
│   │       ├── en_ext.dict.yaml        # 扩展英文词库
│   │       ├── cn_en.txt               # 中英混合词源文件
│   │       ├── cn_en_abc.txt           # (自动生成)
│   │       ├── cn_en_double_pinyin.txt # (自动生成)
│   │       ├── cn_en_flypy.txt         # (自动生成)
│   │       └── ...                     # 各双拼方案的混合词库
│   │
│   ├── opencc/                 # OpenCC 映射
│   │   ├── emoji-map.txt               # Emoji 映射源文件
│   │   ├── emoji.json                  # OpenCC 配置文件
│   │   └── others.txt                  # 月份/星期/部首等特殊映射
│   │
│   ├── lua/                    # Lua 扩展脚本
│   │   ├── cold_word_drop/             # 冷词降频子系统
│   │   ├── calc_translator.lua         # 计算器
│   │   ├── date_translator.lua         # 日期/时间
│   │   ├── lunar.lua                   # 农历
│   │   ├── number_translator.lua       # 大写数字
│   │   ├── ...                         # 更多扩展
│   │   └── lunar.db                    # 农历数据库
│   │
│   ├── config/                 # 全局配置文件
│   │   ├── default.yaml                # 全局默认配置（方案列表、快捷键等）
│   │   ├── weasel.yaml                 # 小狼毫前端配置
│   │   ├── squirrel.yaml               # 鼠须管前端配置
│   │   ├── symbols_v.yaml              # v 模式符号输入（全拼）
│   │   ├── symbols_caps_v.yaml         # V 模式符号输入（双拼）
│   │   └── custom_phrase.txt           # 自定义短语
│   │
│   ├── patches/                # 自定义补丁（双拼适配等）
│   │   ├── README.md                    # 补丁使用说明
│   │   ├── double_pinyin_flypy.custom.yaml
│   │   ├── melt_eng.custom.yaml
│   │   └── radical_pinyin.custom.yaml
│   │
│   ├── recipes/                # Plum 安装配方
│   │   ├── recipe.yaml                 # 默认配方
│   │   ├── full.recipe.yaml            # 完整安装
│   │   ├── all_dicts.recipe.yaml       # 全部词库
│   │   ├── cn_dicts.recipe.yaml        # 仅中文词库
│   │   ├── en_dicts.recipe.yaml        # 仅英文词库
│   │   ├── config.recipe.yaml          # 配置 & 切换双拼
│   │   ├── grammar.recipe.yaml         # 语法模型
│   │   ├── opencc.recipe.yaml          # OpenCC 映射
│   │   ├── reverse_tone.recipe.yaml    # 反查音调
│   │   └── no_lua_schema.recipe.yaml   # Lua-free 方案
│   │
│   ├── no_lua_schema/          # Lua-free 方案变体（用于不支持 Lua 的平台）
│   │   ├── med_ice.schema.yaml
│   │   └── double_pinyin*.schema.yaml
│   │
│   └── platforms/              # 平台集成
│       ├── Hamster/                    # 仓输入法
│       └── iRime/                      # iRime
│
├── build/                      # 构建工具 & 脚本
│   ├── main.go                         # 构建主程序
│   ├── go.mod / go.sum                 # Go 模块依赖
│   ├── Makefile                        # 构建命令入口
│   ├── rime/                           # 构建核心库
│   │   ├── rime.go                     # 路径配置 & 工具函数
│   │   ├── check.go                    # 词库校验
│   │   ├── sort.go                     # 排序 & 去重
│   │   ├── pinyin.go                   # 半自动注音
│   │   ├── cn_en.go                    # 中英混输词库生成
│   │   ├── emoji.go                    # Emoji 映射生成 & 校验
│   │   ├── polyphone.go               # 多音字检查
│   │   └── others.go                   # 临时工具
│   ├── lint/                           # 代码检查（yamllint + luacheck）
│   ├── smoke/                          # 冒烟测试（rime-cli）
│   └── out/                            # 构建输出（可部署的完整 Rime 配置）
│
├── docs/                       # 文档
│   ├── Changelog.md                    # 更新日志
│   ├── Credits.md                      # 致谢
│   ├── Installation.md                 # 安装说明
│   └── assets/                         # 截图 & 图片
│
└── .github/                    # CI/CD
    ├── workflows/
    │   ├── release.yml                 # 测试 & 发布流水线
    │   └── test.yml                    # PR 冒烟测试
    └── ISSUE_TEMPLATE/
```

---

## 文件类型与扩展名

### `.schema.yaml` — 输入方案文件

定义一种输入法的完整行为：拼写规则（`speller`）、候选词翻译器（`translator`）、过滤器（`filters`）、按键绑定等。每个文件代表一个独立的输入方案，由 `schema_id` 字段唯一标识。

```
med_ice.schema.yaml
  schema_id: med_ice
  name: 雾凇拼音
  引擎管线: processor → segmentor → translator → filters
  依赖: melt_eng, radical_pinyin
```

`t9.schema.yaml` 通过 `__include: med_ice.schema.yaml:/` 继承全拼方案的全部配置，只覆写九宫格特有的部分。

### `.dict.yaml` — 词库文件

Rime 的词库格式，文件头为 YAML 元数据，正文为 Tab 分隔的词条数据。分两类：

| 类型 | 示例 | 作用 |
|------|------|------|
| **词库索引** | `med_ice.dict.yaml` | 通过 `import_tables` 引用子词库，自身也包含少量词条（如大写字母映射） |
| **数据词库** | `cn/base.dict.yaml` | 实际存放词条数据：`汉字\t拼音\t权重` |

数据词库的正文格式为 Tab 分隔：

```
# +_+
一	yi	100
你好	ni hao	150
世界	shi jie	120
```

`# +_+` 是标记行，之前的为文件头（YAML），之后的为词条数据。不同词库的列数不同：

| 列数 | 格式 | 示例文件 |
|------|------|---------|
| 2 列 | `汉字\t拼音` | `41448.dict.yaml` |
| 3 列 | `汉字\t拼音\t权重` | `base.dict.yaml` |
| 2 列 | `汉字\t权重` (无注音) | `tencent.dict.yaml` |

### `.custom.yaml` — 用户补丁文件

Rime 的**不修改原文件**覆盖配置机制。文件名格式为 `{schema_id}.custom.yaml`，放置于 Rime 用户文件夹中，重新部署后自动与原文件合并。

- 修改范围由 `patch:` 键指定
- 不需要复制整个原文件，只写要改的部分
- 项目中的 `src/patches/` 提供常用双拼适配补丁作为参考

### `.recipe.yaml` — Plum 安装配方

Plum（东风破）是 Rime 的包管理器。配方文件定义了一组安装操作：

- `install_files` — 要复制到用户文件夹的文件列表
- `download_files` — 从 URL 下载的文件
- `patch_files` — 自动生成的 `.custom.yaml` 补丁

用户通过 `bash rime-install <配方名>` 一键执行配方中定义的全部操作。

### `.txt` — 特殊文本词库

| 文件 | 格式 | 说明 |
|------|------|------|
| `cn_en.txt` | `中英混合词\t编码` | 中英混合词汇，构建时生成各双拼方案版本 |
| `custom_phrase.txt` | `编码\t短语\t权重` | 用户自定义短语，Tab 分隔 |
| `emoji-map.txt` | `Emoji 对应的中文关键词...` | Emoji 映射源文件，构建时生成 OpenCC 格式 |

### OpenCC 文件 (`.json` / `.txt`)

OpenCC（Open Chinese Convert）是中文转换框架。本项目用它实现 Emoji 映射和特殊文本替换：

| 文件 | 格式 | 说明 |
|------|------|------|
| `emoji.json` | OpenCC 配置 | 链式调用 `emoji.txt` 和 `others.txt` |
| `emoji.txt` | `关键词\t关键词 Emoji` | Emoji 映射表（由 `emoji-map.txt` 生成） |
| `others.txt` | `中文\t映射文本` | 月份、星期、部首名称等特殊映射 |

### `.lua` — Lua 扩展脚本

通过 `librime-lua` API 扩展 Rime 功能。每个脚本作为一个 translator 或 filter 嵌入到输入方案引擎管线中：

| 脚本 | 功能 | 触发方式 |
|------|------|---------|
| `calc_translator.lua` | 计算器 | 输入 `c` 或 `C` 前缀 |
| `date_translator.lua` | 日期/时间/星期 | 输入 `date`、`time`、`week` 等 |
| `lunar.lua` | 农历日期 | 输入 `lunar` |
| `number_translator.lua` | 大写数字/金额 | 输入 `R` 前缀 |
| `unicode.lua` | Unicode 字符 | 输入 `U` 前缀 |
| `uuid.lua` | UUID 生成 | 输入 `uuid` |
| `autocap_filter.lua` | 英文自动首字母大写 | 自动 |
| `v_filter.lua` | v 模式优先符号 | 输入 `v` 时 |
| `long_word_filter.lua` | 长词优先 | 自动 |
| `pin_cand_filter.lua` | 置顶候选 | 自动 |

### `.db` — SQLite 数据库

`lunar.db` 存有 1900-2100 年的农历数据，供 `lunar.lua` 查询使用。

---

## 构建流程

`src/` 为源文件目录（按功能分类），`build/out/` 为构建产物（扁平 Rime 部署结构）。运行 `make -C build build` 执行以下管线：

```
src/                           build/out/
├── dict/cn/*.dict.yaml  ───→  cn_dicts/    (排序 + 去重 + 注音 + 权重)
├── dict/en/en.dict.yaml ───→  en_dicts/    (排序 + 去重)
├── dict/en/cn_en.txt    ───→  en_dicts/cn_en*.txt  (生成所有双拼方案)
├── opencc/emoji-map.txt  ───→ opencc/emoji.txt    (生成 Emoji 映射)
├── schema/*.schema.yaml  ───→ *.schema.yaml        (直接复制)
├── config/*              ───→ *.yaml, *.txt         (直接复制)
├── lua/**                ───→ lua/                  (直接复制)
├── dict/*.dict.yaml      ───→ *.dict.yaml           (直接复制)
├── recipes/recipe.yaml   ───→ recipe.yaml           (直接复制)
├── opencc/*.json, *.txt  ───→ opencc/               (直接复制)
└── ../LICENSE            ───→ LICENSE               (直接复制)
```

### 构建产物分类

| 处理方式 | 涉及文件 |
|---|---|
| **直接复制** | `src/schema/*`, `src/config/*`, `src/lua/**`, `src/opencc/emoji.json`, `src/opencc/others.txt`, `src/dict/*.dict.yaml`, `src/recipes/recipe.yaml`, `LICENSE` |
| **排序 + 去重** | `src/dict/cn/8105.dict.yaml`, `src/dict/cn/41448.dict.yaml`, `src/dict/cn/base.dict.yaml`, `src/dict/en/en.dict.yaml` |
| **注音 + 权重 + 排序** | `src/dict/cn/ext.dict.yaml`, `src/dict/cn/tencent.dict.yaml` |
| **源文件生成** | `src/opencc/emoji-map.txt` → `emoji.txt`; `src/dict/en/cn_en.txt` → 9 个 `cn_en_*.txt` |

---

## Plum 安装配方详解

Plum（东风破）是 Rime 的包管理器，通过 `.recipe.yaml` 文件执行自动化安装、下载、打补丁。项目提供以下配方：

| 配方 | Rx 标识 | 用途 |
|------|---------|------|
| **默认** | `all` | 完整安装所有方案、词库、配置 |
| **full** | `src/recipes/full` | 同上，完整安装 |
| **cn_dicts** | `src/recipes/cn_dicts` | 仅安装中文词库 |
| **en_dicts** | `src/recipes/en_dicts` | 仅安装英文词库 |
| **all_dicts** | `src/recipes/all_dicts` | 安装中英文词库 + OpenCC |
| **opencc** | `src/recipes/opencc` | 仅安装 OpenCC 映射（Emoji 等） |
| **config** | `src/recipes/config` | 配置方案切换 + 双拼适配补丁 |
| **grammar** | `src/recipes/grammar` | 下载并配置万象语法模型 |
| **no_lua_schema** | `src/recipes/no_lua_schema` | 替换为 Lua-free 方案（无 Lua 环境时使用） |
| **reverse_tone** | `src/recipes/reverse_tone` | 反查音调配置 |

### 使用方法

```bash
# 首次安装（完整）
bash rime-install josephxzy/med-ice

# 安装指定配方
bash rime-install josephxzy/med-ice:src/recipes/config

# 安装时指定双拼方案（以 config 配方为例）
bash rime-install josephxzy/med-ice:src/recipes/config schema=double_pinyin_flypy
```

### 配方文件结构

```yaml
recipe:
  Rx: src/recipes/full          # 配方标识
  args:                          # 可选参数
    - schema=med_ice
  description: >-                # 配方说明
  install_files: >-              # 要复制的文件列表（glob 支持）
    cn_dicts/*.*
    en_dicts/*.*
  download_files:                # 要下载的文件（url → 本地路径）
    - wanxiang.gram::https://...
  patch_files:                   # 自动生成的补丁
    default.custom.yaml:
      - patch/+:
          schema_list:
            - schema: ${schema:-med_ice}
```

---

## 构建命令

```bash
# 完整构建（需要 Go 1.22+）
make -C build build

# 代码检查（需要 yamllint + luacheck）
make -C build lint

# 冒烟测试（需要 rime-cli）
make -C build smoke
```

`make -C build build` 约需 90 秒完成，请耐心等待。

---

## 安装

1. 运行 `make -C build build` 生成 `build/out/` 目录
2. 将 `build/out/` 中的所有文件复制到 Rime 用户文件夹
3. 重新部署

或下载预构建的 [Release](https://github.com/josephxzy/med-ice/releases) 压缩包。

---

## 贡献

请阅读 [AGENTS.md](./AGENTS.md) 了解代码规范和贡献流程。

## 致谢

本项目由 [雾凇拼音 (rime-ice)](https://github.com/iDvel/rime-ice) 改编而来，继承了其精校词库、输入方案和 Lua 扩展。

| 来源 | 说明 |
|------|------|
| [iDvel/rime-ice](https://github.com/iDvel/rime-ice) | 雾凇拼音，本项目的上游 |
| [mirtlecn/rime-radical-pinyin](https://github.com/mirtlecn/rime-radical-pinyin) | 部件拆字方案 |
| [rime/rime-prelude](https://github.com/rime/rime-prelude) | Rime 默认配置 |

### 许可证

本项目沿用上游 [LGPL-3.0](./LICENSE) 许可证。`radical_pinyin.*.yaml` 和 `lua/search.lua` 文件遵循上游 `mirtlecn/rime-radical-pinyin` 的许可。
