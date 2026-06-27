package main

import (
	"fmt"
	"io"
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
			goto SORT
		case "t":
			rime.Temp()
			return
		case "tp":
			rime.Pinyin(filepath.Join(rime.OutDir, "cn_dicts", "temp.txt"))
			return
		}
	}

	// 准备输出目录：创建目录结构，复制词典源文件和静态文件
	prepareOutputDir()
	fmt.Println("--------------------------------------------------")

	// Emoji 检查和更新
	rime.CheckAndGenerateEmoji()
	fmt.Println("--------------------------------------------------")

	// 从 src/dict/en/cn_en.txt 更新中英混输词库
	rime.CnEn()
	fmt.Println("--------------------------------------------------")

	// 为没注音的词汇半自动注音
	rime.Pinyin(rime.ExtPath)
	fmt.Println("--------------------------------------------------")

	// 为 ext、tencent 没权重的词条加上权重，有权重的改为下面设置的权重
	rime.AddWeight(rime.ExtPath, 100)
	rime.AddWeight(rime.TencentPath, 100)
	fmt.Println("--------------------------------------------------")

	// 检查
	// _type: 1 只有汉字 2 汉字+注音 3 汉字+注音+权重 4 汉字+权重
	rime.Check(rime.HanziPath, 3)
	rime.Check(rime.BasePath, 3)
	rime.Check(rime.ExtPath, 3)
	rime.Check(rime.TencentPath, 4)
	fmt.Println("--------------------------------------------------")

	// 检查同义多音字
	rime.CheckPolyphone(rime.BasePath)
	rime.CheckPolyphone(rime.ExtPath)
	fmt.Println("--------------------------------------------------")

	areYouOK()

SORT:
	// 排序，顺便去重
	rime.Sort(rime.HanziPath, 3)
	rime.Sort(filepath.Join(rime.OutDir, "cn_dicts", "41448.dict.yaml"), 2)
	rime.Sort(rime.BasePath, 3)
	rime.Sort(rime.ExtPath, 3)
	rime.Sort(rime.TencentPath, 4)
	rime.Sort(filepath.Join(rime.OutDir, "en_dicts", "en.dict.yaml"), 2)

	fmt.Println("--------------------------------------------------")
	verifyOutput()
}

func prepareOutputDir() {
	log.Println("Preparing output directory...")

	// 清理并重建 out/ 目录
	os.RemoveAll(rime.OutDir)

	dirs := []string{
		filepath.Join(rime.OutDir, "cn_dicts"),
		filepath.Join(rime.OutDir, "en_dicts"),
		filepath.Join(rime.OutDir, "opencc"),
		filepath.Join(rime.OutDir, "lua"),
		filepath.Join(rime.OutDir, "lua", "cold_word_drop"),
		filepath.Join(rime.OutDir, "build"),
	}

	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Fatalf("Failed to create directory %s: %v", dir, err)
		}
	}

	// 复制词典源文件到 out/
	copyDictFiles()

	// 复制静态文件到 out/
	copyStaticFiles()

	log.Println("Output directory prepared successfully.")
}

func copyDictFiles() {
	// cn_dicts
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "8105.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "8105.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "41448.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "41448.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "base.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "base.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "ext.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "ext.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "tencent.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "tencent.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "cn", "others.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "others.dict.yaml"),
	)

	// en_dicts
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "en", "en.dict.yaml"),
		filepath.Join(rime.OutDir, "en_dicts", "en.dict.yaml"),
	)
	copyFile(
		filepath.Join(rime.SrcDir, "dict", "en", "en_ext.dict.yaml"),
		filepath.Join(rime.OutDir, "en_dicts", "en_ext.dict.yaml"),
	)
}

