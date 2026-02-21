#!/usr/bin/env python3
import argparse
import os
import sys
import json

# Intentar importar SDK de Google y Pillow
try:
    import google.generativeai as genai
    import PIL.Image
except ImportError:
    print(json.dumps({"status": "error", "message": "Faltan librerías. Ejecuta: pip install google-generativeai pillow"}), file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Analizar una imagen usando Gemini Vision.")
    parser.add_argument("--image", required=True, help="Ruta local de la imagen.")
    parser.add_argument("--prompt", default="Describe esta imagen en detalle.", help="Instrucción para el modelo.")
    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(json.dumps({"status": "error", "message": "Falta GOOGLE_API_KEY en .env"}))
        sys.exit(1)

    if not os.path.exists(args.image):
        print(json.dumps({"status": "error", "message": f"Imagen no encontrada: {args.image}"}))
        sys.exit(1)

    try:
        genai.configure(api_key=api_key)
        
        # Usamos gemini-flash-latest que es el alias más estable y compatible
        model = genai.GenerativeModel('gemini-flash-latest')
        
        img = PIL.Image.open(args.image)
        
        # Generar contenido enviando texto + imagen
        response = model.generate_content([args.prompt, img])
        
        print(json.dumps({
            "status": "success",
            "description": response.text
        }))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()