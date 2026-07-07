package rime

import (
	"bufio"
	"fmt"
	"log"
	"math"
	"os"
	"path"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/yanyiwu/gojieba"
)

var jieba = gojieba.NewJieba()

// 汉字-拼音 映射
var hanziPinyin = make(map[string][]string) // 使用 check.go 中的 hanPinyin，再经过 onlyOne 替换
// 词组-拼音 映射
var wordPinyin = make(map[string][]string)

// 指定唯一读音
// 1. 同义多音字
// 2. 一般只在特定的词组中发某个音，如「浚xun县」的「浚jun」只在这里念 xun，已经包含了特定的映射，其余的均使用最常见的注音
// 3. 还有一些多音字，一个音是主流常用，一个音基本不会使用，如「奘」的 zhuang/zang，只保留 zang
var onlyOne = map[string]string{
	// 同义多音字，但是两种读音是通用的（有的是全部通用，有的是部分含义通用），暂时只选取一种读音，由其他脚本完成多种注音的处理
	"谁":   "shei",
	"血":   "xue",
	"熟":   "shu",
	"露":   "lu",
	"掴":   "guai",
	"棽":   "shen",
	"爪":   "zhua",
	"薄":   "bo",
	"剥":   "bo",
	"哟":   "yo",
	"嚼":   "jiao",
	"密钥":  "mi yao",
	"公钥":  "gong yao",
	"私钥":  "si yao",
	"甲壳":  "jia ke",
	"掉色":  "diao se",
	"怎么着": "zen me zhe",
	"这么着": "zhe me zhe",
	"那么着": "na me zhe",
	// 其他多音字，指定唯一读音
	"的":   "de",
	"了":   "le",
	"核儿":  "he er",
	"核":   "he",
	"褪下":  "tui xia",
	"褪":   "tui",
	"便便":  "bian bian",
	"便宜":  "pian yi",
	"便":   "bian",
	"尿尿":  "niao niao",
	"尿":   "niao",
	"衣裳":  "yi shang",
	"裳":   "shang",
	"喳喳":  "zha zha",
	"喳":   "zha",
	"脉脉":  "mo mo",
	"脉":   "mai",
	"呱呱":  "gua gua",
	"呱":   "gua",
	"咀":   "ju",
	"大王":  "da wang",
	"大伯":  "da bo",
	"大":   "da",
	"摩挲":  "mo suo",
	"摩":   "mo",
	"澄清":  "cheng qing",
	"澄":   "cheng",
	"出车":  "chu che",
	"车":   "che",
	"约一约": "yue yi yue",
	"约":   "yue",
	"绿营":  "lv ying",
	"绿":   "lv",
	"圈里":  "quan li",
	"圈外":  "quan wai",
	"咱家":  "zan jia",
	"圈":   "quan",
	"伯":   "bo",
	"胖":   "pang",
	"南":   "nan",
	"颈":   "jing",
	"氏":   "shi",
	"度":   "du",
	"柜":   "gui",
	"奘":   "zang",
	"叶":   "ye",
	"吭":   "keng",
	"纶":   "lun",
	"莎":   "sha",
	"噌":   "ceng",
	"解":   "jie",
	"价":   "jia",
	"种":   "zhong",
	"嘚":   "de",
	"浚":   "jun",
	"枸":   "gou",
	"拾":   "shi",
	"塞":   "sai",
	"膻":   "shan",
	"数":   "shu",
	"媞":   "ti",
	"哦":   "o",
	"络":   "luo",
	"俩":   "lia",
	"咋":   "za",
	"否":   "fou",
	"尾":   "wei",
	"弄":   "nong",
	"强":   "qiang",
	"烙":   "lao",
	"卜":   "bu",
	"祭":   "ji",
	"缉":   "ji",
	"侥":   "jiao",
	"驮":   "tuo",
	"陆":   "lu",
	"盖":   "gai",
	"色":   "se",
	"涌":   "yong",
	"栅":   "zha",
	"啜":   "chuo",
	"涡":   "wo",
	"券":   "quan",
	"糜":   "mi",
	"焯":   "chao",
	"藉":   "ji",
	"蚌":   "bang",
	"沌":   "dun",
	"殷":   "yin",
	"翟":   "zhai",
	"腌":   "yan",
	"佛":   "fo",
	"合":   "he",
	"乘":   "cheng",
	"溃":   "kui",
	"牟":   "mou",
	"疟":   "nve",
	"雀":   "que",
	"虹":   "hong",
	"碌":   "lu",
	"捋":   "lv",
	"堡":   "bao",
	"读":   "du",
	"蛤":   "ha",
	"繁":   "fan",
	"巷":   "xiang",
	"磅":   "bang",
	"粘":   "zhan",
	"见":   "jian",
	"筠":   "yun",
	"会":   "hui",
	"铅":   "qian",
	"呢":   "ne",
	"栎":   "li",
	"咽":   "yan",
	"殖":   "zhi",
	"泷":   "long",
	"迫":   "po",
	"囤":   "tun",
	"娜":   "na",
	"纤":   "xian",
	"嘘":   "xu",
	"阿":   "a",
	"泌":   "mi",
	"咯":   "lo",
	"扁":   "bian",
	"综":   "zong",
	"哪":   "na",
	"艾":   "ai",
	"期":   "qi",
	"晟":   "sheng",
	"召":   "zhao",
	"瀑":   "pu",
	"棱":   "leng",
	"区":   "qu",
	"蔓":   "man",
	"亟":   "ji",
	"蔚":   "wei",
	"莘":   "shen",
	"石":   "shi",
	"炮":   "pao",
	"喋":   "die",
	"句":   "ju",
	"杉":   "shan",
	"臭":   "chou",
	"禅":   "chan",
	"埋":   "mai",
	"仇":   "chou",
	"和":   "he",
	"折":   "zhe",
	"单":   "dan",
	"臂":   "bi",
	"提":   "ti",
	"贾":   "jia",
	"澹":   "dan",
	"扛":   "kang",
	"员":   "yuan",
	"戌":   "xu",
	"楷":   "kai",
	"卒":   "zu",
	"兹":   "zi",
	"秘":   "mi",
	"洞":   "dong",
	"番":   "fan",
	"亲":   "qin",
	"洗":   "xi",
	"无":   "wu",
	"缩":   "suo",
	"尺":   "chi",
	"差":   "cha",
	"说":   "shuo",
	"术":   "shu",
	"龟":   "gui",
	"万":   "wan",
	"没":   "mei",
	"查":   "cha",
	"省":   "sheng",
	"卡":   "ka",
	"奇":   "qi",
	"齐":   "qi",
	"择":   "ze",
	"峙":   "zhi",
	"戛":   "jia",
	"绰":   "chuo",
	"葚":   "shen",
	"嘞":   "lei",
	"凹":   "ao",
	"给":   "gei",
	"栖":   "qi",
	"契":   "qi",
	"窨":   "yin",
	"谷":   "gu",
}

