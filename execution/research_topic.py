import argparse
import json
import sys
from pathlib import Path

try:
    from duckduckgo_search import DDGS
except ImportError:
    print(
        "Error: Missing required library 'duckduckgo_search'. Please install it with 'pip install duckduckgo-search'",
        file=sys.stderr
    )
    sys.exit(10)


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
    Main function to research a topic using DuckDuckGo.
    Saves titles, URLs, and snippets to a text file.
    """
    parser = argparse.ArgumentParser(
        description="Performs a web search for a topic and saves the results."
    )
    parser.add_argument("--query", required=True, help="The search query.")
    parser.add_argument("--output-file", required=True, help="Path to save the research results.")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results to fetch.")
    args = parser.parse_args()

    query = args.query
    output_file = Path(args.output_file)
    max_results = args.max_results

    # --- Execution ---
    results = []
    try:
        # Using DuckDuckGo Search (DDGS)
        with DDGS() as ddgs:
            # ddgs.text() returns a generator of results
            search_gen = ddgs.text(query, max_results=max_results)
            if search_gen:
                results = list(search_gen)
            
    except Exception as e:
        print_error("Search Error: Failed to retrieve results from the search engine.", str(e), 2)

    # --- Formatting Output ---
    if not results:
        content = f"Research Topic: {query}\n"
        content += "=" * 40 + "\n\n"
        content += "No results found."
    else:
        content = f"Research Topic: {query}\n"
        content += f"Found {len(results)} results.\n"
        content += "=" * 40 + "\n\n"

        for i, res in enumerate(results, 1):
            title = res.get('title', 'No Title')
            href = res.get('href', 'No URL')
            body = res.get('body', 'No description available.')
            
            content += f"{i}. {title}\n"
            content += f"   URL: {href}\n"
            content += f"   Summary: {body}\n"
            content += "-" * 20 + "\n"

    # --- Writing to File ---
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding='utf-8')
    except IOError as e:
        print_error(f"File Error: Could not write to output file '{output_file}'.", str(e), 3)

    # --- Success Output ---
    output_data = {
        "status": "success",
        "research_file_path": str(output_file),
        "results_count": len(results)
    }
    print(json.dumps(output_data, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()