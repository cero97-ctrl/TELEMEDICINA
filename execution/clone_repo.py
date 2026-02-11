import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not found. Secrets will not be loaded from .env file.", file=sys.stderr)
    # Define a dummy function if dotenv is not installed
    def load_dotenv():
        pass


def print_error(message: str, stderr: str, exit_code: int):
    """Prints a structured error message to stderr and exits."""
    error_data = {
        "status": "error",
        "error_message": message,
        "details": stderr.strip()
    }
    print(json.dumps(error_data, indent=2), file=sys.stderr)
    sys.exit(exit_code)


def main():
    """
    Main function to clone a GitHub repository.
    Handles CLI arguments, authentication, execution, and error reporting.
    """
    # Load environment variables from .env file for secrets like GITHUB_TOKEN
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Clones a GitHub repository using credentials from .env if available."
    )
    parser.add_argument("--repo-url", required=True, help="URL of the GitHub repository.")
    parser.add_argument("--branch", help="Optional: Specific branch to clone.")
    parser.add_argument("--output-dir", required=True, help="Directory to clone the repository into.")
    args = parser.parse_args()

    repo_url = args.repo_url
    output_dir = Path(args.output_dir)

    # Ensure the parent directory of the output directory exists
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    # --- Command Construction ---
    command = ["git", "clone"]
    if args.branch:
        command.extend(["--branch", args.branch])

    # Handle authentication for private repos if a token is available
    github_token = os.getenv("GITHUB_TOKEN")
    parsed_url = urlparse(repo_url)
    if "github.com" in parsed_url.netloc and github_token:
        # Insert token into URL: https://<token>@github.com/user/repo.git
        netloc_with_token = f"{github_token}@{parsed_url.netloc}"
        authed_url_parts = parsed_url._replace(netloc=netloc_with_token)
        repo_url = urlunparse(authed_url_parts)

    command.extend([repo_url, str(output_dir)])

    # --- Execution and Validation ---
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            stderr = result.stderr
            if "Authentication failed" in stderr:
                print_error("Authentication failed. Ensure GITHUB_TOKEN is set correctly in .env for private repos.", stderr, 2)
            elif "not found" in stderr:
                print_error("Repository or branch not found. Check the URL and branch name.", stderr, 3)
            else:
                print_error("Git clone command failed with an unexpected error.", stderr, 1)

        # Post-execution validation
        if not output_dir.is_dir() or not any(output_dir.iterdir()):
            print_error(f"Validation failed: Git clone seemed to succeed, but the output directory '{output_dir}' is empty or not a directory.", "", 4)

        # --- Success Output ---
        output_data = {"status": "success", "local_repo_path": str(output_dir)}
        print(json.dumps(output_data, indent=2))
        sys.exit(0)

    except FileNotFoundError:
        print_error("Execution failed: 'git' command not found. Is Git installed and in your PATH?", "", 5)

if __name__ == "__main__":
    main()