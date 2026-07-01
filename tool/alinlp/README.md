# 阿里云 NLP 中文分词 CLI

免费版中文分词（阿里云 NLP 基础版），每日 500 次免费额度。

## 开通

1. [阿里云 NLP 控制台](https://nlp.aliyun.com/) 开通基础版（免费）
2. [RAM 访问控制](https://ram.console.aliyun.com/) 获取 AccessKey

## 安装

```bash
cd tool/alinlp
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_key_secret"
```

## 使用

```bash
python alinlp_ws.py "双价肾综合征出血热灭活疫苗"
# → 双价 肾 综合征 出血热 灭活 疫苗
#   [今日: 1/500]

echo "阿苯达唑片" | python alinlp_ws.py

# 查看配额
python alinlp_ws.py config
# → 日期:        2026-07-01
# → 今日已调用:  12
# → 每日限制:    500

# 修改限制
python alinlp_ws.py config --limit 1000
```

## 配额

配置文件 `~/.alinlp_config.json`，每日自动重置。调用前检查今日次数，超额直接拒绝不发请求。
