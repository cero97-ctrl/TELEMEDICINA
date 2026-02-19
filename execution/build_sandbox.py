#!/usr/bin/env python3
import docker
import sys
import os

def main():
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"❌ Error conectando a Docker: {e}")
        sys.exit(1)

    print("🐳 Construyendo imagen de Sandbox personalizada (agent-sandbox)...")
    print("   Esto instalará: pandas, numpy, matplotlib, requests, beautifulsoup4, pypdf.")
    print("   ⏳ Paciencia, esto puede tardar unos minutos la primera vez.")

    # Definir el contenido del Dockerfile
    dockerfile_content = """
FROM python:3.10-slim

# Evitar archivos .pyc y buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar librerías pesadas de Ciencia de Datos
RUN pip install --no-cache-dir pandas numpy matplotlib requests beautifulsoup4 pypdf

WORKDIR /app
"""
    
    # Crear un archivo temporal para el contexto de build
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dockerfile_path = os.path.join(project_root, "Dockerfile.sandbox")
    
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    try:
        # Construir la imagen
        image, logs = client.images.build(path=project_root, dockerfile="Dockerfile.sandbox", tag="agent-sandbox:latest", rm=True)
        print("\n✅ Imagen 'agent-sandbox:latest' construida exitosamente.")
        print("   Ahora tus scripts de Python volarán. 🚀")
    except docker.errors.BuildError as e:
        print(f"\n❌ Error en el build: {e}")
        for line in e.build_log:
            if 'stream' in line: print(line['stream'].strip())
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()