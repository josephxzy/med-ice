# 自定义字典和短语

雾凇拼音支持添加自定义词库、短语和中英混输词条。修改后需要运行构建命令。

## 目录结构

```
src/dict/
├── med_ice.dict.yaml          # 主词库索引（全拼）
├── melt_eng.dict.yaml         # 英文词库索引
├── radical_pinyin.dict.yaml   # 拆字词库
├── cn/                        # 中文词库文件
│   ├── 8105.dict.yaml         # 常用汉字字表
│   ├── 41448.dict.yaml        # 大字表（默认不启用）
│   ├── base.dict.yaml         # 核心词库（两字词 + 常用词）
│   ├── ext.dict.yaml          # 扩展词库
│   ├── tencent.dict.yaml      # 腾讯词向量大词库
│   └── others.dict.yaml       # 杂项
└── en/                        # 英文词库文件
    ├── en.dict.yaml           # 核心英文词库
    ├── en_ext.dict.yaml       # 扩展英文词库
    └── cn_en.txt              # 中英混输源文件

src/config/
└── custom_phrase.txt          # 自定义短语
```

---

## 自定义短语

自定义短语适合添加邮箱、手机号、常用短句等，**权重最高，排在候选项最前面**。

### 格式

`src/config/custom_phrase.txt` 使用 Tab 分割：

```
词汇<Tab>编码<Tab>权重
```

示例：

```
一个	ig	1
邮箱	youxiang	2
```

- **词汇**：要输出的文字
- **编码**：拼音（可以是非完整编码，如 `ig`）
- **权重**：数字越大越靠前

> 用非完整编码的好处是不会参与造词。如果想让某个完整拼音的词汇置顶，建议用 `pin_cand_filter.lua`。

### 使用自己的短语文件

1. 创建自己的 `.txt` 文件（放在 Rime 用户配置目录，不是项目仓库）
2. 通过 patch 修改 `med_ice.schema.yaml` 中的引用：

```yaml
# med_ice.custom.yaml（放在用户配置目录）
patch:
  custom_phrase/user_dict: my_phrases  # 指向 my_phrases.txt
```

### 双拼自定义短语

双拼方案的默认自定义短语文件是 `custom_phrase_double.txt`（需手动创建）。对应方案中的 `custom_phrase/user_dict` 配置。

---

## 添加自定义词库

### 方式一：挂载外部词库（推荐）

1. 创建自己的词库文件，如 `my_dict.dict.yaml`，放在 Rime 用户配置目录
2. 在 `src/dict/med_ice.dict.yaml` 的 `import_tables` 中添加引用：

```yaml
import_tables:
  - cn_dicts/8105
  - cn_dicts/base
  - cn_dicts/ext
  - cn_dicts/tencent
  - cn_dicts/others
  - my_dict           # ← 新增：挂载 my_dict.dict.yaml
```

3. 运行构建：`make -C build build`

### 方式二：直接添加到项目词库

如果要贡献到项目中，在 `src/dict/cn/` 下新建词库文件：

**中文词库格式** (`my_words.dict.yaml`)：

```yaml
# Rime dictionary
# encoding: utf-8

---
name: my_words
version: "2026-01-01"
import_tables:
  - cn_dicts/my_words
...

# +_+
词汇	zhu yin	100
另一个词	ling yi ge ci	50
```

- `# +_+` 标记之后是词条数据
- 每行格式：`汉字<Tab>拼音（空格分隔）<Tab>权重`
- 权重默认 100，数字越大排序越靠前

然后在 `med_ice.dict.yaml` 中引用：

```yaml
import_tables:
  # ...
  - cn_dicts/my_words  # 新增
```

**英文词库格式** (`my_en.dict.yaml`)：

```yaml
# Rime dictionary
# encoding: utf-8

---
name: my_en
version: "2026-01-01"
import_tables:
  - en_dicts/my_en
...

# +_+
Apple	Apple
iPhone	iPhone
```

然后在 `melt_eng.dict.yaml` 中引用。

---

## 中英混输

中英混输允许直接输入 `Xguang` 得到 `X光`。修改 `src/dict/en/cn_en.txt`：

```
X光	X guang
3D	3 D
```

每行格式：`中文词<Tab>拼音（空格分隔）`

修改后运行 `make -C build build`，脚本会自动生成各个双拼方案的混输词库。

---

## 构建与验证

修改任何词库文件后：

```bash
make -C build build
```

构建过程会：
1. 自动注音（`ext.dict.yaml` 中没有注音的词条）
2. 补充权重
3. **排序和去重**（重复词条以权重最高的为准）
4. 生成中英混输词库
5. 生成 Emoji 映射

> 构建脚本至少需要 90 秒，请耐心等待。如有错误或警告，按提示修改后再重新构建。

---

## 注意事项

- **不要直接修改** `build/out/` 下的文件，这些是构建产物，会被覆盖
- 修改中文词条写入 `src/dict/cn/` 下对应文件，不要直接改 `src/dict/med_ice.dict.yaml`（它只是索引）
- 修改英文词条写入 `src/dict/en/` 下对应文件
- 含有多音字的词条必须放到 `ext.dict.yaml`（脚本会自动处理注音）
- 大词库（`tencent.dict.yaml`）**不能包含注音**，脚本会自动补充
- 修改后必须运行 `make -C build build` 进行排序和校验
- 用 `git grep "目标词" src/dict/` 确认词条是否已存在，避免重复
