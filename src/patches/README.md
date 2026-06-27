# 自定义补丁 (Patches)

本目录提供常用的 Rime 自定义补丁（`.custom.yaml`），用于在双拼方案下适配拼写派生规则。

## 什么是补丁

Rime 通过 `.custom.yaml` 机制允许用户在**不修改原文件**的前提下覆盖或追加配置。文件名格式为 `{schema_id}.custom.yaml`，放置于 Rime 用户文件夹中，重新部署后生效。

## 使用方式

将需要的 `.custom.yaml` 文件复制到 **Rime 用户文件夹** 中，重新部署即可。无需修改仓库内的原始方案文件。

## 补丁说明

| 文件 | 作用 | 适用场景 |
|------|------|---------|
| `double_pinyin_flypy.custom.yaml` | 清空 preedit_format，使输入时显示双拼编码而非全拼 | 小鹤双拼用户（其他双拼改文件名前缀即可） |
| `melt_eng.custom.yaml` | 切换英文混输的拼写派生规则为双拼方案 | 使用双拼 + 英文混输的用户 |
| `radical_pinyin.custom.yaml` | 切换部件拆字的拼写派生规则为双拼方案 | 使用双拼 + 拆字反查的用户 |

## 示例：小鹤双拼用户如何适配

1. 将 `double_pinyin_flypy.custom.yaml` 复制到用户文件夹
2. 将 `melt_eng.custom.yaml` 复制到用户文件夹，确认 `__include` 行为小鹤双拼
3. 将 `radical_pinyin.custom.yaml` 复制到用户文件夹，确认 `__include` 行为小鹤双拼
4. 重新部署

## 其他双拼方案

将文件名中的 `flypy` 替换为对应方案 ID 即可：

| 方案 | 文件前缀 |
|------|---------|
| 自然码双拼 | `double_pinyin` |
| 小鹤双拼 | `double_pinyin_flypy` |
| 微软双拼 | `double_pinyin_mspy` |
| 搜狗双拼 | `double_pinyin_sogou` |
| 智能 ABC 双拼 | `double_pinyin_abc` |
| 拼音加加双拼 | `double_pinyin_jiajia` |
| 紫光双拼 | `double_pinyin_ziguang` |
