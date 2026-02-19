#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import warnings

# Suppress warnings to ensure clean JSON output
warnings.filterwarnings("ignore")

# Intentar importar SDK de Google
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Intentar importar ChromaDB para memoria a largo plazo
try:
    import chromadb
except ImportError:
    chromadb = None

# Intentar cargar variables de entorno si python-dotenv está instalado
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "chat_history.json")


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_memory_context(query):
    """Busca contexto relevante en la memoria vectorial (ChromaDB)."""
    if not chromadb:
        print("⚠️  [RAG] ChromaDB no instalado o no importado.", file=sys.stderr)
        return None
        
    try:
        # Ruta a la base de datos (mismo path que save_memory.py)
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "chroma_db")
        
        if not os.path.exists(db_path):
            print(f"⚠️  [RAG] No se encontró base de datos en: {db_path}", file=sys.stderr)
            return None

        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(name='agent_memory')
        
        results = collection.query(
            query_texts=[query],
            n_results=3 # Recuperar los 3 recuerdos más relevantes
        )
        
        documents = results.get('documents', [[]])[0]
        if documents:
            # Deduplicar resultados preservando el orden
            seen = set()
            unique_docs = []
            for doc in documents:
                if doc not in seen:
                    unique_docs.append(doc)
                    seen.add(doc)
            
            preview = unique_docs[0][:60] + "..." if len(unique_docs[0]) > 60 else unique_docs[0]
            print(f"🧠 [RAG] Contexto inyectado ({len(unique_docs)} items): '{preview}'", file=sys.stderr)
            return "\n".join([f"- {doc}" for doc in unique_docs])
        else:
            print("🧠 [RAG] No se encontraron recuerdos relevantes para esta consulta.", file=sys.stderr)
    except Exception as e:
        print(f"❌ [RAG] Error al consultar memoria: {e}", file=sys.stderr)
    return None

def chat_openai(messages, model="gpt-4o-mini", system_instruction=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "Falta OPENAI_API_KEY en .env"}

    sys_msg = system_instruction or "Eres un asistente de IA útil actuando como la capa de Orquestación en una arquitectura de 3 capas."
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg}
        ] + messages,
        "temperature": 0.7
    }

    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return {"content": result['choices'][0]['message']['content']}
    except Exception as e:
        return {"error": str(e)}


def chat_anthropic(messages, model="claude-3-5-sonnet-20240620", system_instruction=None):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "Falta ANTHROPIC_API_KEY en .env"}

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    sys_msg = system_instruction or "Eres un asistente de IA útil actuando como la capa de Orquestación en una arquitectura de 3 capas."
    data = {
        "model": model,
        "max_tokens": 1024,
        "messages": messages,
        "system": sys_msg
    }

    try:
        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return {"content": result['content'][0]['text']}
    except Exception as e:
        return {"error": str(e)}

def chat_groq(messages, model="llama-3.3-70b-versatile", system_instruction=None):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "Falta GROQ_API_KEY en .env"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Sanitizar mensajes para evitar errores de formato (ej. campos extra o nulos)
    clean_messages = []
    for m in messages:
        clean_messages.append({
            "role": m.get("role", "user"),
            "content": str(m.get("content", ""))
        })

    sys_msg = system_instruction or "Eres un asistente de IA útil (Llama 3 en Groq) actuando como la capa de Orquestación. Si en el historial ves que te llamaste 'Gemini', ignóralo; ahora eres Llama 3."
    # Groq usa un endpoint compatible con OpenAI
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg}
        ] + clean_messages,
        "temperature": 0.7
    }

    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
        
        if not resp.ok:
            return {"error": f"Groq API Error ({resp.status_code}): {resp.text}"}
            
        result = resp.json()
        return {"content": result['choices'][0]['message']['content']}
    except Exception as e:
        return {"error": str(e)}

