#!/usr/bin/env python3
import argparse
import sys
import os
import time
import json

# Intentar importar requests
try:
    import requests
except ImportError:
    print(json.dumps({"status": "error", "message": "Librería 'requests' no encontrada. Instala: pip install requests"}), file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Capturar una imagen desde un dispositivo ESP32-CAM.")
    parser.add_argument("--ip", required=True, help="Dirección IP de la cámara (ej. 192.168.1.100).")
    parser.add_argument("--output-file", required=True, help="Ruta donde guardar la imagen capturada.")
    parser.add_argument("--timeout", type=int, default=5, help="Tiempo de espera en segundos.")
    parser.add_argument("--retries", type=int, default=3, help="Número de reintentos.")
    
    args = parser.parse_args()

    # Construir URL (asumiendo endpoint estándar '/capture' común en ejemplos de Arduino/ESP32)
    # Si tu firmware usa otro endpoint (ej. /cam-hi.jpg), cámbialo aquí.
    url = f"http://{args.ip}/capture"
    
    print(f"📸 Conectando a {url}...", file=sys.stderr)

    for attempt in range(args.retries):
        try:
            response = requests.get(url, timeout=args.timeout)
            
            if response.status_code == 200:
                # Verificar Content-Type si es posible, pero ESP32 a veces no lo manda bien
                content_type = response.headers.get("Content-Type", "")
                
                # Validación laxa: si es imagen o si tiene contenido sustancial
                if "image" in content_type or len(response.content) > 1000:
                    # Asegurar directorio
                    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
                    
                    with open(args.output_file, "wb") as f:
                        f.write(response.content)
                        
                    print(json.dumps({
                        "status": "success",
                        "image_path": args.output_file,
                        "size_bytes": len(response.content)
                    }))
                    sys.exit(0)
                else:
                    print(f"⚠️ Respuesta recibida pero no parece una imagen válida (Content-Type: {content_type}, Size: {len(response.content)}).", file=sys.stderr)
            else:
                print(f"⚠️ Error HTTP {response.status_code} en intento {attempt + 1}", file=sys.stderr)

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error de conexión en intento {attempt + 1}: {e}", file=sys.stderr)
        
        if attempt < args.retries - 1:
            time.sleep(2)

    # Si llegamos aquí, falló todo
    print(json.dumps({
        "status": "error", 
        "message": f"No se pudo capturar imagen desde {args.ip} tras {args.retries} intentos."
    }))
    sys.exit(1)

if __name__ == "__main__":
    main()