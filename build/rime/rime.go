package rime

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	mapset "github.com/deckarep/golang-set/v2"
)

type lemma struct {
	text   string
	code   string
	weight int
}

var (
	mark        = "# +_+"
	SrcDir      string
	OutDir      string
	Manifest    *FileManifest
	EmojiMapPath string
	EmojiPath   string

	// 以下变量现在从 Manifest 动态填充
	HanziPath   string
	BasePath    string
	ExtPath     string
	TencentPath string

	HanziSet   mapset.Set[string]
	BaseSet    mapset.Set[string]
	ExtSet     mapset.Set[string]
	TencentSet mapset.Set[string]

	需要注音TXT   string
	错别字TXT    string
	汉字拼音映射TXT string

	AutoConfirm bool
)

func init() {
	flag.StringVar(&SrcDir, "src_path", "", "Source directory (src/)")
	flag.StringVar(&OutDir, "out_path", "", "Output directory (out/)")
	flag.BoolVar(&AutoConfirm, "auto_confirm", false, "Automatically confirm the prompt")
}

// InitManifest 解析命令行参数后初始化源/输出目录，然后从 src/ 的 YAML 配置自动发现所有文件依赖。
// 必须在使用任何路径变量（HanziPath, BasePath 等）或处理函数之前调用。
func InitManifest() {
	flag.Parse()

	if SrcDir == "" {
		SrcDir = filepath.Join("..", "src")
	}
	if OutDir == "" {
		OutDir = "out"
	}
	SrcDir, _ = filepath.Abs(SrcDir)
	OutDir, _ = filepath.Abs(OutDir)

	Manifest = DiscoverManifest(SrcDir)

	EmojiMapPath = filepath.Join(SrcDir, "opencc", "emoji-map.txt")
	EmojiPath = filepath.Join(OutDir, "opencc", "emoji.txt")

	// 从 manifest 填充路径变量
	if d := Manifest.DictByName("8105"); d != nil {
		HanziPath = d.OutAbsPath
	}
	if d := Manifest.DictByName("base"); d != nil {
		BasePath = d.OutAbsPath
	}
	if d := Manifest.DictByName("ext"); d != nil {
		ExtPath = d.OutAbsPath
	}
	if d := Manifest.DictByName("tencent"); d != nil {
		TencentPath = d.OutAbsPath
	}

	// 读取源文件构建去重集合
	readSrcSets()

	需要注音TXT = filepath.Join("rime", "需要注音.txt")
	错别字TXT = filepath.Join("rime", "错别字.txt")
	汉字拼音映射TXT = filepath.Join("rime", "汉字拼音映射.txt")

	initCheck()
	initSchemas()
	initPinyin()
}

func readSrcSets() {
	if d := Manifest.DictByName("8105"); d != nil && d.Category == "cn" {
		HanziSet = readToSet(d.SrcPath)
	} else {
		HanziSet = mapset.NewSet[string]()
	}
	if d := Manifest.DictByName("base"); d != nil && d.Category == "cn" {
		BaseSet = readToSet(d.SrcPath)
	} else {
		BaseSet = mapset.NewSet[string]()
	}
	if d := Manifest.DictByName("ext"); d != nil && d.Category == "cn" {
		ExtSet = readToSet(d.SrcPath)
	} else {
		ExtSet = mapset.NewSet[string]()
	}
	if d := Manifest.DictByName("tencent"); d != nil && d.Category == "cn" {
		TencentSet = readToSet(d.SrcPath)
	} else {
		TencentSet = mapset.NewSet[string]()
	}
}

// DictNeedsPinyin 判断某个输出路径对应的词库是否需要注音
func DictNeedsPinyin(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.NeedPinyin
}

// DictNeedsWeight 判断是否需要补权重
func DictNeedsWeight(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.NeedWeight
}

// DictIsBase 判断是否为核心词库（不去重）
func DictIsBase(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.IsBase
}

// isHanziDict 判断是否为字表（8105）
func isHanziDict(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.Name == "8105"
}

// isBaseDict 判断是否为核心词库（base）
func isBaseDict(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.Name == "base"
}

// isTencentDict 判断是否为腾讯大词库
func isTencentDict(dictPath string) bool {
	df := Manifest.DictByPath(dictPath)
	return df != nil && df.Name == "tencent"
}

// srcPath 获取指定名称的词库源文件路径
func srcPath(name string) string {
	d := Manifest.DictByName(name)
	if d != nil {
		return d.SrcPath
	}
	return ""
}

func readToSet(dictPath string) mapset.Set[string] {
	set := mapset.NewSet[string]()

	file, err := os.Open(dictPath)
	if err != nil {
		log.Printf("警告: 无法读取 %s: %v", dictPath, err)
		return set
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

// DictDedupSets 获取去重时应排除的词条集合。如果不需要去重返回空列表。
func DictDedupSets(dictPath string) []mapset.Set[string] {
	df := Manifest.DictByPath(dictPath)
	if df == nil || len(df.DedupFrom) == 0 {
		return nil
	}
	var sets []mapset.Set[string]
	for _, depName := range df.DedupFrom {
		switch depName {
		case "8105":
			sets = append(sets, HanziSet)
		case "base":
			sets = append(sets, BaseSet)
		case "ext":
			sets = append(sets, ExtSet)
		case "tencent":
			sets = append(sets, TencentSet)
		}
	}
	return sets
}

func printlnTimeCost(content string, start time.Time) {
	printfTimeCost(content, start)
	fmt.Println()
}

func printfTimeCost(content string, start time.Time) {
	fmt.Printf("%s：\t%.2fs", content, time.Since(start).Seconds())
}

func contains(arr []string, item string) bool {
	for _, x := range arr {
		if item == x {
			return true
		}
	}
	return false
}

func AddWeight(dictPath string, weight int) {
	printlnTimeCost("加权重\t"+path.Base(dictPath), time.Now())

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
		if line == "" {
			continue
		}
		parts := strings.Split(line, "\t")
		_, err := strconv.Atoi(parts[len(parts)-1])
		if err != nil {
			lines[i] = line + "\t" + strconv.Itoa(weight)
		} else {
			lines[i] = strings.Join(parts[:len(parts)-1], "\t") + "\t" + strconv.Itoa(weight)
		}
	}

	resultString := strings.Join(lines, "\n")
	err = os.WriteFile(dictPath, []byte(resultString), 0644)
	if err != nil {
		log.Fatal(err)
	}
}
