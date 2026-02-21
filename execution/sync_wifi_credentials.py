#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv, find_dotenv

def main():
    # Cargar variables de entorno
    load_dotenv(find_dotenv(usecwd=True))
    
    ssid = os.getenv("WIFI_SSID")
    password = os.getenv("WIFI_PASSWORD")
    
    if not ssid or not password:
        print("❌ Error: No se encontraron WIFI_SSID o WIFI_PASSWORD en el archivo .env")
        print("   Por favor agrégalos: WIFI_SSID=mi_wifi y WIFI_PASSWORD=mi_clave")
        sys.exit(1)
        
    # Ruta del archivo de cabecera C++ (en el mismo directorio que el .ino)
    # Ajustamos la ruta basándonos en la ubicación de este script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    header_path = os.path.join(script_dir, "wifi_credentials.h")
    
    content = f"""/**
 * ARCHIVO GENERADO AUTOMÁTICAMENTE DESDE .env
 * NO EDITAR MANUALMENTE.
 * NO SUBIR A GITHUB.
 */

#ifndef WIFI_CREDENTIALS_H
#define WIFI_CREDENTIALS_H

#define WIFI_SSID "{ssid}"
#define WIFI_PASSWORD "{password}"

#endif
"""
    
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"✅ Credenciales WiFi sincronizadas en: {header_path}")

if __name__ == "__main__":
    main()