package rime

import (
	"io"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// SchemaConfig 从 .schema.yaml 中解析出的关键信息
type SchemaConfig struct {
	Schema struct {
		SchemaID string `yaml:"schema_id"`
	} `yaml:"schema"`
	Translator struct {
		Dictionary string `yaml:"dictionary"`
	} `yaml:"translator"`
	CustomPhrase struct {
		Dictionary string `yaml:"dictionary"`
		UserDict   string `yaml:"user_dict"`
	} `yaml:"custom_phrase"`
	CNEn struct {
		Dictionary string `yaml:"dictionary"`
		UserDict   string `yaml:"user_dict"`
	} `yaml:"cn_en"`
	MeltEng struct {
		Dictionary string `yaml:"dictionary"`
	} `yaml:"melt_eng"`
	RadicalLookup struct {
		Dictionary string `yaml:"dictionary"`
	} `yaml:"radical_lookup"`
}

// DictConfig 从 .dict.yaml 中解析出的关键信息
type DictConfig struct {
	Name         string   `yaml:"name"`
	ImportTables []string `yaml:"import_tables"`
}

// DefaultConfig 从 default.yaml 中解析的 schema 列表
type DefaultConfig struct {
	SchemaList []struct {
		Schema string `yaml:"schema"`
	} `yaml:"schema_list"`
}

// DictFile 描述一个需要复制和处理的词库文件
type DictFile struct {
	Name         string   // 词库名称 (如 "base", "ext")
	Category     string   // 类别: "cn", "en"
	SrcPath      string   // 源文件绝对路径
	OutRelPath   string   // 输出相对路径 (如 "cn_dicts/base.dict.yaml")
	OutAbsPath   string   // 输出绝对路径
	Columns      int      // 数据列数: 2(字+注音), 3(字+注音+权重), 4(字+权重)
	NeedPinyin   bool     // 是否需要自动注音 (ext)
	NeedWeight   bool     // 是否需要补权重
	IsBase       bool     // 是否为核心词库 (不与其他词库去重)
	DedupFrom    []string // 去重依赖的词库名称列表
}

// FileManifest 构建文件清单
type FileManifest struct {
	Dicts       []*DictFile // 所有词库文件
	SchemaFiles []string    // schema 文件路径 (相对 src/)
	ConfigFiles []string    // 配置文件路径 (相对 src/)
	LuaDir      string      // lua 源目录
}

// DiscoverManifest 扫描 src/ 目录，从 schema 和 dict 的 YAML 配置自动发现所有文件依赖
func DiscoverManifest(srcDir string) *FileManifest {
	m := &FileManifest{}

	// 读取 default.yaml 获取启用的 schema 列表
	defaultYAML, err := os.ReadFile(filepath.Join(srcDir, "config", "default.yaml"))
	if err != nil {
		log.Fatalf("无法读取 default.yaml: %v", err)
	}
	var defCfg DefaultConfig
	yaml.Unmarshal(defaultYAML, &defCfg)

	// 收集所有被引用的 dictionary 名称
	dictNames := map[string]bool{}
	schemaDir := filepath.Join(srcDir, "schema")
	schemaEntries, _ := os.ReadDir(schemaDir)
	for _, entry := range schemaEntries {
		if !strings.HasSuffix(entry.Name(), ".schema.yaml") {
			continue
		}
		m.SchemaFiles = append(m.SchemaFiles, entry.Name())
		schemaYAML, err := os.ReadFile(filepath.Join(schemaDir, entry.Name()))
		if err != nil {
			log.Printf("警告: 无法读取 %s: %v", entry.Name(), err)
			continue
		}
		var sc SchemaConfig
		yaml.Unmarshal(schemaYAML, &sc)

		for _, d := range []string{
			sc.Translator.Dictionary,
			sc.MeltEng.Dictionary,
			sc.RadicalLookup.Dictionary,
		} {
			if d != "" {
				dictNames[d] = true
			}
		}
	}

	// 解析每个主词库的 import_tables，递归收集所有子词库
	dictDir := filepath.Join(srcDir, "dict")
	cnDictDir := filepath.Join(dictDir, "cn")
	enDictDir := filepath.Join(dictDir, "en")

	collected := map[string]*DictFile{}
	var resolveImports func(name string, category string) []string
	resolveImports = func(name string, category string) []string {
		// 主词库在 src/dict/ 下
		mainPath := filepath.Join(dictDir, name+".dict.yaml")
		mainDC := parseDictConfig(mainPath)
		if mainDC == nil {
			return nil
		}

		var files []string
		for _, imp := range mainDC.ImportTables {
			// import_tables 格式: "cn_dicts/base", "en_dicts/en_ext"
			parts := strings.SplitN(imp, "/", 2)
			if len(parts) != 2 {
				continue
			}
			subDir, subName := parts[0], parts[1]
			var subSrcPath string
			var subCategory string
			if subDir == "cn_dicts" {
				subSrcPath = filepath.Join(cnDictDir, subName+".dict.yaml")
				subCategory = "cn"
			} else if subDir == "en_dicts" {
				subSrcPath = filepath.Join(enDictDir, subName+".dict.yaml")
				subCategory = "en"
			} else {
				continue
			}

			if _, exists := collected[subName]; exists {
				continue
			}

			df := classifyDictFile(subSrcPath, subName, subCategory, OutDir)
			collected[subName] = df
			files = append(files, subName)
		}
		return files
	}

	// 为每个被引用的主词库解析 import_tables
	for name := range dictNames {
		idxPath := filepath.Join(dictDir, name+".dict.yaml")
		if _, err := os.Stat(idxPath); err != nil {
			idxPath = ""
		}
		resolveImports(name, "")
	}

	// 补充扫描 cn/ 和 en/ 下被注释但用户可能启用的词库（如 41448）
	// 这些文件会被复制和排序，但不参与 Check 校验
	_ = filepath.Walk(cnDictDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(info.Name(), ".dict.yaml") {
			return nil
		}
		name := strings.TrimSuffix(info.Name(), ".dict.yaml")
		if _, exists := collected[name]; !exists {
			collected[name] = classifyDictFile(path, name, "cn", OutDir)
		}
		return nil
	})
	_ = filepath.Walk(enDictDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(info.Name(), ".dict.yaml") {
			return nil
		}
		name := strings.TrimSuffix(info.Name(), ".dict.yaml")
		if _, exists := collected[name]; !exists {
			collected[name] = classifyDictFile(path, name, "en", OutDir)
		}
		return nil
	})

	for _, df := range collected {
		m.Dicts = append(m.Dicts, df)
	}
	sort.Slice(m.Dicts, func(i, j int) bool {
		return m.Dicts[i].Name < m.Dicts[j].Name
	})

	// 设置去重依赖关系
	baseNames := map[string]bool{}
	extNames := map[string]bool{}
	for _, df := range m.Dicts {
		if df.IsBase && df.Category == "cn" {
			baseNames[df.Name] = true
		}
		if df.Name == "ext" && df.Category == "cn" {
			extNames[df.Name] = true
		}
	}
	for _, df := range m.Dicts {
		// ext 去重 base
		if df.Name == "ext" && df.Category == "cn" {
			for n := range baseNames {
				df.DedupFrom = append(df.DedupFrom, n)
			}
		}
		// tencent 去重 base + ext
		if df.Name == "tencent" && df.Category == "cn" {
			for n := range baseNames {
				df.DedupFrom = append(df.DedupFrom, n)
			}
			for n := range extNames {
				df.DedupFrom = append(df.DedupFrom, n)
			}
		}
	}

	// 收集配置文件和 lua
	m.LuaDir = filepath.Join(srcDir, "lua")
	configDir := filepath.Join(srcDir, "config")
	configEntries, _ := os.ReadDir(configDir)
	for _, entry := range configEntries {
		if !entry.IsDir() {
			m.ConfigFiles = append(m.ConfigFiles, entry.Name())
		}
	}

	return m
}

