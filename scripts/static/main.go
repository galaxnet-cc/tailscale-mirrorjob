package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path"
	"regexp"

	"github.com/gocolly/colly/v2"
)

var staticRe = regexp.MustCompile(`\S+\.tgz`)

var filePath string
var upstream_url string 

func init() {
	flag.StringVar(&filePath, "path", "/tmp/", "download file path")
	upstream_url = os.Getenv("TUNASYNC_UPSTREAM_URL")
	if upstream_url == "" {
		upstream_url = "https://pkgs.tailscale.com/stable/#static"
	}
}

func main() {
	flag.Parse()

	c := colly.NewCollector()
	os.Mkdir(filePath, os.ModePerm)
	// Find and visit all links
	c.OnHTML("li a", func(e *colly.HTMLElement) {
		link := e.Attr("href")
		// 打印链接
		if staticRe.Match([]byte(link)) {
			fmt.Println(link)
			err := downloadFile(path.Join(filePath, link), link)
			if err != nil {
				fmt.Println(err)
			}
		}
	})
	c.OnRequest(func(r *colly.Request) {
		fmt.Println("Visiting", r.URL)
	})
	c.Visit(upstream_url)
}

func downloadFile(filepath string, file string) (err error) {
	_, err = os.Stat(filePath)

	// Check if error is due to file not existing
	if errors.Is(err, os.ErrNotExist) {
		return
	}

	// Create the file
	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	// Get the data
	resp, err := http.Get(fmt.Sprintf("https://dl.tailscale.com/stable/%s", file))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Check server response
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	// Writer the body to file
	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return err
	}

	return nil
}
