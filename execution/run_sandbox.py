#!/usr/bin/env python3
import argparse
import json
import sys
import os

try:
    import docker
except ImportError:
    print(json.dumps({"status": "error", "message": "Librería 'docker' no instalada. Ejecuta: pip install docker"}))
    sys.exit(1)

def run_in_sandbox(code_to_run):
    """
    Ejecuta código Python dentro de un contenedor Docker aislado y seguro.
    """
    try:
        client = docker.from_env()
    except docker.errors.DockerException:
        return {"status": "error", "message": "No se puede conectar al demonio de Docker. ¿Está corriendo?"}

    # Definir rutas absolutas para montar volúmenes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    docs_path = os.path.join(project_root, "docs")
    tmp_path = os.path.join(project_root, ".tmp")
    
    # Asegurar que existan
    os.makedirs(docs_path, exist_ok=True)
    os.makedirs(tmp_path, exist_ok=True)

    container = None
    try:
        # Verificar si la imagen existe localmente, si no, avisar que se descargará
        image_name = "agent-sandbox:latest"
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            print(f"   ⚠️ La imagen '{image_name}' no existe. Usando 'python:3.10-slim' como respaldo (más lento).", file=sys.stderr)
            image_name = "python:3.10-slim"

        container = client.containers.run(
            image=image_name,
            command=["python", "-c", code_to_run],
            detach=True,
            network_disabled=False, # Habilitado para permitir 'pip install'
            mem_limit="512m",       # Aumentado para librerías de datos
            cpu_shares=512,
            volumes={
                docs_path: {'bind': '/mnt/docs', 'mode': 'rw'}, # Tus docs (Lectura/Escritura)
                tmp_path: {'bind': '/mnt/out', 'mode': 'rw'}    # Salida temporal (Lectura/Escritura)
            }
        )

        # Esperar a que termine, con un timeout mayor (120s) para permitir instalaciones (pip install)
        result = container.wait(timeout=120)
        
        stdout = container.logs(stdout=True, stderr=False).decode('utf-8').strip()
        stderr = container.logs(stdout=False, stderr=True).decode('utf-8').strip()

        # Ayuda contextual para errores de rutas comunes
        if "FileNotFoundError" in stderr and "/home/" in stderr:
            stderr += "\n\n💡 PISTA: Estás en un Sandbox Docker. Las rutas de tu PC no existen aquí.\n   - Tus documentos están en: /mnt/docs/\n   - Tu carpeta temporal en: /mnt/out/"

        return {
            "status": "success",
            "exit_code": result.get('StatusCode', -1),
            "stdout": stdout,
            "stderr": stderr
        }

    except docker.errors.ContainerError as e:
        return {"status": "error", "message": f"Error en el código: {e.stderr.decode('utf-8')}"}
    except Exception as e: # Captura timeouts y otros errores de Docker
        return {"status": "error", "message": str(e)}
    finally:
        if container:
            container.remove(force=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar código Python en un sandbox de Docker.")
    parser.add_argument("--code", required=True, help="El código Python a ejecutar.")
    args = parser.parse_args()

    output = run_in_sandbox(args.code)
    print(json.dumps(output, indent=2))