func copyStaticFiles() {
	srcDir := rime.SrcDir
	outDir := rime.OutDir

	// Schema files
	schemaFiles, _ := filepath.Glob(filepath.Join(srcDir, "schema", "*.schema.yaml"))
	for _, f := range schemaFiles {
		copyFile(f, filepath.Join(outDir, filepath.Base(f)))
	}

	// Dict index files
	copyFile(filepath.Join(srcDir, "dict", "med_ice.dict.yaml"), filepath.Join(outDir, "med_ice.dict.yaml"))
	copyFile(filepath.Join(srcDir, "dict", "melt_eng.dict.yaml"), filepath.Join(outDir, "melt_eng.dict.yaml"))
	copyFile(filepath.Join(srcDir, "dict", "radical_pinyin.dict.yaml"), filepath.Join(outDir, "radical_pinyin.dict.yaml"))

	// Config files
	configFiles, _ := filepath.Glob(filepath.Join(srcDir, "config", "*"))
	for _, f := range configFiles {
		copyFile(f, filepath.Join(outDir, filepath.Base(f)))
	}

	// Lua scripts
	copyDir(filepath.Join(srcDir, "lua"), filepath.Join(outDir, "lua"))

	// OpenCC config files
	copyFile(filepath.Join(srcDir, "opencc", "emoji.json"), filepath.Join(outDir, "opencc", "emoji.json"))
	copyFile(filepath.Join(srcDir, "opencc", "others.txt"), filepath.Join(outDir, "opencc", "others.txt"))

	// Recipe
	copyFile(filepath.Join(srcDir, "recipes", "recipe.yaml"), filepath.Join(outDir, "recipe.yaml"))

	// License
	copyFile(filepath.Join(srcDir, "..", "LICENSE"), filepath.Join(outDir, "LICENSE"))

	// Build placeholder
	os.WriteFile(filepath.Join(outDir, "build", ".gitkeep"), []byte{}, 0644)
}

func copyFile(src, dst string) {
	srcFile, err := os.Open(src)
	if err != nil {
		log.Fatalf("Fatal: cannot open source %s: %v", src, err)
	}
	defer srcFile.Close()

	ensureDir(filepath.Dir(dst))

	dstFile, err := os.Create(dst)
	if err != nil {
		log.Fatalf("Fatal: cannot create dest %s: %v", dst, err)
	}
	defer dstFile.Close()

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		log.Fatalf("Fatal: failed to copy %s: %v", src, err)
	}
}

func copyDir(src, dst string) {
	entries, err := os.ReadDir(src)
	if err != nil {
		log.Fatalf("Fatal: cannot read dir %s: %v", src, err)
	}
	log.Printf("Copying directory %s → %s (%d entries)", src, dst, len(entries))
	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())
		if entry.IsDir() {
			copyDir(srcPath, dstPath)
		} else {
			copyFile(srcPath, dstPath)
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

	files := []string{
		filepath.Join(rime.OutDir, "cn_dicts", "8105.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "base.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "ext.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "tencent.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "others.dict.yaml"),
		filepath.Join(rime.OutDir, "cn_dicts", "41448.dict.yaml"),
		filepath.Join(rime.OutDir, "en_dicts", "en.dict.yaml"),
		filepath.Join(rime.OutDir, "en_dicts", "en_ext.dict.yaml"),
		filepath.Join(rime.OutDir, "med_ice.dict.yaml"),
		filepath.Join(rime.OutDir, "melt_eng.dict.yaml"),
		filepath.Join(rime.OutDir, "radical_pinyin.dict.yaml"),
	}

	for _, f := range files {
		data, err := os.ReadFile(f)
		if err != nil {
			log.Printf("MISSING: %s", f)
			continue
		}
		content := string(data)
		// 检查是否以 BOM 开头
		if len(content) > 0 && content[0] == '\ufeff' {
			log.Printf("BOM DETECTED: %s", f)
		}
		// 检查是否有空行在 YAML header 和标记之间
		if !strings.Contains(content, "\n# +_+\n") && !strings.Contains(content, "\n#+_+\n") {
			if !strings.Contains(content, "# +_+") {
				log.Printf("NO MARKER (# +_+): %s", f)
			}
		}
		// 检查 encoding 声明
		if !strings.Contains(content, "encoding: utf-8") && !strings.Contains(content, "encoding:utf-8") {
			log.Printf("NO ENCODING: %s", f)
		}
		// 检查 CRLF
		if strings.Contains(content, "\r\n") {
			log.Printf("CRLF DETECTED: %s", filepath.Base(f))
		}
	}

	// 验证 cn_en*.txt 文件存在
	cnEnFiles, _ := filepath.Glob(filepath.Join(rime.OutDir, "en_dicts", "cn_en*.txt"))
	log.Printf("cn_en*.txt files: %d", len(cnEnFiles))

	// 验证 lua 文件存在
	luaFiles, _ := filepath.Glob(filepath.Join(rime.OutDir, "lua", "*.lua"))
	log.Printf("lua files in out/: %d", len(luaFiles))

	// 验证 opencc
	emojiPath := filepath.Join(rime.OutDir, "opencc", "emoji.txt")
	if _, err := os.Stat(emojiPath); os.IsNotExist(err) {
		log.Printf("MISSING: emoji.txt")
	}

	log.Println("Verification complete.")
}
