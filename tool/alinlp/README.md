# 阿里云 NLP 中文分词 CLI

免费版中文分词，阿里云自然语言处理（NLP）基础版，每日调用额度充足。

## 开通

1. 登录 [阿里云 NLP 控制台](https://nlp.aliyun.com/)
2. 开通"基础版-中文分词"（免费）
3. 获取 AccessKey: [RAM 访问控制](https://ram.console.aliyun.com/)

## 安装

```bash
cd tool/alinlp
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_key_secret"
```

## 使用

```bash
# 命令行输入
python alinlp_ws.py "双价肾综合征出血热灭活疫苗"
# → 双价 肾 综合征 出血热 灭活 疫苗

# 管道输入
echo "阿苯达唑片治疗寄生虫感染" | python alinlp_ws.py
# → 阿苯达唑 片 治疗 寄生虫 感染
```

## 限制

- 单次最大 1024 字符
- 免费版有 QPS 限制（建议 >100ms 间隔）
