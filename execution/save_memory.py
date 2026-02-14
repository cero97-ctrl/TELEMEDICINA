import argparse
import json
import sys
import uuid
import datetime
from pathlib import Path

try:
    import chromadb
except ImportError:
    print(
        "Error: Missing required library 'chromadb'. Please install it with 'pip install chromadb'",
        file=sys.stderr
    )
    sys.exit(10)

def print_error(message: str, details: str, exit_code: int):
    error_data = {
        "status": "error",
        "error_message": message,
        "details": details.strip()
    }
    print(json.dumps(error_data, indent=2), file=sys.stderr)
    sys.exit(exit_code)

def main():
    """
    Saves a text snippet to the local ChromaDB vector store.
    Generates a unique ID and timestamps the entry.
    """
    parser = argparse.ArgumentParser(description="Save a memory to ChromaDB.")
    parser.add_argument("--text", required=True, help="The content to remember.")
    parser.add_argument("--category", default="general", help="Category tag (e.g., error_fix, preference).")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Path to ChromaDB.")
    args = parser.parse_args()

    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_or_create_collection(name="agent_memory")
    except Exception as e:
        print_error("Database Error: Failed to connect to ChromaDB.", str(e), 2)

    # Generate unique ID and metadata
    memory_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    metadata = {
        "category": args.category,
        "timestamp": timestamp,
        "source": "user_input"
    }

    try:
        collection.add(
            documents=[args.text],
            metadatas=[metadata],
            ids=[memory_id]
        )
    except Exception as e:
        print_error("Storage Error: Failed to save memory.", str(e), 3)

    output_data = {
        "status": "success",
        "memory_id": memory_id,
        "category": args.category,
        "timestamp": timestamp
    }
    print(json.dumps(output_data, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()