func initPinyin() {
	// 从 base、ext 准备结巴的词典和词组拼音映射
	for _, name := range []string{"base", "ext"} {
		dictPath := srcPath(name)
		if dictPath == "" {
			continue
		}
		file, err := os.Open(dictPath)
		if err != nil {
			log.Fatalln(err)
		}

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
			if strings.HasPrefix(line, "#") || line == "" {
				continue
			}
			parts := strings.Split(line, "\t")
			if len(parts) != 3 || !isAllLower(parts[1]) {
				continue
			}
			text, code := parts[0], parts[1]
			weight, err := strconv.Atoi(parts[2])
			if err != nil {
				log.Fatalln(err, line)
			}
			jieba.AddWordEx(text, weight, "")
			wordPinyin[text] = append(wordPinyin[text], code)
		}

		file.Close()
	}

	// 拷贝 hanPinyin 到 hanziPinyin，再从 onlyOne 替换掉映射中的注音
	for k, v := range hanPinyin {
		hanziPinyin[k] = v
	}
	for text, code := range onlyOne {
		if utf8.RuneCountInString(text) == 1 {
			hanziPinyin[text] = []string{code}
		} else {
			wordPinyin[text] = []string{code}
		}
	}
}

// Pinyin 半自动的注音
// 能准确注音的，注音；拿不准的，留着手动注音
//
// 按 dict 的 columns 声明解析每行：
//   type 1 (text)           → 补注音 + 权重 0
//   type 3 (text,code,weight) → code 为空或含汉字则重新注音，保留权重
//   type 4 (text,weight)      → 补注音，保留权重
func Pinyin(dictPath string) {
	defer printlnTimeCost("注音\t"+path.Base(dictPath), time.Now())

	df := Manifest.DictByPath(dictPath)
	columns := 3
	if df != nil {
		columns = df.Columns
	}

	file, err := os.ReadFile(dictPath)
	if err != nil {
		log.Fatalln(err)
	}
	lines := strings.Split(string(file), "\n")

	isMark := false
	for i, line := range lines {
		if strings.Contains(dictPath, "temp") {
			isMark = true
		}
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
		text := parts[0]
		var code, weight string

		switch columns {
		case 1:
			code = generatePinyin(text)
			weight = "0"
		case 3:
			code, weight = "", ""
			if len(parts) >= 2 {
				code = parts[1]
			}
			if len(parts) >= 3 {
				weight = parts[2]
			}
			if code == "" || containsHan(code) {
				code = generatePinyin(text)
			}
		case 4:
			code = generatePinyin(text)
			if len(parts) >= 2 {
				weight = parts[1]
			}
		default:
			log.Fatalf("Pinyin: 不支持的 columns 类型 %d: %s", columns, line)
		}

		lines[i] = text + "\t" + code + "\t" + weight
	}

	resultString := strings.Join(lines, "\n")
	err = os.WriteFile(dictPath, []byte(resultString), 0644)
	if err != nil {
		log.Fatal(err)
	}
}

