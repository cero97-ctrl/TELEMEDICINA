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
    Lists the most recent memories stored in ChromaDB by sorting metadata timestamps.
    """
    parser = argparse.ArgumentParser(description="List recent agent memories.")
    parser.add_argument("--limit", type=int, default=10, help="Number of memories to return.")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Path to ChromaDB.")
    args = parser.parse_args()

    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_or_create_collection(name="agent_memory")
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(2)

    try:
        # Fetch all items to sort them in Python (ChromaDB doesn't support native sort by metadata yet)
        # For a local agent with <10k memories, this is fast enough.
        data = collection.get()
        
        memories = []
        if data['ids']:
            for i in range(len(data['ids'])):
                mem_id = data['ids'][i]
                doc = data['documents'][i] if data['documents'] else ""
                meta = data['metadatas'][i] if data['metadatas'] else {}
                
                memories.append({
                    "id": mem_id,
                    "content": doc,
                    "metadata": meta,
                    "timestamp": meta.get("timestamp", "")
                })
        
        # Sort by timestamp descending (newest first)
        # ISO format strings are sortable lexicographically
        memories.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Slice to limit
        recent_memories = memories[:args.limit]

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(3)

    print(json.dumps({
        "status": "success",
        "count": len(recent_memories),
        "memories": recent_memories
    }, indent=2))

if __name__ == "__main__":
    main()