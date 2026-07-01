package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"script/rime"
	"strings"
)

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "s":
			rime.InitManifest()
			goto SORT
		case "t":
			rime.InitManifest()
			rime.Temp()
			return
		case "tp":
			rime.InitManifest()
			rime.Pinyin(filepath.Join(rime.OutDir, "cn_dicts", "temp.txt"))
			return
		}
	}

	rime.InitManifest()

	prepareOutputDir()
	fmt.Println("--------------------------------------------------")

	rime.CheckAndGenerateEmoji()
	fmt.Println("--------------------------------------------------")

	rime.CnEn()
	fmt.Println("--------------------------------------------------")

	// 为 manifest 中标记了 NeedPinyin 的词库注音
	for _, d := range rime.Manifest.CNDicts() {
		if d.NeedPinyin {
			rime.Pinyin(d.OutAbsPath)
		}
	}
	fmt.Println("--------------------------------------------------")

	// 为需要权重的词库补权重
	for _, d := range rime.Manifest.CNDicts() {
		if d.NeedWeight {
			rime.AddWeight(d.OutAbsPath, 100)
		}
	}
	fmt.Println("--------------------------------------------------")

	// 为医学词库生成简拼索引（用于 med_ice 的超级简拼功能）
	var medPaths []string
	for _, d := range rime.Manifest.CNDicts() {
		if strings.HasPrefix(d.Name, "med_") {
			medPaths = append(medPaths, d.OutAbsPath)
		}
	}
	if len(medPaths) > 0 {
		rime.BuildMedAbbrevIndex(medPaths, filepath.Join(rime.OutDir, "med_abbrev_index.txt"))
		fmt.Println("--------------------------------------------------")
	}

	// 按词库类型检查（仅检查需要校验的核心词库，跳过大字表 41448 等）
	for _, name := range []string{"8105", "base", "ext", "tencent"} {
		if d := rime.Manifest.DictByName(name); d != nil {
			rime.Check(d.OutAbsPath, d.Columns)
		}
	}
	fmt.Println("--------------------------------------------------")

	// 检查多音字（base 和 ext）
	if base := rime.Manifest.DictByName("base"); base != nil {
		rime.CheckPolyphone(base.OutAbsPath)
	}
	if ext := rime.Manifest.DictByName("ext"); ext != nil {
		rime.CheckPolyphone(ext.OutAbsPath)
	}
	fmt.Println("--------------------------------------------------")

	areYouOK()

SORT:
	// 排序、去重
	for _, d := range rime.Manifest.Dicts {
		rime.SortDict(d)
	}

	fmt.Println("--------------------------------------------------")
	verifyOutput()
}

func prepareOutputDir() {
	log.Println("Preparing output directory...")

	os.RemoveAll(rime.OutDir)

	dirs := []string{
		filepath.Join(rime.OutDir, "cn_dicts"),
		filepath.Join(rime.OutDir, "en_dicts"),
		filepath.Join(rime.OutDir, "opencc"),
		filepath.Join(rime.OutDir, "lua", "cold_word_drop"),
		filepath.Join(rime.OutDir, "build"),
	}
	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Fatalf("Failed to create directory %s: %v", dir, err)
		}
	}

	// 从 manifest 复制所有词库文件
	for _, d := range rime.Manifest.Dicts {
		rime.CopyFileContent(d.SrcPath, d.OutAbsPath)
	}

	// 复制 schema 文件
	srcDir := rime.SrcDir
	for _, sf := range rime.Manifest.SchemaFiles {
		rime.CopyFileContent(
			filepath.Join(srcDir, "schema", sf),
			filepath.Join(rime.OutDir, sf),
		)
	}

	// 复制 dict 索引文件
	dictDir := filepath.Join(srcDir, "dict")
	dictEntries, _ := os.ReadDir(dictDir)
	for _, entry := range dictEntries {
		if strings.HasSuffix(entry.Name(), ".dict.yaml") {
			rime.CopyFileContent(
				filepath.Join(dictDir, entry.Name()),
				filepath.Join(rime.OutDir, entry.Name()),
			)
		}
	}

	// 复制配置文件
	configDir := filepath.Join(srcDir, "config")
	for _, cf := range rime.Manifest.ConfigFiles {
		rime.CopyFileContent(
			filepath.Join(configDir, cf),
			filepath.Join(rime.OutDir, cf),
		)
	}

	// 复制自定义短语（用户词库数据，非配置文件）
	rime.CopyFileContent(
		filepath.Join(srcDir, "custom_phrase.txt"),
		filepath.Join(rime.OutDir, "custom_phrase.txt"),
	)

	// 复制 lua
	copyDir(filepath.Join(srcDir, "lua"), filepath.Join(rime.OutDir, "lua"))

	// 复制 opencc
	for _, f := range []string{"emoji.json", "others.txt"} {
		rime.CopyFileContent(
			filepath.Join(srcDir, "opencc", f),
			filepath.Join(rime.OutDir, "opencc", f),
		)
	}

	// 复制 recipe
	rime.CopyFileContent(
		filepath.Join(srcDir, "recipes", "recipe.yaml"),
		filepath.Join(rime.OutDir, "recipe.yaml"),
	)

	// 复制 LICENSE
	rime.CopyFileContent(
		filepath.Join(srcDir, "..", "LICENSE"),
		filepath.Join(rime.OutDir, "LICENSE"),
	)

	os.WriteFile(filepath.Join(rime.OutDir, "build", ".gitkeep"), []byte{}, 0644)

	log.Println("Output directory prepared successfully.")
}

