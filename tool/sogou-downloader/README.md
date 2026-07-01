# 搜狗医学词库下载工具

从 [搜狗输入法词库](https://pinyin.sogou.com/dict/cate/index/132) 医学分类批量下载、转换、合并词库。

## 使用

```bash
cd tool/sogou-downloader
node download.mjs
```

## 流程

1. 爬取 37 页共 362 个医学词库的下载链接
2. 下载 `.scel` 文件到 `down/`
3. 调用 `../scel2txt/scel2txt.py` 转换为 `.txt`（提取词库名作为注释头）
4. 合并去重，输出 `down/sogou_medical_merged.txt`

每个 `.scel` 同目录下会生成 `.meta.json` 记录来源信息（词库名、搜狗页面链接、下载量、更新时间）。

## 增量更新

已下载的 `down/*.scel` 会自动跳过，只下载新增的词库。

## 转换到 med-ice 词库

合并后的 txt 文件格式为每行一个词条。手动转换：

```bash
# 生成 .dict.yaml
python -c "
lines = open('down/sogou_medical_merged.txt').read().splitlines()
with open('../../src/dict/cn/med_sogou.dict.yaml', 'w') as f:
    f.write('# Rime dictionary\n---\nname: med_sogou\nversion: \"1\"\n...\n# +_+\n')
    for w in lines:
        if w.strip(): f.write(f'{w}\t1\n')
"
```
