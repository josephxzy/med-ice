# Med-Ice (med-ice)

> 基于 **[雾凇拼音 (rime-ice)](https://github.com/iDvel/rime-ice)** 改编，LGPL-3.0 许可证。
> 上游项目：<https://github.com/iDvel/rime-ice>

Med-Ice 是一份开箱即用的简体中文 Rime 输入法配置，长期维护，功能齐全。

## 功能

| 分类 | 功能 |
|------|------|
| **基础** | 全拼 / 七种双拼 / 九宫格；Emoji；中英混输；拆字反查；符号输入 |
| **扩展** | 日期时间、农历、计算器、数字大写、Unicode、UUID |
| **智能** | 英文自动大写、长词优先、错音错字提示、置顶候选、英文降权 |
| **词库** | 精校中文词库 + 英文词库 + 腾讯大词库，持续维护 |

![输入方案](docs/assets/基础-方案设定_compressed.webp)

## 快速安装

1. 前往 [Release](https://github.com/josephxzy/med-ice/releases) 下载最新 `full.zip`
2. 解压所有文件到 Rime 配置目录：
   - **Windows 小狼毫**：`%APPDATA%\Rime`
   - **macOS 鼠须管**：`~/Library/Rime`
   - **Linux**：`~/.config/ibus/rime` 或 `~/.local/share/fcitx5/rime`
3. 右键托盘图标 → **重新部署**

> 详细说明和更多安装方式见 [安装指南](docs/Installation.md)

## 文档

| 文档 | 说明 |
|------|------|
| [安装指南](docs/Installation.md) | 各平台安装、plum、Git 安装 |
| [自定义字典](docs/CustomDict.md) | 添加词库、自定义短语、中英混输 |
| [自定义 Lua](docs/CustomLua.md) | 编写扩展脚本（translator / filter） |
| [项目结构](docs/ProjectStructure.md) | 目录结构、文件类型说明 |
| [配置引用链](docs/ConfigReference.md) | default.yaml → schema → dict 的依赖关系 |
| [开发指南](docs/Development.md) | 构建流程、命令、测试、CI/CD |
| [致谢](docs/Credits.md) | 上游项目与依赖 |

## 开发

```bash
git clone https://github.com/josephxzy/med-ice.git
cd med-ice
make -C build build          # 构建（需要 Go 1.24+）
make -C build lint           # 代码检查
make -C build smoke          # 冒烟测试
```

详见 [开发指南](docs/Development.md) 和 [AGENTS.md](AGENTS.md)。

## 致谢

| 来源 | 说明 |
|------|------|
| [iDvel/rime-ice](https://github.com/iDvel/rime-ice) | 上游项目，词库和方案的基础 |
| [mirtlecn/rime-radical-pinyin](https://github.com/mirtlecn/rime-radical-pinyin) | 部件拆字方案 |
| [rime/rime-prelude](https://github.com/rime/rime-prelude) | Rime 默认配置 |

本项目沿用上游 [LGPL-3.0](LICENSE) 许可证。