func copyDir(src, dst string) {
	entries, err := os.ReadDir(src)
	if err != nil {
		log.Fatalf("Fatal: cannot read dir %s: %v", src, err)
	}
	log.Printf("Copying directory %s -> %s (%d entries)", src, dst, len(entries))
	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())
		if entry.IsDir() {
			ensureDir(dstPath)
			copyDir(srcPath, dstPath)
		} else {
			rime.CopyFileContent(srcPath, dstPath)
		}
	}
}

func ensureDir(path string) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		os.MkdirAll(path, 0755)
	}
}

func areYouOK() {
	if rime.AutoConfirm {
		fmt.Println("Auto confirm enabled. Skipping prompt.")
		return
	}

	fmt.Println("Are you OK:")
	var isOK string
	_, _ = fmt.Scanf("%s", &isOK)
	isOK = strings.ToLower(isOK)
	if isOK != "ok" && isOK != "y" && isOK != "yes" {
		os.Exit(123)
	}
}

func verifyOutput() {
	log.Println("Verifying output integrity...")

	for _, d := range rime.Manifest.Dicts {
		data, err := os.ReadFile(d.OutAbsPath)
		if err != nil {
			log.Printf("MISSING: %s", d.OutAbsPath)
			continue
		}
		content := string(data)
		if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
			log.Printf("BOM DETECTED: %s", d.OutAbsPath)
		}
		if !strings.Contains(content, "\n# +_+\n") && !strings.Contains(content, "\n#+_+\n") {
			if !strings.Contains(content, "# +_+") {
				log.Printf("NO MARKER (# +_+): %s", d.OutAbsPath)
			}
		}
		if !strings.Contains(content, "encoding: utf-8") && !strings.Contains(content, "encoding:utf-8") {
			log.Printf("NO ENCODING: %s", d.OutAbsPath)
		}
		if strings.Contains(content, "\r\n") {
			log.Printf("CRLF DETECTED: %s", filepath.Base(d.OutAbsPath))
		}
	}

	// 验证 cn_en*.txt
	cnEnFiles, _ := filepath.Glob(filepath.Join(rime.OutDir, "en_dicts", "cn_en*.txt"))
	log.Printf("cn_en*.txt files: %d", len(cnEnFiles))

	// 验证 lua
	luaFiles, _ := filepath.Glob(filepath.Join(rime.OutDir, "lua", "*.lua"))
	log.Printf("lua files in out/: %d", len(luaFiles))

	// 验证 emoji.txt
	emojiPath := filepath.Join(rime.OutDir, "opencc", "emoji.txt")
	if _, err := os.Stat(emojiPath); os.IsNotExist(err) {
		log.Printf("MISSING: emoji.txt")
	}

	// 验证 schema 和 config
	for _, sf := range rime.Manifest.SchemaFiles {
		p := filepath.Join(rime.OutDir, sf)
		if _, err := os.Stat(p); os.IsNotExist(err) {
			log.Printf("MISSING SCHEMA: %s", sf)
		}
	}
	for _, cf := range rime.Manifest.ConfigFiles {
		p := filepath.Join(rime.OutDir, cf)
		if _, err := os.Stat(p); os.IsNotExist(err) {
			log.Printf("MISSING CONFIG: %s", cf)
		}
	}

	log.Println("Verification complete.")
}