func parseDictConfig(path string) *DictConfig {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var dc DictConfig
	yaml.Unmarshal(data, &dc)
	return &dc
}

func classifyDictFile(srcPath, name, category, outDir string) *DictFile {
	df := &DictFile{
		Name:   name,
		SrcPath: srcPath,
	}
	dc := parseDictConfig(srcPath)

	if category == "cn" {
		df.Category = "cn"
		df.OutRelPath = filepath.Join("cn_dicts", name+".dict.yaml")
		df.OutAbsPath = filepath.Join(outDir, df.OutRelPath)
		df.NeedWeight = true

		switch name {
		case "8105":
			df.Columns = 3
			df.IsBase = true
			df.NeedPinyin = false
			df.NeedWeight = false
		case "41448":
			df.Columns = 2
			df.IsBase = true
			df.NeedPinyin = false
			df.NeedWeight = false
		case "base":
			df.Columns = 3
			df.IsBase = true
			df.NeedPinyin = false
			df.NeedWeight = false
		case "ext":
			df.Columns = 3
			df.NeedPinyin = true
		case "tencent":
			df.Columns = 4
			df.NeedPinyin = false
		case "others":
			df.Columns = 3
			df.NeedPinyin = false
			df.NeedWeight = false
		default:
			if strings.HasPrefix(name, "med_") {
				df.Columns = 2
				df.NeedPinyin = true
				df.NeedWeight = true
			} else {
				df.Columns = 3
				df.NeedWeight = false
			}
		}
	} else {
		df.Category = "en"
		df.OutRelPath = filepath.Join("en_dicts", name+".dict.yaml")
		df.OutAbsPath = filepath.Join(outDir, df.OutRelPath)
		df.Columns = 2
		df.IsBase = true
		df.NeedPinyin = false
		df.NeedWeight = false
	}

	_ = dc
	return df
}

