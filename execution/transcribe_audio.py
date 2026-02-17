#!/usr/bin/env python3
import argparse
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print(json.dumps({"status": "error", "message": "Librería google-generativeai no instalada."}))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio usando Gemini.")
    parser.add_argument("--file", required=True, help="Ruta del archivo de audio.")
    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(json.dumps({"status": "error", "message": "Falta GOOGLE_API_KEY."}))
        sys.exit(1)

    genai.configure(api_key=api_key)

    try:
        # Subir archivo a la API de Gemini
        audio_file = genai.upload_file(path=args.file)
        
        # Usar modelo Flash que es rápido y multimodal
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prompt para transcripción fiel
        response = model.generate_content([
            "Transcribe este audio exactamente como se escucha. Si es una instrucción para un bot, transcríbela tal cual.",
            audio_file
        ])
        
        print(json.dumps({"status": "success", "text": response.text.strip()}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()