// 生成拼音
// 多音字的处理：
// 如果 wordPinyin 没有包含多音字的映射， 返回 []string{"gao xing 地 beng qi lai"} 然后手动注音
// 如果 wordPinyin 包含「高兴地 gao xing de」，则将 "高兴地蹦起来" 返回 []string{"gao xing de beng qi lai"}
func generatePinyin(s string) string {
	var r string

	words := jieba.Cut(s, true)
	for _, word := range words {
		// 非 CJK 字符跳过，不参与拼音（如 %, /, (, ), 希腊字母, 罗马数字, A型 等）
		firstRune, _ := utf8.DecodeRuneInString(word)
		if !unicode.Is(unicode.Han, firstRune) {
			continue
		}

		// 单字，且不是多音字
		if utf8.RuneCountInString(word) == 1 && len(hanziPinyin[word]) == 1 {
			r += hanziPinyin[word][0] + " "
			continue
		}

		// 词组，且映射中没有多种注音
		if len(wordPinyin[word]) == 1 {
			r += wordPinyin[word][0] + " "
			continue
		}

		// 词组，未能通过映射进行注音，但本身不包含多音字
		notPolyphone := false
		for _, char := range word {
			pys := hanziPinyin[string(char)]
			if len(pys) > 1 {
				notPolyphone = true
				break
			}
		}
		if !notPolyphone {
			for _, char := range word {
				if pys := hanziPinyin[string(char)]; len(pys) > 0 {
					r += pys[0] + " "
				}
			}
			continue
		}

		// 其他的，逐字取首个读音作为近似注音
		for _, char := range word {
			if pys := hanziPinyin[string(char)]; len(pys) > 0 {
				r += pys[0] + " "
			}
		}
	}

	return strings.TrimSpace(r)
}

// GeneratePinyinTest 临时测试一个
func GeneratePinyinTest(s string) {
	words := jieba.Cut(s, true)
	r := generatePinyin(s)
	fmt.Printf("%s %q\n", words, r)
}

// SetMedWeight 为医学词库统一权重
//
// 权重策略（按词库类型）：
//   med_merged: 源文件有教材词频，线性归一化到 [100, 10000]，保留内部相对排序
//   其他 curated（药品、方剂、药材等）: 人工整理的高质量列表，按字数赋较高权重
//   med_sogou: 自动搜集的大词库（279K），按字数赋较低权重，不淹没 curated 内容
func SetMedWeight(dictName, dictPath string) {
	file, err := os.ReadFile(dictPath)
	if err != nil {
		log.Printf("  跳过 %s: %v", path.Base(dictPath), err)
		return
	}
	lines := strings.Split(string(file), "\n")

	switch {
	case dictName == "med_merged":
		normalizeMergedWeight(lines)
	case dictName == "med_sogou":
		assignSogouWeight(lines)
	default:
		assignCuratedMedWeight(lines)
	}

	result := strings.Join(lines, "\n")
	os.WriteFile(dictPath, []byte(result), 0644)
	log.Printf("  权重: %s", path.Base(dictPath))
}

