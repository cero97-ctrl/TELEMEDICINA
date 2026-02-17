#!/usr/bin/env python3
import argparse
import json
import sys
import requests
from bs4 import BeautifulSoup

def main():
    parser = argparse.ArgumentParser(description="Scrape text from a website.")
    parser.add_argument("--url", required=True, help="URL to scrape.")
    parser.add_argument("--output-file", required=True, help="Output file path.")
    args = parser.parse_args()

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(args.url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(f"Source: {args.url}\n\n{text}")
            
        print(json.dumps({"status": "success", "file": args.output_file}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()