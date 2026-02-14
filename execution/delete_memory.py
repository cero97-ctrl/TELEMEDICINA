import argparse
import json
import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    print("Error: Missing 'chromadb'.", file=sys.stderr)
    sys.exit(10)

def main():
    """
    Deletes a memory from ChromaDB by its ID.
    """
    parser = argparse.ArgumentParser(description="Delete a memory from ChromaDB.")
    parser.add_argument("--memory-id", required=True, help="The ID of the memory to delete.")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Path to ChromaDB.")
    args = parser.parse_args()

    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_or_create_collection(name="agent_memory")
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(2)

    try:
        # ChromaDB delete by ID
        # Note: ChromaDB does not throw an error if the ID doesn't exist, it just does nothing.
        collection.delete(ids=[args.memory_id])
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(3)

    print(json.dumps({
        "status": "success",
        "deleted_id": args.memory_id,
        "message": "Memory deleted successfully (if it existed)."
    }, indent=2))

if __name__ == "__main__":
    main()