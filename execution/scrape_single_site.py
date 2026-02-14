import argparse
import json
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(
        "Error: Missing required libraries. Please install them with 'pip install requests beautifulsoup4'",
        file=sys.stderr
    )
    sys.exit(10) # Special exit code for dependency issues


def print_error(message: str, details: str, exit_code: int):
    """Prints a structured error message to stderr and exits."""
    error_data = {
        "status": "error",
        "error_message": message,
        "details": details.strip()
    }
    print(json.dumps(error_data, indent=2), file=sys.stderr)
    sys.exit(exit_code)


def main():
    """
    Main function to scrape a website's main text content.
    Handles CLI arguments, fetching, parsing, and error reporting.
    """
    parser = argparse.ArgumentParser(
        description="Scrapes the main text content from a single URL and saves it to a file."
    )
    parser.add_argument("--url", required=True, help="URL of the website to scrape.")
    parser.add_argument("--output-file", required=True, help="Path to save the scraped content.")
    args = parser.parse_args()

    target_url = args.url
    output_file = Path(args.output_file)

    # --- Fetching ---
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.HTTPError as e:
        print_error(
            f"HTTP Error: The server returned status code {e.response.status_code}.",
            f"URL: {target_url}\nResponse: {e.response.text[:500]}",
            2
        )
    except requests.exceptions.RequestException as e:
        print_error(
            "Network Error: Failed to fetch the URL.",
            f"URL: {target_url}\nError: {str(e)}",
            3
        )

    # --- Parsing and Extraction ---
    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to find common main content tags, fall back to body
        main_content = soup.find('main') or soup.find('article') or soup.body

        if not main_content:
             print_error("Parsing Error: Could not find <body> tag in the HTML document.", "", 4)

        # Get text, separated by newlines, and strip leading/trailing whitespace from each line
        text_content = main_content.get_text(separator='\n', strip=True)

        if not text_content.strip():
            print_error(
                "Validation Error: The extracted content is empty.",
                "This can happen if the page content is rendered by JavaScript. Consider a tool like Selenium.",
                5
            )
    except Exception as e:
        print_error("Parsing Error: An unexpected error occurred while parsing the HTML.", str(e), 4)


    # --- Writing to File ---
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(text_content, encoding='utf-8')
    except IOError as e:
        print_error(f"File Error: Could not write to output file '{output_file}'.", str(e), 6)


    # --- Success Output ---
    output_data = {
        "status": "success",
        "scraped_file_path": str(output_file)
    }
    print(json.dumps(output_data, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()