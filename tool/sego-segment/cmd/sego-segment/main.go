package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/huichen/sego"
)

func main() {
	var segmenter sego.Segmenter
	segmenter.LoadDictionary("../../data/dictionary.txt")

	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		segs := segmenter.Segment([]byte(line))
		words := make([]string, len(segs))
		for i, s := range segs {
			words[i] = s.Token().Text()
		}
		fmt.Println(strings.Join(words, " "))
	}
}
