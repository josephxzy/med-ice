# 项目结构

## 目录总览

```
med-ice/
├── README.md
├── LICENSE                     # LGPL-3.0
├── go.work                     # Go workspace
├── AGENTS.md                   # 贡献者 & AI Agent 约定
│
├── src/                        # 源文件（开发在此编辑）
│   ├── schema/                 # 输入方案 (.schema.yaml)
│   ├── dict/                   # 词库 (cn/ 中文, en/ 英文)
│   ├── opencc/                 # OpenCC 映射
│   ├── lua/                    # Lua 扩展脚本
│   ├── config/                 # 全局配置
│   ├── patches/                # 用户补丁参考
│   ├── recipes/                # Plum 配方
│   ├── no_lua_schema/          # Lua-free 方案变体
│   └── platforms/              # 平台集成
│
├── tool/build/                      # 构建工具（Go）
│   ├── main.go                 # 入口
│   ├── rime/                   # 构建核心库
│   ├── lint/                   # 代码检查
│   ├── smoke/                  # 冒烟测试
│   └── out/                    # 构建产物（可部署的 Rime 配置）
│
├── docs/                       # 开发文档
│   └── assets/                 # 截图
│
└── .github/                    # CI/CD
    └── workflows/
```

## src/ → tool/build/out/ 架构

项目采用源文件与构建产物分离的设计：

- **`src/`** — 按功能分类的源文件，适合开发和版本管理
- **`tool/build/out/`** — 构建产物，扁平的 Rime 部署结构，适合直接复制到用户目录

运行 `make -C tool/build build` 后，`tool/build/out/` 中的文件结构即为 Rime 期望的配置目录结构，可以直接部署。

详见 [开发指南](./Development.md#构建流程)。

## 各目录说明

### `src/schema/` — 输入方案

定义输入法的完整行为：拼写规则、翻译器、过滤器、按键绑定。

| 文件 | 方案 |
|------|------|
| `rime_ice.schema.yaml` | 全拼（主方案） |
| `double_pinyin.schema.yaml` | 自然码双拼 |
| `double_pinyin_flypy.schema.yaml` | 小鹤双拼 |
| `double_pinyin_mspy.schema.yaml` | 微软双拼 |
| `double_pinyin_sogou.schema.yaml` | 搜狗双拼 |
| `double_pinyin_ziguang.schema.yaml` | 紫光双拼 |
| `double_pinyin_abc.schema.yaml` | 智能 ABC 双拼 |
| `double_pinyin_jiajia.schema.yaml` | 拼音加加双拼 |
| `t9.schema.yaml` | 九宫格（继承 rime_ice） |
| `melt_eng.schema.yaml` | 英文混输 |
| `radical_pinyin.schema.yaml` | 拆字反查 |

### `src/dict/` — 词库

**中文词库** (`cn/`)：

| 文件 | 格式 | 说明 |
|------|------|------|
| `8105.dict.yaml` | 3 列 (字\|拼音\|权重) | 常用汉字字表 |
| `41448.dict.yaml` | 2 列 (字\|拼音) | 大字表，默认不启用 |
| `base.dict.yaml` | 3 列 | 核心词库（两字词 + 常用词） |
| `ext.dict.yaml` | 3 列 | 扩展词库（含多音字） |
| `tencent.dict.yaml` | 2 列 (词\|权重) | 大词库，无注音，脚本自动生成 |
| `others.dict.yaml` | 3 列 | 容错音、方言等 |

**英文词库** (`en/`)：

| 文件 | 说明 |
|------|------|
| `en.dict.yaml` | 核心英文词库 |
| `en_ext.dict.yaml` | 扩展英文词库 |
| `cn_en.txt` | 中英混合词汇源文件 |

**词库索引** (`dict/` 根目录)：

| 文件 | 挂载 |
|------|------|
| `rime_ice.dict.yaml` | cn_dicts/ 下所有中文词库 |
| `melt_eng.dict.yaml` | en_dicts/ 下所有英文词库 |
| `radical_pinyin.dict.yaml` | 拆字词库 |

### `src/lua/` — Lua 扩展

| 脚本 | 类型 | 功能 |
|------|------|------|
| `date_translator.lua` | translator | 日期/时间/星期 |
| `lunar.lua` | translator | 农历查询 |
| `calc_translator.lua` | translator | 计算器 |
| `number_translator.lua` | translator | 数字大写 |
| `unicode.lua` | translator | Unicode 输入 |
| `uuid.lua` | translator | UUID 生成 |
| `force_gc.lua` | translator | 暴力 GC |
| `autocap_filter.lua` | filter | 英文自动大写 |
| `v_filter.lua` | filter | v 模式符号优先 |
| `corrector.lua` | filter | 错音错字提示 |
| `pin_cand_filter.lua` | filter | 置顶候选项 |
| `long_word_filter.lua` | filter | 长词优先 |
| `reduce_english_filter.lua` | filter | 英文降权 |
| `search.lua` | filter | 拆字辅码 |

详见 [自定义 Lua 脚本](./CustomLua.md)。

### `src/config/` — 全局配置

| 文件 | 说明 |
|------|------|
| `default.yaml` | 方案列表、快捷键、全局行为 |
| `weasel.yaml` | 小狼毫前端配置 |
| `squirrel.yaml` | 鼠须管前端配置 |
| `symbols_v.yaml` | v 模式符号输入 |
| `symbols_caps_v.yaml` | V 模式符号输入 |
| `custom_phrase.txt` | 自定义短语 |

### `src/opencc/` — OpenCC 映射

| 文件 | 说明 |
|------|------|
| `emoji.json` | OpenCC 配置，链式加载 emoji.txt 和 others.txt |
| `emoji-map.txt` | Emoji 映射源文件 |
| `emoji.txt` | Emoji 映射表（由 emoji-map.txt 生成） |
| `others.txt` | 月份/星期/部首等特殊映射 |

## 文件类型参考

### `.schema.yaml` — 输入方案文件

定义一种输入法的完整行为。核心属性：
- `schema_id` — 方案唯一标识
- `engine` — 引擎管线（processor → segmentor → translator → filters）
- `translator/dictionary` — 挂载的词库
- `dependencies` — 依赖的其他 schema

### `.dict.yaml` — 词库文件

分两类：
- **词库索引**：通过 `import_tables` 引用子词库
- **数据词库**：实际存放词条，`# +_+` 标记之后为数据区

| 列数 | 格式 | 示例 |
|------|------|------|
| 2 列 | `汉字\t拼音` | `41448.dict.yaml` |
| 3 列 | `汉字\t拼音\t权重` | `base.dict.yaml` |
| 2 列 | `汉字\t权重` (无注音) | `tencent.dict.yaml` |

### `.custom.yaml` — 用户补丁

不修改原文件即可覆盖配置。文件名格式 `{schema_id}.custom.yaml`，放入用户目录后自动合并。

### `.txt` — 文本词库

| 文件 | 格式 |
|------|------|
| `cn_en.txt` | `中英混合词\t编码` |
| `custom_phrase.txt` | `编码\t短语\t权重` |
| `emoji-map.txt` | `Emoji 关键词1 关键词2 ...` |
