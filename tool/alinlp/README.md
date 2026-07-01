# 阿里云 NLP 中文分词 CLI

免费版中文分词（阿里云 NLP 基础版），每日 500 次免费额度。

## 开通

1. [阿里云 NLP 控制台](https://nlp.aliyun.com/) 开通基础版（免费）
2. [RAM 访问控制](https://ram.console.aliyun.com/) 获取 AccessKey

## 配置

首次运行自动从模板创建 `config.json`：

```bash
cd tool/alinlp
python alinlp_ws.py config
```

编辑 `config.json` 填入密钥：

```json
{
  "access_key_id": "LTAI5t...",
  "access_key_secret": "abc...",
  "daily_limit": 500
}
```

（也可用环境变量 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `_SECRET`，配置文件优先）

## 使用

```bash
python alinlp_ws.py "双价肾综合征出血热灭活疫苗"
# → 双价 肾 综合征 出血热 灭活 疫苗
#   [今日: 1/500]

python alinlp_ws.py config         # 查看统计
python alinlp_ws.py config --limit 1000  # 修改上限
```

## 安全

- `config.json` 含密钥，已在 `.gitignore` 中排除
- `config.template.json` 是模板文件，可安全提交