// normalizeMergedWeight 将 med_merged 的教材词频用对数归一化到 [200, 5000]
// 对数变换压缩极端值，避免大量低频词堆在底部
func normalizeMergedWeight(lines []string) {
	// 第一遍：找最小和最大权重
	oldMin, oldMax := 0, 0
	for _, line := range lines {
		parts := strings.Split(line, "\t")
		if len(parts) < 3 || parts[0] == "" || strings.HasPrefix(line, "#") {
			continue
		}
		w, err := strconv.Atoi(parts[2])
		if err != nil || w <= 0 {
			continue
		}
		if oldMin == 0 || w < oldMin {
			oldMin = w
		}
		if w > oldMax {
			oldMax = w
		}
	}
	if oldMax <= oldMin {
		return
	}

	// 第二遍：归一化
	isMark := false
	for i, line := range lines {
		if !isMark {
			if strings.HasPrefix(line, mark) || line == "..." {
				isMark = true
			}
			continue
		}
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 3 || parts[0] == "" {
			continue
		}
		oldWeight, err := strconv.Atoi(parts[2])
		if err != nil || oldWeight <= 0 {
			// 源词频为 0 的条目按字数赋底限权重
			charCount := utf8.RuneCountInString(parts[0])
			var weight int
			switch {
			case charCount <= 5:
				weight = 50
			case charCount <= 10:
				weight = 20
			default:
				weight = 5
			}
			lines[i] = fmt.Sprintf("%s\t%s\t%d", parts[0], parts[1], weight)
			continue
		}
		// 对数映射：log10(oldWeight) → [200, 5000]
		logOld := math.Log10(float64(oldWeight))
		logMax := math.Log10(float64(oldMax))
		newWeight := 200 + int(logOld*4800/logMax)
		lines[i] = fmt.Sprintf("%s\t%s\t%d", parts[0], parts[1], newWeight)
	}
}

// assignCuratedMedWeight 为人工整理的医学词库（药品、方剂、药材等）按字数赋权重
// ≤5 字: 500  6-10 字: 100  >10 字: 20
func assignCuratedMedWeight(lines []string) {
	isMark := false
	for i, line := range lines {
		if !isMark {
			if strings.HasPrefix(line, mark) || line == "..." {
				isMark = true
			}
			continue
		}
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 3 || parts[0] == "" {
			continue
		}
		oldWeight, _ := strconv.Atoi(parts[2])
		if oldWeight != 0 {
			continue
		}
		charCount := utf8.RuneCountInString(parts[0])
		var weight int
		switch {
		case charCount <= 5:
			weight = 500
		case charCount <= 10:
			weight = 100
		default:
			weight = 20
		}
		lines[i] = fmt.Sprintf("%s\t%s\t%d", parts[0], parts[1], weight)
	}
}

// assignSogouWeight 为搜狗医学词库按字数赋较低权重
// ≤5 字: 100  6-10 字: 20  >10 字: 5
func assignSogouWeight(lines []string) {
	isMark := false
	for i, line := range lines {
		if !isMark {
			if strings.HasPrefix(line, mark) || line == "..." {
				isMark = true
			}
			continue
		}
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 3 || parts[0] == "" {
			continue
		}
		oldWeight, _ := strconv.Atoi(parts[2])
		if oldWeight != 0 {
			continue
		}
		charCount := utf8.RuneCountInString(parts[0])
		var weight int
		switch {
		case charCount <= 5:
			weight = 100
		case charCount <= 10:
			weight = 20
		default:
			weight = 5
		}
		lines[i] = fmt.Sprintf("%s\t%s\t%d", parts[0], parts[1], weight)
	}
}

// 判断 code 是否全小写，不判断空格
func isAllLower(s string) bool {
	for _, ch := range s {
		if ch == ' ' {
			continue
		}
		if !unicode.IsLower(ch) {
			return false
		}
	}
	return true
}

// 判断字符串是否包含汉字
func containsHan(s string) bool {
	for _, r := range s {
		if unicode.Is(unicode.Han, r) {
			return true
		}
	}
	return false
}
