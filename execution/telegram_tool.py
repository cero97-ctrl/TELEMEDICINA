#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import time
from dotenv import load_dotenv

# Cargar entorno para obtener credenciales
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", CHAT_ID or "").strip()
OFFSET_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_offset.txt")

def send_message(text, target_chat_id=None):
    """Envía un mensaje al chat configurado."""
    dest_id = target_chat_id or CHAT_ID
    if not TOKEN or not dest_id:
        print(json.dumps({"status": "error", "message": "Faltan credenciales o Chat ID destino."}))
        sys.exit(1)
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": dest_id, "text": text, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(json.dumps({"status": "success", "message": "Mensaje enviado."}))
    except Exception:
        # Si falla (común por errores de sintaxis Markdown), reintentar como texto plano
        try:
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(json.dumps({"status": "success", "message": "Mensaje enviado (texto plano por error de formato)."}))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

def check_messages():
    """Consulta nuevos mensajes (polling) manteniendo el estado del offset."""
    if not TOKEN:
        print(json.dumps({"status": "error", "message": "Falta TELEGRAM_BOT_TOKEN en .env"}))
        sys.exit(1)
        
    offset = 0
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, 'r') as f:
            try:
                offset = int(f.read().strip())
            except:
                offset = 0
    
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": offset, "limit": 10, "timeout": 5}
    
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        messages = []
        max_update_id = offset
        
        for result in data.get("result", []):
            update_id = result["update_id"]
            # Solo procesamos mensajes nuevos
            if update_id >= offset:
                max_update_id = max(max_update_id, update_id + 1)
                
                # Seguridad: Filtrar por CHAT_ID si está definido para ignorar extraños
                msg_chat_id = str(result.get("message", {}).get("chat", {}).get("id", ""))
                
                # Si ALLOWED_USERS es "*", permite a todos. Si no, verifica la lista.
                if ALLOWED_USERS != "*":
                    allowed_list = [u.strip() for u in ALLOWED_USERS.split(",") if u.strip()]
                    if msg_chat_id not in allowed_list:
                        print(f"⚠️ Ignorando mensaje de {msg_chat_id} (No autorizado. Permitidos: '{ALLOWED_USERS}')", file=sys.stderr)
                        continue
                    
                message = result.get("message", {})
                text = message.get("text", "")
                photo = message.get("photo")
                
                if text:
                    messages.append(f"{msg_chat_id}|{text}")
                elif photo:
                    # Telegram envía varias resoluciones, la última es la mejor
                    file_id = photo[-1]["file_id"]
                    caption = message.get("caption", "") or ""
                    # Usamos un prefijo especial para identificar fotos en el listener
                    messages.append(f"{msg_chat_id}|__PHOTO__:{file_id}|||{caption}")
        
        # Guardar nuevo offset para no repetir mensajes
        if max_update_id > offset:
            os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
            with open(OFFSET_FILE, 'w') as f:
                f.write(str(max_update_id))
                
        print(json.dumps({"status": "success", "messages": messages}))
        
    except requests.exceptions.ReadTimeout:
        # Timeout de lectura es normal en polling; devolvemos lista vacía para reintentar silenciosamente
        print(json.dumps({"status": "success", "messages": []}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

def get_chat_id():
    """Obtiene el ID del chat del último mensaje recibido para configuración."""
    if not TOKEN:
        print(json.dumps({"status": "error", "message": "Falta TELEGRAM_BOT_TOKEN en .env"}))
        sys.exit(1)
        
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    # Intentar varias veces (polling) para dar tiempo al usuario
    for _ in range(5):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("result", [])
            if results:
                # Procesar los últimos mensajes para obtener IDs únicos
                users = {}
                for update in reversed(results): # Empezar por el más reciente
                    chat_info = update.get("message", {}).get("chat", {})
                    chat_id = chat_info.get("id")
                    if chat_id and chat_id not in users:
                        username = chat_info.get("username", "N/A")
                        first_name = chat_info.get("first_name", "Usuario")
                        users[chat_id] = f"{first_name} (@{username})"
                
                user_list = [{"id": uid, "name": name} for uid, name in users.items()]
                
                print(json.dumps({"status": "success", "users": user_list, "message": "Copia el ID del estudiante que necesites."}))
                return
            
            time.sleep(2) # Esperar 2 segundos antes de reintentar
            
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)
            
    print(json.dumps({"status": "error", "message": "No se encontraron mensajes recientes. Pide al estudiante que envíe 'Hola' a tu bot ANTES de ejecutar esto."}))
    sys.exit(1)

def download_file(file_id, dest_path):
    """Descarga un archivo desde los servidores de Telegram."""
    if not TOKEN:
        print(json.dumps({"status": "error", "message": "Falta TELEGRAM_BOT_TOKEN"}))
        sys.exit(1)
        
    try:
        # 1. Obtener la ruta del archivo
        info_url = f"https://api.telegram.org/bot{TOKEN}/getFile"
        res = requests.get(info_url, params={"file_id": file_id}, timeout=10)
        res.raise_for_status()
        file_path_remote = res.json()["result"]["file_path"]
        
        # 2. Descargar el contenido
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path_remote}"
        img_data = requests.get(download_url, timeout=20).content
        
        with open(dest_path, 'wb') as f:
            f.write(img_data)
            
        print(json.dumps({"status": "success", "file_path": dest_path}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Herramienta de integración con Telegram.")
    parser.add_argument("--action", choices=["send", "check", "get-id", "download"], required=True, help="Acción a realizar.")
    parser.add_argument("--message", help="Mensaje a enviar (requerido para --action send).")
    parser.add_argument("--chat-id", help="ID del chat destino (opcional, por defecto usa el del .env).")
    parser.add_argument("--file-id", help="ID del archivo a descargar (para --action download).")
    parser.add_argument("--dest", help="Ruta destino (para --action download).")
    
    args = parser.parse_args()
    
    if args.action == "send":
        send_message(args.message or "Notificación vacía", args.chat_id)
    elif args.action == "check":
        check_messages()
    elif args.action == "get-id":
        get_chat_id()
    elif args.action == "download":
        if not args.file_id or not args.dest:
            print(json.dumps({"status": "error", "message": "Faltan argumentos --file-id o --dest"}))
            sys.exit(1)
        download_file(args.file_id, args.dest)

if __name__ == "__main__":
    main()