# 配置引用链

项目通过 Rime 的 YAML 配置定义各组件之间的引用关系。理解这条链是修改和扩展项目的基础。

## 完整引用链

```
default.yaml
  └─ schema_list               ← 启用哪些输入方案
       └─ rime_ice
            └─ rime_ice.schema.yaml
                 ├─ dependencies: [melt_eng, radical_pinyin]   ← 声明依赖的其他 schema
                 ├─ translator/dictionary: rime_ice             ← 挂载中文词库索引
                 ├─ melt_eng/dictionary: melt_eng              ← 挂载英文词库索引
                 └─ radical_lookup/dictionary: radical_pinyin  ← 挂载拆字词库索引

rime_ice.dict.yaml (词库索引，本身不含词条)
  └─ import_tables:
       ├─ cn_dicts/8105        → cn_dicts/8105.dict.yaml      ← 常用汉字字表
       ├─ cn_dicts/base        → cn_dicts/base.dict.yaml       ← 核心词库
       ├─ cn_dicts/ext         → cn_dicts/ext.dict.yaml        ← 扩展词库
       ├─ cn_dicts/tencent     → cn_dicts/tencent.dict.yaml    ← 大词库
       └─ cn_dicts/others      → cn_dicts/others.dict.yaml     ← 杂项

melt_eng.dict.yaml
  └─ import_tables:
       ├─ en_dicts/en_ext      → en_dicts/en_ext.dict.yaml
       └─ en_dicts/en          → en_dicts/en.dict.yaml
```

## 各层说明

### 第一层：`default.yaml` — 用户选方案

```yaml
schema_list:
  - schema: rime_ice
  - schema: double_pinyin
```

Rime 部署时根据这个列表加载对应的 `.schema.yaml` 文件。这里没有直接指定词库。

### 第二层：`*.schema.yaml` — 方案定义，指定用哪个词库

```yaml
# rime_ice.schema.yaml
schema:
  schema_id: rime_ice
  dependencies:
    - melt_eng        # 声明依赖，Rime 会确保 melt_eng.schema.yaml 先加载

engine:
  translators:
    - table_translator@melt_eng          # 英文翻译器
    - table_translator@cn_en             # 中英混输
    - table_translator@radical_lookup    # 拆字反查

translator:
  dictionary: rime_ice                    # ← 挂载 rime_ice.dict.yaml
```

- `dictionary: rime_ice` → Rime 自动在配置目录找 `rime_ice.dict.yaml`
- `dependencies: [melt_eng, radical_pinyin]` → 确保依赖的 schema 先部署
- `table_translator@melt_eng` → 引用 `melt_eng` schema 中定义的 translator

### 第三层：`*.dict.yaml` — 词库索引，声明导入哪些子词库

```yaml
# rime_ice.dict.yaml
---
name: rime_ice
import_tables:
  - cn_dicts/8105       # → cn_dicts/8105.dict.yaml
  - cn_dicts/base        # → cn_dicts/base.dict.yaml
  - cn_dicts/ext         # → cn_dicts/ext.dict.yaml
```

- `name` 必须与 schema 中 `dictionary` 的值一致
- `import_tables` 中的路径省略 `.dict.yaml` 后缀，Rime 自动补全
- 实际的词条数据在 `cn_dicts/base.dict.yaml` 等文件中

### 第四层：`cn_dicts/*.dict.yaml` — 实际词库文件

```yaml
# src/dict/cn/base.dict.yaml
---
name: base
version: "2026-01-01"
...
# +_+              ← 数据分界标记
雾凇拼音	wu song pin yin	6666
```

## 构建时如何处理这条链

`tool/build/rime/config.go` 中的 `DiscoverManifest()` 沿着这条链自动发现文件：

1. 解析 `default.yaml` → 获取 schema 列表
2. 解析每个 `*.schema.yaml` → 提取 `dictionary:` 引用的词库名
3. 解析每个 `*.dict.yaml` → 提取 `import_tables` 子词库，递归解析
4. 输出完整的文件清单，驱动复制和处理

## 添加新词库的正确方式

1. 在 `src/dict/cn/` 下创建 `mywords.dict.yaml`
2. 在 `rime_ice.dict.yaml` 的 `import_tables` 中添加 `- cn_dicts/mywords`
3. 运行 `make -C tool/build build`

构建脚本会自动发现、复制、处理新文件，不需要改 Go 代码。