// DictByName 按名称查找词库
func (m *FileManifest) DictByName(name string) *DictFile {
	for _, d := range m.Dicts {
		if d.Name == name {
			return d
		}
	}
	return nil
}

// DictByPath 按输出路径查找词库
func (m *FileManifest) DictByPath(path string) *DictFile {
	for _, d := range m.Dicts {
		if d.OutAbsPath == path {
			return d
		}
	}
	return nil
}

// BaseDicts 获取所有核心词库
func (m *FileManifest) BaseDicts() []*DictFile {
	var result []*DictFile
	for _, d := range m.Dicts {
		if d.IsBase {
			result = append(result, d)
		}
	}
	return result
}

// CNDicts 获取所有中文词库
func (m *FileManifest) CNDicts() []*DictFile {
	var result []*DictFile
	for _, d := range m.Dicts {
		if d.Category == "cn" {
			result = append(result, d)
		}
	}
	return result
}

// ENDicts 获取所有英文词库
func (m *FileManifest) ENDicts() []*DictFile {
	var result []*DictFile
	for _, d := range m.Dicts {
		if d.Category == "en" {
			result = append(result, d)
		}
	}
	return result
}

// CopyFileContent copies a file from src to dst
func CopyFileContent(src, dst string) {
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

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		dstFile.Close()
		log.Fatalf("Fatal: failed to copy %s: %v", src, err)
	}
	if err := dstFile.Sync(); err != nil {
		dstFile.Close()
		log.Fatalf("Fatal: failed to sync %s: %v", dst, err)
	}
	dstFile.Close()
}

// FixLineEndings 将文件中的 CRLF 转换为 LF，确保 Linux/macOS 下可正常解析
func FixLineEndings(path string) {
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	fixed := strings.ReplaceAll(string(data), "\r\n", "\n")
	if string(data) != fixed {
		os.WriteFile(path, []byte(fixed), 0644)
		log.Printf("Fixed CRLF -> LF: %s", filepath.Base(path))
	}
}

func ensureDir(path string) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		os.MkdirAll(path, 0755)
	}
}
