package rime

import (
	"bufio"
	"flag"
	"fmt"
	mapset "github.com/deckarep/golang-set/v2"
	"log"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// 一个词的组成部分
type lemma struct {
	text   string // 汉字
	code   string // 编码
	weight int    // 权重
}

var (
	mark         = "# +_+" // 词库中的标记符号，表示从这行开始进行检查或排序
	SrcDir       string   // 源文件目录 (src/)
	OutDir       string   // 构建输出目录 (out/)
	EmojiMapPath string
	EmojiPath    string
	HanziPath    string
	BasePath     string
	ExtPath      string
	TencentPath  string
	SrcHanziPath string // 源文件中的字表路径（init 阶段使用）
	SrcBasePath  string // 源文件中的核心词库路径
	SrcExtPath   string // 源文件中的扩展词库路径
	SrcTencentPath string // 源文件中的腾讯词库路径
	HanziSet     mapset.Set[string]
	BaseSet      mapset.Set[string]
	ExtSet       mapset.Set[string]
	TencentSet   mapset.Set[string]
	需要注音TXT      string
	错别字TXT       string
	汉字拼音映射TXT    string
	AutoConfirm  bool
)

func init() {
	flag.StringVar(&SrcDir, "src_path", "", "Source directory (src/)")
	flag.StringVar(&OutDir, "out_path", "", "Output directory (out/)")
	flag.BoolVar(&AutoConfirm, "auto_confirm", false, "Automatically confirm the prompt")
	flag.Parse()

	if SrcDir == "" {
		SrcDir = filepath.Join("..", "src")
	}
	if OutDir == "" {
		OutDir = "out"
	}

	SrcDir, _ = filepath.Abs(SrcDir)
	OutDir, _ = filepath.Abs(OutDir)

	EmojiMapPath = filepath.Join(SrcDir, "opencc", "emoji-map.txt")
	EmojiPath = filepath.Join(OutDir, "opencc", "emoji.txt")

	HanziPath = filepath.Join(OutDir, "cn_dicts", "8105.dict.yaml")
	BasePath = filepath.Join(OutDir, "cn_dicts", "base.dict.yaml")
	ExtPath = filepath.Join(OutDir, "cn_dicts", "ext.dict.yaml")
	TencentPath = filepath.Join(OutDir, "cn_dicts", "tencent.dict.yaml")

	SrcHanziPath = filepath.Join(SrcDir, "dict", "cn", "8105.dict.yaml")
	SrcBasePath = filepath.Join(SrcDir, "dict", "cn", "base.dict.yaml")
	SrcExtPath = filepath.Join(SrcDir, "dict", "cn", "ext.dict.yaml")
	SrcTencentPath = filepath.Join(SrcDir, "dict", "cn", "tencent.dict.yaml")

	HanziSet = readToSet(SrcHanziPath)
	BaseSet = readToSet(SrcBasePath)
	ExtSet = readToSet(SrcExtPath)
	TencentSet = readToSet(SrcTencentPath)

	需要注音TXT = filepath.Join("rime", "需要注音.txt")
	错别字TXT = filepath.Join("rime", "错别字.txt")
	汉字拼音映射TXT = filepath.Join("rime", "汉字拼音映射.txt")

	initCheck()
	initSchemas()
	initPinyin()
}

// 将所有词库读入 set，供检查或排序使用
func readToSet(dictPath string) mapset.Set[string] {
	set := mapset.NewSet[string]()

	file, err := os.Open(dictPath)
	if err != nil {
		log.Fatalln(err)
	}
	defer file.Close()

	sc := bufio.NewScanner(file)
	isMark := false
	for sc.Scan() {
		line := sc.Text()
		if !isMark {
			if strings.HasPrefix(line, mark) {
				isMark = true
			}
			continue
		}
		parts := strings.Split(line, "\t")
		set.Add(parts[0])
	}

	return set
}

// 打印耗时时间
func printlnTimeCost(content string, start time.Time) {
	// fmt.Printf("%s：\t%.2fs\n", content, time.Since(start).Seconds())
	printfTimeCost(content, start)
	fmt.Println()
}

// 打印耗时时间
func printfTimeCost(content string, start time.Time) {
	fmt.Printf("%s：\t%.2fs", content, time.Since(start).Seconds())
}

// slice 是否包含 item
func contains(arr []string, item string) bool {
	for _, x := range arr {
		if item == x {
			return true
		}
	}
	return false
}

// AddWeight  为 ext、tencent 没权重的词条加上权重，有权重的改为 weight
func AddWeight(dictPath string, weight int) {
	// 控制台输出
	printlnTimeCost("加权重\t"+path.Base(dictPath), time.Now())

	// 读取到 lines 数组
	file, err := os.ReadFile(dictPath)
	if err != nil {
		log.Fatal(err)
	}
	lines := strings.Split(string(file), "\n")

	isMark := false
	for i, line := range lines {
		if !isMark {
			if strings.HasPrefix(line, mark) {
				isMark = true
			}
			continue
		}
		// 过滤空行
		if line == "" {
			continue
		}
		// 修改权重为传入的 weight，没有就加上
		parts := strings.Split(line, "\t")
		_, err := strconv.Atoi(parts[len(parts)-1])
		if err != nil {
			lines[i] = line + "\t" + strconv.Itoa(weight)
		} else {
			lines[i] = strings.Join(parts[:len(parts)-1], "\t") + "\t" + strconv.Itoa(weight)
		}
	}

	// 写入
	resultString := strings.Join(lines, "\n")
	err = os.WriteFile(dictPath, []byte(resultString), 0644)
	if err != nil {
		log.Fatal(err)
	}
}
