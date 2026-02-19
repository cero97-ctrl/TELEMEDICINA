#!/usr/bin/env python3
import argparse
import os
import sys
import json
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Añadir el directorio actual al path para importar chat_with_llm
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from chat_with_llm import chat_openai, chat_anthropic, chat_gemini
except ImportError:
    print(json.dumps({"status": "error", "message": "No se pudo importar chat_with_llm.py."}), file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Traducir archivos de texto usando IA.")
    parser.add_argument("--file", required=True, help="Ruta del archivo a traducir.")
    parser.add_argument("--lang", required=True, help="Idioma destino.")
    args = parser.parse_args()

    file_path = args.file
    target_lang = args.lang

    if not os.path.exists(file_path):
        print(json.dumps({"status": "error", "message": f"Archivo no encontrado: {file_path}"}))
        sys.exit(1)

    try:
        if file_path.lower().endswith(".pdf"):
            if PdfReader is None:
                print(json.dumps({"status": "error", "message": "Librería pypdf no instalada."}))
                sys.exit(1)
            reader = PdfReader(file_path)
            content = "\n".join([page.extract_text() for page in reader.pages])
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Error leyendo archivo: {e}"}))
        sys.exit(1)

    prompt = f"""Actúa como un Traductor Técnico experto. Traduce el siguiente contenido al idioma: {target_lang}.

REGLAS:
1. Mantén el formato Markdown/Texto intacto (encabezados, bloques de código, negritas).
2. NO traduzcas nombres de variables, comandos de código o rutas de archivos.
3. Devuelve ÚNICAMENTE el contenido traducido, sin explicaciones extra ni bloques de markdown envolventes (```).

CONTENIDO A TRADUCIR:
{content}
"""

    messages = [{"role": "user", "content": prompt}]

    # Priorizar Gemini como se solicitó
    response = {}
    if os.getenv("GOOGLE_API_KEY"):
        response = chat_gemini(messages)
    elif os.getenv("OPENAI_API_KEY"):
        response = chat_openai(messages, model="gpt-4o")
    elif os.getenv("ANTHROPIC_API_KEY"):
        response = chat_anthropic(messages, model="claude-3-5-sonnet-20240620")
    else:
        print(json.dumps({"status": "error", "message": "No se encontraron API Keys configuradas en .env"}))
        sys.exit(1)

    if "error" in response:
        print(json.dumps({"status": "error", "message": response["error"]}))
        sys.exit(1)

    translated_content = response.get("content", "")

    # Limpieza básica
    if translated_content.startswith("```markdown"):
        translated_content = translated_content.replace("```markdown", "", 1)
    elif translated_content.startswith("```"):
        translated_content = translated_content.replace("```", "", 1)
    if translated_content.endswith("```"):
        translated_content = translated_content[:-3]

    # Generar nombre de archivo de salida
    base, ext = os.path.splitext(file_path)
    
    # Si era PDF, la salida será texto/markdown
    if ext.lower() == ".pdf":
        ext = ".txt"
        
    # Simplificar el idioma para el nombre del archivo (ej. "Inglés" -> "ingles")
    lang_suffix = target_lang.lower().split()[0]
    output_path = f"{base}_{lang_suffix}{ext}"

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated_content.strip())
        
        print(json.dumps({
            "status": "success", 
            "file_path": output_path
        }))
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Error escribiendo archivo: {e}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
