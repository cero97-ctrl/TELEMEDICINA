#!/usr/bin/env python3
import argparse
import json
import sys

try:
    import chromadb
except ImportError:
    print("Error: Missing 'chromadb'.", file=sys.stderr)
    sys.exit(10)

def main():
    parser = argparse.ArgumentParser(description="Eliminar un recuerdo por ID.")
    parser.add_argument("--id", help="ID del recuerdo a eliminar.")
    parser.add_argument("--text", help="Texto contenido en el recuerdo a eliminar (borra coincidencias).")
    parser.add_argument("--db-path", default=".tmp/chroma_db", help="Ruta a ChromaDB.")
    args = parser.parse_args()

    if not args.id and not args.text:
        print(json.dumps({"status": "error", "message": "Debes proporcionar --id o --text."}))
        sys.exit(1)

    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_or_create_collection(name="agent_memory")
        
        if args.id:
            collection.delete(ids=[args.id])
            print(json.dumps({
                "status": "success", 
                "message": f"Recuerdo {args.id} eliminado correctamente."
            }))
        elif args.text:
            # Buscar IDs por texto
            results = collection.get()
            ids_to_delete = []
            if results['ids']:
                for i, doc in enumerate(results['documents']):
                    if args.text.lower() in doc.lower():
                        ids_to_delete.append(results['ids'][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                print(json.dumps({
                    "status": "success", 
                    "message": f"Se eliminaron {len(ids_to_delete)} recuerdos que contenían '{args.text}'."
                }))
            else:
                print(json.dumps({"status": "error", "message": f"No se encontraron recuerdos con: {args.text}"}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()