package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/go-ego/gse"
)

func main() {
	seg := gse.New("zh", "jp")

	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		words := seg.Cut(line, true)
		fmt.Println(strings.Join(words, " "))
	}
}