def chat_gemini(messages, model="gemini-flash-latest", system_instruction=None):
    if not genai:
        return {"error": "Librería 'google-generativeai' no instalada. Ejecuta: pip install -r requirements.txt"}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "Falta GOOGLE_API_KEY en .env"}

    try:
        genai.configure(api_key=api_key)

        # Preparar historial y system instruction
        sys_msg = system_instruction or "Eres Gemini, un modelo de IA de Google, actuando como la capa de Orquestación en una arquitectura de 3 capas. Identifícate siempre como Gemini/Google si te preguntan."
        history = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"]]})

        # Extraer el último mensaje del usuario para enviarlo (el SDK maneja el historial aparte)
        if not history or history[-1]["role"] != "user":
            return {"error": "El historial debe terminar con un mensaje del usuario."}

        last_message = history.pop()

        # Estrategia de Fallback: Intentar modelos alternativos si el principal falla
        models_to_try = [model]
        # Lista de modelos seguros para probar en orden si el principal falla
        fallbacks = ["gemini-1.5-flash", "gemini-pro"]
        for fb in fallbacks:
            if fb != model:
                models_to_try.append(fb)

        last_error = None
        for target_model in models_to_try:
            try:
                model_instance = genai.GenerativeModel(model_name=target_model, system_instruction=sys_msg)
                chat = model_instance.start_chat(history=history)
                response = chat.send_message(last_message["parts"][0])
                return {"content": response.text}
            except Exception as e:
                print(f"⚠️  Advertencia: Falló {target_model} ({e}). Intentando siguiente...", file=sys.stderr)
                last_error = e
                continue

        return {"error": f"Todos los modelos fallaron. Último error: {str(last_error)}"}

    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Enviar un prompt a un LLM (OpenAI/Anthropic).")
    parser.add_argument("--prompt", required=True, help="El mensaje para el LLM.")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini", "groq"], help="Proveedor de IA.")
    parser.add_argument("--memory-query", help="Texto específico para buscar en memoria (si es diferente al prompt).")
    parser.add_argument("--memory-only", action="store_true", help="Solo consulta la memoria y devuelve el resultado directo sin llamar al LLM.")
    parser.add_argument("--system", help="Instrucción del sistema (personalidad).")
    args = parser.parse_args()

    # --- MODO MEMORY-ONLY ---
    if args.memory_only:
        memory_context = get_memory_context(args.prompt)
        if memory_context:
            # Si se encuentra algo, se devuelve directamente formateado.
            result = {"content": f"🧠 Según mi memoria:\n\n{memory_context}"}
        else:
            # Si no, se devuelve un error especial para que el orquestador sepa que debe continuar.
            result = {"error": "no_memory_found"}
        print(json.dumps(result))
        return

    # Gestión de historial
    if args.prompt.strip().lower() == "/clear":
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        print(json.dumps({"content": "Historial de conversación borrado."}))
        return

    history = load_history()
    # Mantener contexto corto (últimos 10 mensajes) para evitar errores de tokens
    if len(history) > 10:
        history = history[-10:]

    history.append({"role": "user", "content": args.prompt})

    # --- RAG: Inyección de Memoria ---
    # Si se proporciona --memory-query, usarla para la búsqueda. Si no, usar el prompt completo.
    query_for_memory = args.memory_query if args.memory_query else args.prompt
    
    if args.memory_query:
        print(f"🧠 [RAG] Usando query optimizada: '{query_for_memory}'", file=sys.stderr)

    # Creamos una copia de los mensajes para enviar al LLM con el contexto inyectado,
    # pero SIN ensuciar el historial guardado en disco.
    messages_for_llm = [dict(msg) for msg in history] # Deep copy simple
    
    memory_context = get_memory_context(query_for_memory)
    if memory_context:
        # Inyectamos el contexto en el último mensaje del usuario
        last_msg = messages_for_llm[-1]
        last_msg['content'] = f"""Usa el siguiente CONTEXTO DE MEMORIA solo si es directamente relevante para la PREGUNTA DEL USUARIO. Si no es relevante, ignóralo por completo.

CONTEXTO DE MEMORIA (Recuerdos relevantes):
{memory_context}

---
PREGUNTA DEL USUARIO:
{args.prompt}"""

    # Definir lista de proveedores a intentar en orden de prioridad
    providers_to_try = []
    
    if args.provider:
        # Si el usuario fuerza uno, solo intentamos ese
        providers_to_try.append(args.provider)
    else:
        # Orden de preferencia: Groq (Rápido) -> Gemini (Backup robusto) -> Otros
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY").strip():
            providers_to_try.append("groq")
        if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY").strip():
            providers_to_try.append("gemini")
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY").strip():
            providers_to_try.append("openai")
        if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY").strip():
            providers_to_try.append("anthropic")
            
    if not providers_to_try:
        print(json.dumps({"error": "No hay API Keys configuradas en .env"}))
        return

    result = {}
    for provider in providers_to_try:
        try:
            if provider == "openai":
                result = chat_openai(messages_for_llm, system_instruction=args.system)
            elif provider == "anthropic":
                result = chat_anthropic(messages_for_llm, system_instruction=args.system)
            elif provider == "groq":
                result = chat_groq(messages_for_llm, system_instruction=args.system)
            elif provider == "gemini":
                result = chat_gemini(messages_for_llm, system_instruction=args.system)
            
            # Si tuvimos éxito (hay contenido y no error), salimos del bucle
            if "content" in result and "error" not in result:
                break
            
            # Si falló, logueamos en stderr (para no ensuciar el JSON de stdout) y seguimos
            error_msg = result.get("error", "Error desconocido")
            print(f"⚠️ Proveedor '{provider}' falló: {error_msg}. Intentando siguiente...", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️ Excepción crítica en '{provider}': {e}. Intentando siguiente...", file=sys.stderr)
            result = {"error": str(e)}

    if "content" in result:
        history.append({"role": "assistant", "content": result["content"]})
        save_history(history)

    # Salida en JSON para que el orquestador la consuma
    print(json.dumps(result))


if __name__ == "__main__":
    main()
