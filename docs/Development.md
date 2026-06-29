# 开发指南

## 构建流程

`src/` 为源文件目录（按功能分类），`build/out/` 为构建产物（扁平 Rime 部署结构）。

```bash
make -C build build
```

执行以下管线（约 90 秒完成）：

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

### 构建产物处理方式

| 处理方式 | 涉及文件 |
|---|---|
| 直接复制 | `src/schema/*`, `src/config/*`, `src/lua/**`, `src/opencc/emoji.json`, `src/opencc/others.txt`, `src/dict/*.dict.yaml`, `src/recipes/recipe.yaml`, `LICENSE` |
| 排序 + 去重 | `src/dict/cn/8105.dict.yaml`, `src/dict/cn/41448.dict.yaml`, `src/dict/cn/base.dict.yaml`, `src/dict/en/en.dict.yaml` |
| 注音 + 权重 + 排序 | `src/dict/cn/ext.dict.yaml`, `src/dict/cn/tencent.dict.yaml` |
| 源文件生成 | `src/opencc/emoji-map.txt` → `emoji.txt`; `src/dict/en/cn_en.txt` → 9 个 `cn_en_*.txt` |

## 配置文件引用链

详见 [配置引用链](./ConfigReference.md)。

构建脚本 `build/rime/config.go` 沿此引用链自动发现文件依赖，不需要在 Go 代码中硬编码文件名：

```
default.yaml → schema → dict 索引 → import_tables → 实际词库文件
```

## 构建命令

```bash
# 完整构建（需要 Go 1.24+）
make -C build build

# 代码检查（需要 yamllint + luacheck）
make -C build lint

# 仅检查 YAML
make -C build lint-yaml

# 仅检查 Lua
make -C build lint-lua

# 冒烟测试（需要 rime-cli，Linux 环境）
make -C build smoke
```

## 冒烟测试

冒烟测试通过 `rime_deployer` + `rime_api_console` 验证配置完整性和功能正确性。

测试用例在 `build/smoke/cases/med_ice/input_cases.tsv` 中，格式为：

```
case_id	schema_id	key_sequence	expected_text
```

添加新功能后，应在此文件中加入对应的测试用例。CI 中每次推送和 PR 都会自动运行。

## Plum 安装配方

项目提供多个 Plum 配方用于自动化安装：

| 配方 | 用途 |
|------|------|
| `src/recipes/full` | 完整安装 |
| `src/recipes/cn_dicts` | 仅中文词库 |
| `src/recipes/en_dicts` | 仅英文词库 |
| `src/recipes/all_dicts` | 所有词库 + OpenCC |
| `src/recipes/opencc` | 仅 OpenCC 映射 |
| `src/recipes/config` | 方案切换 + 双拼适配 |
| `src/recipes/grammar` | 万象语法模型 |
| `src/recipes/no_lua_schema` | Lua-free 方案 |
| `src/recipes/reverse_tone` | 反查音调 |

> 注意：项目重构后采用 src/ → build/out/ 架构，plum 安装暂时不可用。推荐从 [Release 页面](https://github.com/josephxzy/med-ice/releases) 下载 `full.zip`。

## 新增词库

1. 在 `src/dict/cn/` 下创建 `mywords.dict.yaml`
2. 在 `med_ice.dict.yaml` 的 `import_tables` 中添加 `- cn_dicts/mywords`
3. 运行 `make -C build build`

构建脚本会自动发现、复制、排序、去重新文件。详见 [自定义字典](./CustomDict.md)。

## 新增 Lua 脚本

1. 在 `src/lua/` 下创建 `.lua` 文件
2. 在 schema 中引用（`lua_translator@*文件名` 或 `lua_filter@*文件名`）
3. 运行 `make -C build build`

详见 [自定义 Lua 脚本](./CustomLua.md)。Translator 和 Filter 的 API 不同，注意区分。

## 构建核心库 (`build/rime/`)

| 文件 | 功能 |
|------|------|
| `config.go` | YAML 解析，从 schema/dict 自动发现文件依赖 |
| `rime.go` | 路径管理、工具函数、核心变量 |
| `check.go` | 词库校验（格式、注音、错别字） |
| `sort.go` | 排序、去重 |
| `pinyin.go` | 半自动注音（基于 gojieba） |
| `cn_en.go` | 中英混输词库生成（7 种双拼方案） |
| `emoji.go` | Emoji 映射生成与校验 |
| `polyphone.go` | 多音字检查 |
| `others.go` | 临时/调试工具 |

## CI/CD

| 工作流 | 触发条件 | 功能 |
|------|------|------|
| `release.yml` | push main / tag / workflow_dispatch | Lint → Build → Smoke → Pack → Release |
| `test.yml` | pull_request / workflow_dispatch | Lint → Build → Smoke |
