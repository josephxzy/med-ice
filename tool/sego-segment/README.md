# sego-segment

中文分词工具，基于 [gse](https://github.com/go-ego/gse)（纯 Go，无 C 依赖）。

## 安装

```bash
cd tool/sego-segment
go mod tidy
go build -o sego-segment .
```

## 使用

```bash
# 从 stdin 读入，每行一个词条
echo "阿苯达唑片" | ./sego-segment
# 输出: 阿苯 达唑 片

# 从文件批量处理
cat medical_terms.txt | ./sego-segment > segmented.txt
```

## 用途

将超长药名（如"双价肾综合征出血热灭活疫苗"）拆分为可检索的词组分段，配合医学检索模式使用。
