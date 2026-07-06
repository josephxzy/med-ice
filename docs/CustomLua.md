# 自定义 Lua 脚本

雾凇拼音通过 [librime-lua](https://github.com/hchunhui/librime-lua) 插件实现了很多高级功能（日期、农历、计算器、Unicode 等）。你也可以编写自己的 Lua 脚本来扩展功能。

## 目录结构

所有 Lua 脚本放在 `src/lua/` 下：

```
src/lua/
├── date_translator.lua    # 日期/时间/星期
├── lunar.lua              # 农历
├── lunar.db               # 农历数据库
├── calc_translator.lua    # 计算器
├── number_translator.lua  # 数字大写
├── unicode.lua            # Unicode 输入
├── uuid.lua               # UUID 生成
├── autocap_filter.lua     # 英文自动大写
├── v_filter.lua           # v 模式 symbols 优先
├── pin_cand_filter.lua    # 置顶候选项
├── corrector.lua          # 错音错字提示
├── cold_word_drop/        # 冷词降权脚本
├── ...
└── my_script.lua          # ← 你自定义的脚本
```

## 快速开始

### 1. 创建 Lua 脚本

在 `src/lua/` 下创建一个 `.lua` 文件。**Translator 和 Filter 的 API 不同**，请参考对应模板。

#### Translator 模板（产生新候选项）

```lua
-- my_translator.lua
-- 输入 "test" 返回 "测试成功" 候选项
local M = {}

function M.init(env)
    -- 读取方案配置（可选）
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
end

function M.func(input, seg, env)
    -- input: 输入码
    -- seg: 当前 segment
    -- 产生候选项用 yield(Candidate(...))
    if input == "test" then
        yield(Candidate("", seg.start, seg._end, "测试成功", ""))
    end
end

return M
```

完整 API 参考：[librime-lua Wiki](https://github.com/hchunhui/librime-lua/wiki/Scripting)

#### Filter 模板（处理已有候选项）

```lua
-- my_filter.lua
-- 将所有候选项文字转为大写（一个无实际意义的示例）
local function my_filter(input, env)
    -- input:iter() 遍历所有候选项
    -- 用 yield(cand) 传递候选项
    for cand in input:iter() do
        yield(cand)  -- 原样传递 = 不做任何修改
    end
end

return my_filter
```

如需读取方案配置（如 `long_word_filter.lua`、`reduce_english_filter.lua`），使用 `M.init(env)` + `M.func(input)` 模式：

```lua
-- my_filter_with_config.lua
local M = {}

function M.init(env)
    local config = env.engine.schema.config
    env.name_space = env.name_space:gsub("^*", "")
    -- 读取自定义配置
    M.count = config:get_int(env.name_space .. "/count") or 2
end

function M.func(input)
    for cand in input:iter() do
        yield(cand)
    end
end

return M
```

> **Translator vs Filter 关键区别：**
> 
> | | Translator | Filter |
> |---|---|------|
> | 函数签名 | `func(input, seg, env)` | `func(input)` 或 `func(input, env)` |
> | 产生候选 | `yield(Candidate(...))` 新建 | `input:iter()` 遍历，`yield(cand)` 传递 |
> | 返回值 | `return M`（`{init, func}`） | 简单场景直接 `return fn`，需配置用 `return M` |
> | schema 注册 | `lua_translator@*文件名` | `lua_filter@*文件名` |

### 2. 在方案中注册

打开 `src/schema/rime_ice.schema.yaml`，在对应位置引用：

```yaml
engine:
  translators:
    - lua_translator@*my_translator    # translator

  filters:
    - lua_filter@*my_filter            # filter
```

- **`translator`**：产生候选项（日期、农历、计算器、Unicode、UUID 等）
- **`filter`**：处理已有候选项（置顶、纠错、降权、自动大写、v 模式等）

星号 `*` 前缀表示从文件自动加载，**不需要手动修改 `rime.lua`**。

### 3. 运行构建

```bash
make -C tool/build build
```

### 4. 验证

构建后 Rime 会加载 `tool/build/out/lua/` 下的脚本。可以用冒烟测试：

```bash
make -C tool/build smoke
```

在 `tool/build/smoke/cases/rime_ice/input_cases.tsv` 中添加测试用例。

## 替换已有 Lua

如果想修改某个已有功能（如日期格式），建议新建文件替换，而不直接修改原文件，这样更新时不会被覆盖。

例如，修改日期格式，创建 `my_date_translator.lua`（可以从 `date_translator.lua` 复制修改），然后在 schema 中替换：

**方式一（推荐）：用 patch 文件**

创建 `rime_ice.custom.yaml` 放到 Rime 用户配置目录（不是项目仓库）：

```yaml
# rime_ice.custom.yaml
patch:
  engine/translators/@2: lua_translator@*my_date_translator
  # @2 是 date_translator 在 translators 列表中的索引（从 0 开始）
```

**方式二：直接修改 schema**

```yaml
engine:
  translators:
    - punct_translator
    - script_translator
    - lua_translator@*my_date_translator  # ← 替换原 date_translator
    - lua_translator@*lunar
    # ...
```

> 注意：方式一的索引用 `@数字` 表示在列表中的位置，如果后续更新后列表顺序变了，索引可能失效。此时需要重新确认位置，或改用方式二（复制完整列表）。

## 现有脚本功能速览

| 脚本 | 类型 | 功能 | 触发方式 |
|------|------|------|----------|
| `date_translator.lua` | translator | 日期、时间、星期 | `rq` / `time` / `xq` 等 |
| `lunar.lua` | translator | 农历查询 | `N` + 日期 |
| `calc_translator.lua` | translator | 计算器 | `cC` + 表达式 |
| `number_translator.lua` | translator | 数字金额大写 | `R` + 数字 |
| `unicode.lua` | translator | Unicode 输入 | `U` + 码点 |
| `uuid.lua` | translator | UUID 生成 | `uuid` |
| `autocap_filter.lua` | filter | 英文自动大写 | 自动 |
| `v_filter.lua` | filter | v 模式符号优先 | 自动 |
| `corrector.lua` | filter | 错音错字提示 | 自动（Ctrl+Shift+Enter 查看） |
| `pin_cand_filter.lua` | filter | 置顶候选项 | 自动 |

## 调试

如果 Lua 脚本不生效，可以启用 `debuger.lua` 查看日志。在 schema 的 `engine/translators` 中加入：

```yaml
- lua_translator@*debuger
```

或参考 [librime-lua 调试文档](https://github.com/hchunhui/librime-lua/wiki/Scripting#debugging)。
