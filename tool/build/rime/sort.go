package rime

import (
	"bufio"
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"os"
	"path"
	"sort"
	"strconv"
	"strings"
	"time"

	mapset "github.com/deckarep/golang-set/v2"
)

// SortDict 对词库文件进行排序和去重，使用 manifest 中的属性决定处理方式
func SortDict(d *DictFile) {
	dictPath := d.OutAbsPath
	_type := d.Columns

	defer updateVersion(dictPath, getSha1(dictPath))
	defer printfTimeCost("排序 "+path.Base(dictPath), time.Now())

	file, err := os.OpenFile(dictPath, os.O_RDWR, 0644)
	if err != nil {
		log.Fatalln(err)
	}
	defer file.Close()

	prefixContents := make([]string, 0)
	contents := make([]lemma, 0)
	aSet := mapset.NewSet[string]()

	isMark := false
	sc := bufio.NewScanner(file)
	for sc.Scan() {
		line := sc.Text()

		if !isMark {
			prefixContents = append(prefixContents, line)
			if strings.HasPrefix(line, mark) {
				isMark = true
			}
			continue
		}

		parts := strings.Split(line, "\t")
		text, code, weight := parts[0], "", ""

		if (_type == 1 || _type == 2 || _type == 3) && len(parts) != _type {
			log.Println("分割错误123")
		}
		if _type == 4 && len(parts) != 2 {
			fmt.Println("分割错误4")
		}

		// 核心词库中注释掉的词条权重置为 0
		if d.IsBase && strings.HasPrefix(line, "# ") {
			if len(parts) >= 3 {
				parts[2] = "0"
			}
		}

		switch _type {
		case 1:
			if aSet.Contains(text) {
				fmt.Println("重复：", line)
				continue
			}
			aSet.Add(text)
			contents = append(contents, lemma{text: text})
		case 2:
			text, code = parts[0], parts[1]
			if aSet.Contains(text + code) {
				fmt.Println("重复：", line)
				continue
			}
			aSet.Add(text + code)
			contents = append(contents, lemma{text: text, code: code})
		case 3:
			text, code, weight = parts[0], parts[1], parts[2]
			if aSet.Contains(text + code) {
				fmt.Println("重复：", line)
				continue
			}
			aSet.Add(text + code)
			w, _ := strconv.Atoi(weight)
			contents = append(contents, lemma{text: text, code: code, weight: w})
		case 4:
			text, weight = parts[0], parts[1]
			if aSet.Contains(text) {
				fmt.Println("重复：", line)
				continue
			}
			aSet.Add(text)
			w, _ := strconv.Atoi(weight)
			contents = append(contents, lemma{text: text, weight: w})
		}
	}
	if err := sc.Err(); err != nil {
		log.Fatalln(err)
	}

	// 排序
	if d.Category == "en" {
		sort.SliceStable(contents, func(i, j int) bool {
			textI, textJ := strings.ToLower(contents[i].text), strings.ToLower(contents[j].text)
			if strings.HasPrefix(textI, "# ") {
				textI = textI[2:]
			}
			if strings.HasPrefix(textJ, "# ") {
				textJ = textJ[2:]
			}
			if textI != textJ {
				return textI < textJ
			}
			return false
		})
	} else {
		sort.SliceStable(contents, func(i, j int) bool {
			if contents[i].code != contents[j].code {
				return contents[i].code < contents[j].code
			}
			if contents[i].weight != contents[j].weight {
				return contents[i].weight > contents[j].weight
			}
			if contents[i].text != contents[j].text {
				return contents[i].text < contents[j].text
			}
			return false
		})
	}

	// 清空并重写
	file.Truncate(0)
	file.Seek(0, 0)

	prefixContents = fixColumnsHeader(prefixContents, d.Columns)

	for _, line := range prefixContents {
		file.WriteString(line + "\n")
	}

	// 核心词库直接写入，不需要从其他词库去重
	if d.IsBase {
		for _, line := range contents {
			if d.Columns == 2 {
				file.WriteString(line.text + "\t" + line.code + "\n")
			} else {
				file.WriteString(line.text + "\t" + line.code + "\t" + strconv.Itoa(line.weight) + "\n")
			}
		}
	} else if len(d.DedupFrom) > 0 {
		// 需要去重的词库
		var dedupSets []mapset.Set[string]
		for _, depName := range d.DedupFrom {
			switch depName {
			case "8105":
				dedupSets = append(dedupSets, HanziSet)
			case "base":
				dedupSets = append(dedupSets, BaseSet)
			case "ext":
				dedupSets = append(dedupSets, ExtSet)
			case "tencent":
				dedupSets = append(dedupSets, TencentSet)
			}
		}

		var intersect mapset.Set[string]
		if len(dedupSets) == 1 {
			intersect = dedupSets[0]
		} else if len(dedupSets) >= 2 {
			intersect = dedupSets[0]
			for i := 1; i < len(dedupSets); i++ {
				intersect = intersect.Intersect(dedupSets[i])
			}
		}

		if intersect != nil {
			for _, line := range contents {
				if intersect.Contains(line.text) {
					fmt.Printf("%s 重复于其他词库：%s\n", d.Name, line.text)
					continue
				}
				writeLemma(file, d, line)
			}
		} else {
			for _, line := range contents {
				writeLemma(file, d, line)
			}
		}
	} else {
		// 外部词库，只排序不去重
		for _, line := range contents {
			writeLemma(file, d, line)
		}
	}

	file.Sync()
}

