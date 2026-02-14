import argparse
import json
import sys
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
    PoC script to demonstrate saving and retrieving vectors using ChromaDB.
    It initializes a local DB, adds sample memories, and queries them.
    """
    parser = argparse.ArgumentParser(description="Proof of Concept for ChromaDB memory.")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Path to the local ChromaDB storage.")
    parser.add_argument("--collection-name", default="agent_memory", help="Name of the collection.")
    args = parser.parse_args()

    db_path = args.db_path
    collection_name = args.collection_name

    # --- Initialization ---
    try:
        # PersistentClient saves data to disk so it survives between runs
        client = chromadb.PersistentClient(path=db_path)
        
        # Get or create the collection
        collection = client.get_or_create_collection(name=collection_name)
    except Exception as e:
        print_error("Database Error: Failed to initialize ChromaDB.", str(e), 2)

    # --- Simulation: Adding Memories ---
    # In a real scenario, this would come from user inputs or processed text.
    sample_memories = [
        "El usuario está interesado en la arquitectura de agentes de IA.",
        "Python es el lenguaje preferido para los scripts de ejecución en este proyecto.",
        "La memoria a largo plazo permite recordar contextos entre sesiones.",
        "Mem0 es una herramienta que gestiona la memoria de LLMs.",
        "ChromaDB es una base de datos vectorial open source que corre localmente."
    ]
    
    # IDs must be unique strings
    ids = [f"mem_{i}" for i in range(len(sample_memories))]
    metadatas = [{"source": "poc_script", "type": "fact"} for _ in sample_memories]

    try:
        # Upsert adds or updates items
        collection.upsert(
            documents=sample_memories,
            ids=ids,
            metadatas=metadatas
        )
    except Exception as e:
        print_error("Storage Error: Failed to upsert documents.", str(e), 3)

    # --- Simulation: Querying ---
    # We search for something semantically related, not necessarily exact keywords
    query_text = "herramientas de base de datos locales"
    
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=2 # Get top 2 matches
        )
    except Exception as e:
        print_error("Query Error: Failed to query the database.", str(e), 4)

    # --- Output ---
    output_data = {
        "status": "success",
        "database_path": db_path,
        "query_performed": query_text,
        "results": results
    }
    print(json.dumps(output_data, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()