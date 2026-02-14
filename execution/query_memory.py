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
    Queries the ChromaDB vector store for semantically similar memories.
    """
    parser = argparse.ArgumentParser(description="Query agent memory.")
    parser.add_argument("--query", required=True, help="The question or topic to search for.")
    parser.add_argument("--n-results", type=int, default=3, help="Number of results to return.")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Path to ChromaDB.")
    args = parser.parse_args()

    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_or_create_collection(name="agent_memory")
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(2)

    try:
        results = collection.query(
            query_texts=[args.query],
            n_results=args.n_results
        )
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(3)

    # Format results for easier reading by the LLM
    formatted_results = []
    if results['documents']:
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i] if results['metadatas'] else {}
            dist = results['distances'][0][i] if results['distances'] else 0
            
            formatted_results.append({
                "content": doc,
                "metadata": meta,
                "relevance_distance": dist
            })

    print(json.dumps({
        "status": "success",
        "query": args.query,
        "results": formatted_results
    }, indent=2))

if __name__ == "__main__":
    main()