func writeLemma(file *os.File, d *DictFile, line lemma) {
	switch d.Columns {
	case 1:
		file.WriteString(line.text + "\n")
	case 2:
		file.WriteString(line.text + "\t" + line.code + "\n")
	case 3:
		file.WriteString(line.text + "\t" + line.code + "\t" + strconv.Itoa(line.weight) + "\n")
	case 4:
		file.WriteString(line.text + "\t" + strconv.Itoa(line.weight) + "\n")
	}
}

// Sort 保留旧接口用于兼容（41448 和 en.dict.yaml 仍通过 manifest 路径调用）
func Sort(dictPath string, _type int) {
	df := Manifest.DictByPath(dictPath)
	if df == nil {
		df = &DictFile{
			OutAbsPath: dictPath,
			Columns:    _type,
			IsBase:     true,
		}
	}
	SortDict(df)
}

func getSha1(dictPath string) string {
	f, err := os.Open(dictPath)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	sha1Handle := sha1.New()
	if _, err := io.Copy(sha1Handle, f); err != nil {
		log.Fatal(err)
	}

	return hex.EncodeToString(sha1Handle.Sum(nil))
}

func fixColumnsHeader(prefixContents []string, columns int) []string {
	columnNames := getColumnNames(columns)
	if columnNames == nil {
		return prefixContents
	}

	var result []string
	inColumns := false
	for _, line := range prefixContents {
		if strings.HasPrefix(strings.TrimSpace(line), "columns:") {
			inColumns = true
			result = append(result, line)
			for _, name := range columnNames {
				result = append(result, "  - "+name)
			}
			continue
		}
		if inColumns {
			trimmed := strings.TrimLeft(line, " ")
			if strings.HasPrefix(trimmed, "- ") {
				continue
			}
			inColumns = false
		}
		result = append(result, line)
	}
	return result
}

func getColumnNames(columns int) []string {
	switch columns {
	case 1:
		return []string{"text"}
	case 2:
		return []string{"text", "code"}
	case 3:
		return []string{"text", "code", "weight"}
	case 4:
		return []string{"text", "weight"}
	default:
		return nil
	}
}

func updateVersion(dictPath string, oldSha1 string) {
	newSha1 := getSha1(dictPath)
	if newSha1 == oldSha1 {
		fmt.Println()
		return
	}
	fmt.Println(" ...sorted")

	file, err := os.OpenFile(dictPath, os.O_RDWR, 0644)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	arr := make([]string, 0)
	sc := bufio.NewScanner(file)
	for sc.Scan() {
		line := sc.Text()
		if strings.HasPrefix(line, "version:") {
			s := fmt.Sprintf("version: \"%s\"", time.Now().Format("2006-01-02"))
			arr = append(arr, s)
		} else {
			arr = append(arr, line)
		}
	}

	file.Truncate(0)
	file.Seek(0, 0)
	for _, line := range arr {
		file.WriteString(line + "\n")
	}
	file.Sync()
}
