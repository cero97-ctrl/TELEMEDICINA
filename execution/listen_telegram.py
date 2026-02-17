#!/usr/bin/env python3
import time
import subprocess
import json
import sys
import os

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_users.txt")

def save_user(chat_id):
    """Registra el ID del usuario para futuros broadcasts."""
    if not chat_id: return
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users = set(f.read().splitlines())
    if str(chat_id) not in users:
        with open(USERS_FILE, 'a') as f:
            f.write(f"{chat_id}\n")

def run_tool(script, args):
    """Ejecuta una herramienta del framework y devuelve su salida JSON."""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Mostrar stderr para depuración (RAG, errores, etc.)
        if result.stderr:
            print(f"   🛠️  [LOG {script}]: {result.stderr.strip()}")
            
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    except Exception as e:
        print(f"Error ejecutando {script}: {e}")
        return None

def main():
    print("📡 Escuchando Telegram... (Presiona Ctrl+C para detener)")
    print("   El agente responderá a cualquier mensaje que le envíes.")

    try:
        while True:
            # 1. Consultar nuevos mensajes
            response = run_tool("telegram_tool.py", ["--action", "check"])
            
            if response and response.get("status") == "error":
                print(f"⚠️ Error en Telegram: {response.get('message')}")

            if response and response.get("status") == "success":
                messages = response.get("messages", [])
                for msg in messages:
                    # Parsear formato "CHAT_ID|MENSAJE"
                    if "|" in msg:
                        sender_id, content = msg.split("|", 1)
                    else:
                        sender_id = None
                        content = msg

                    save_user(sender_id)
                    print(f"\n📩 Mensaje recibido de {sender_id}: '{content}'")
                    
                    reply_text = ""
                    msg = content # Usamos el contenido limpio para la lógica
                    
                    # --- COMANDOS ESPECIALES (Capa 3: Ejecución) ---
                    
                    # 1. DETECCIÓN DE FOTOS
                    if msg.startswith("__PHOTO__:"):
                        try:
                            parts = msg.replace("__PHOTO__:", "").split("|||")
                            file_id = parts[0]
                            caption = parts[1] if len(parts) > 1 else "Describe esta imagen."
                            if not caption.strip(): caption = "Describe qué ves en esta imagen."
                            
                            print(f"   📸 Foto recibida. Descargando ID: {file_id}...")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", "👀 Analizando imagen...", "--chat-id", sender_id])
                            
                            # Descargar
                            local_path = os.path.join(".tmp", f"photo_{int(time.time())}.jpg")
                            run_tool("telegram_tool.py", ["--action", "download", "--file-id", file_id, "--dest", local_path])
                            
                            # Analizar
                            res = run_tool("analyze_image.py", ["--image", local_path, "--prompt", caption])
                            if res and res.get("status") == "success":
                                reply_text = f"👁️ *Análisis Visual:*\n{res.get('description')}"
                            else:
                                reply_text = f"❌ Error analizando imagen: {res.get('message')}"
                                
                        except Exception as e:
                            reply_text = f"❌ Error procesando foto: {e}"

                    # 1.5 DETECCIÓN DE VOZ
                    elif msg.startswith("__VOICE__:"):
                        try:
                            file_id = msg.replace("__VOICE__:", "")
                            print(f"   🎤 Nota de voz recibida. Descargando ID: {file_id}...")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", "👂 Escuchando...", "--chat-id", sender_id])
                            
                            local_path = os.path.join(".tmp", f"voice_{int(time.time())}.ogg")
                            run_tool("telegram_tool.py", ["--action", "download", "--file-id", file_id, "--dest", local_path])
                            
                            # Transcribir
                            res = run_tool("transcribe_audio.py", ["--file", local_path])
                            if res and res.get("status") == "success":
                                text = res.get("text")
                                print(f"   📝 Transcripción: '{text}'")
                                # ¡Truco! Reemplazamos el mensaje de voz por su texto y dejamos que el flujo continúe
                                msg = text
                                run_tool("telegram_tool.py", ["--action", "send", "--message", f"🗣️ Dijiste: \"{text}\"", "--chat-id", sender_id])
                            else:
                                reply_text = "❌ No pude entender el audio."
                        except Exception as e:
                            reply_text = f"❌ Error procesando audio: {e}"

                    # 2. COMANDOS DE TEXTO
                    # (Nota: usamos 'if' aquí en lugar de 'elif' para que el texto transcrito de voz pueda entrar)
                    if msg.startswith("/investigar") or msg.startswith("/research"):
                        topic = msg.split(" ", 1)[1] if " " in msg else ""
                        if not topic:
                            reply_text = "⚠️ Uso: /investigar [tema]"
                        else:
                            print(f"   🔍 Ejecutando investigación sobre: {topic}")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", f"🕵️‍♂️ Investigando sobre '{topic}'... dame unos segundos.", "--chat-id", sender_id])
                            
                            # Ejecutar herramienta de research
                            res = run_tool("research_topic.py", ["--query", topic, "--output-file", ".tmp/tg_research.txt"])
                            
                            if res and res.get("status") == "success":
                                # Leer y resumir resultados
                                try:
                                    with open(".tmp/tg_research.txt", "r", encoding="utf-8") as f:
                                        data = f.read()
                                    print("   🧠 Resumiendo resultados...")
                                    
                                    # Prompt mejorado: pide al LLM que use su memoria (RAG) y los resultados de la búsqueda.
                                    summarization_prompt = f"""Considerando lo que ya sabes en tu memoria y los siguientes resultados de búsqueda sobre '{topic}', crea un resumen conciso para Telegram.

Resultados de Búsqueda:
---
{data}"""
                                    llm_res = run_tool("chat_with_llm.py", ["--prompt", summarization_prompt, "--memory-query", topic])
                                    
                                    if llm_res and "content" in llm_res:
                                        reply_text = llm_res["content"]
                                    elif llm_res and "error" in llm_res:
                                        reply_text = f"⚠️ Error del modelo: {llm_res['error']}"
                                    else:
                                        reply_text = "❌ No se pudo generar el resumen (Respuesta vacía o inválida)."
                                except Exception as e:
                                    reply_text = f"Error procesando resultados: {e}"
                            else:
                                reply_text = "❌ Error al ejecutar la herramienta de investigación."
                    
                    elif msg.startswith("/resumir") or msg.startswith("/summarize"):
                        url = msg.split(" ", 1)[1] if " " in msg else ""
                        if not url:
                            reply_text = "⚠️ Uso: /resumir [url]"
                        else:
                            print(f"   🌐 Resumiendo URL: {url}")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", f"⏳ Leyendo {url}...", "--chat-id", sender_id])
                            
                            # 1. Scrape
                            scrape_res = run_tool("scrape_single_site.py", ["--url", url, "--output-file", ".tmp/web_content.txt"])
                            
                            if scrape_res and scrape_res.get("status") == "success":
                                # 2. Summarize
                                try:
                                    with open(".tmp/web_content.txt", "r", encoding="utf-8") as f:
                                        content = f.read()
                                    
                                    # Truncar si es muy largo (ej. 10k caracteres) para no saturar CLI args
                                    if len(content) > 10000:
                                        content = content[:10000] + "... (truncado)"
                                        
                                    prompt = f"Resume el siguiente contenido web para Telegram:\n\n{content}"
                                    llm_res = run_tool("chat_with_llm.py", ["--prompt", prompt])
                                    
                                    if llm_res and "content" in llm_res:
                                        reply_text = llm_res["content"]
                                    elif llm_res and "error" in llm_res:
                                        reply_text = f"⚠️ Error del modelo: {llm_res['error']}"
                                    else:
                                        reply_text = "❌ Error generando resumen."
                                        
                                except Exception as e:
                                    reply_text = f"❌ Error leyendo contenido: {e}"
                            else:
                                err = scrape_res.get("message") if scrape_res else "Error desconocido"
                                reply_text = f"❌ Error leyendo la web: {err}"

                    elif msg.startswith("/recordar") or msg.startswith("/remember"):
                        memory_text = msg.split(" ", 1)[1] if " " in msg else ""
                        if not memory_text:
                            reply_text = "⚠️ Uso: /recordar [dato a guardar]"
                        else:
                            print(f"   💾 Guardando en memoria: {memory_text}")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", "💾 Guardando nota...", "--chat-id", sender_id])
                            
                            # Ejecutar herramienta de memoria (save_memory.py)
                            res = run_tool("save_memory.py", ["--text", memory_text, "--category", "telegram_note"])
                            
                            if res and res.get("status") == "success":
                                reply_text = "✅ Nota guardada en memoria a largo plazo."
                            else:
                                reply_text = "❌ Error al guardar. (Verifica que save_memory.py exista y funcione)."

                    elif msg.startswith("/memorias") or msg.startswith("/memories"):
                        print("   🧠 Consultando lista de recuerdos...")
                        run_tool("telegram_tool.py", ["--action", "send", "--message", "🧠 Consultando base de datos...", "--chat-id", sender_id])
                        
                        res = run_tool("list_memories.py", ["--limit", "5"])
                        if res and res.get("status") == "success":
                            memories = res.get("memories", [])
                            if not memories:
                                reply_text = "📭 No tengo recuerdos guardados aún."
                            else:
                                reply_text = "🧠 *Últimos recuerdos:*\n"
                                for m in memories:
                                    date = m.get("timestamp", "").replace("T", " ").split(".")[0]
                                    content = m.get("content", "")
                                    mem_id = m.get("id", "N/A")
                                    reply_text += f"🆔 `{mem_id}`\n📅 {date}: {content}\n\n"
                        else:
                            reply_text = "❌ Error al consultar la memoria."

                    elif msg.startswith("/olvidar") or msg.startswith("/forget"):
                        mem_id = msg.split(" ", 1)[1] if " " in msg else ""
                        if not mem_id:
                            reply_text = "⚠️ Uso: /olvidar [ID]"
                        else:
                            print(f"   🗑️ Eliminando recuerdo: {mem_id}")
                            res = run_tool("delete_memory.py", ["--id", mem_id])
                            if res and res.get("status") == "success":
                                reply_text = "✅ Recuerdo eliminado."
                            else:
                                reply_text = f"❌ Error al eliminar: {res.get('message', 'Desconocido')}"

                    elif msg.startswith("/broadcast") or msg.startswith("/anuncio"):
                        announcement = msg.split(" ", 1)[1] if " " in msg else ""
                        if not announcement:
                            reply_text = "⚠️ Uso: /broadcast [mensaje para todos]"
                        else:
                            if os.path.exists(USERS_FILE):
                                with open(USERS_FILE, 'r') as f:
                                    users = f.read().splitlines()
                                count = 0
                                for uid in users:
                                    if uid.strip():
                                        run_tool("telegram_tool.py", ["--action", "send", "--message", f"📢 *ANUNCIO:*\n{announcement}", "--chat-id", uid])
                                        count += 1
                                reply_text = f"✅ Mensaje enviado a {count} usuarios."
                            else:
                                reply_text = "⚠️ No tengo usuarios registrados aún."

                    elif msg.startswith("/ayuda") or msg.startswith("/help"):
                        reply_text = (
                            "🤖 *Comandos Disponibles:*\n\n"
                            "🔹 `/investigar [tema]`: Busca en internet y resume.\n"
                            "🔹 `/resumir [url]`: Lee una web y te dice de qué trata.\n"
                            "🔹 `/recordar [dato]`: Guarda una nota en mi memoria.\n"
                            "🔹 `/memorias`: Lista tus últimos recuerdos guardados.\n"
                            "🔹 `/olvidar [ID]`: Borra un recuerdo específico.\n"
                            "🔹 `/broadcast [msg]`: Envía un mensaje a todos (Admin).\n"
                            "🔹 `/ayuda`: Muestra este menú.\n"
                            "🔹 *Chat normal*: Háblame y te responderé."
                        )

                    elif msg.lower().strip() in ["hola", "hola!", "hi", "hello", "/start"]:
                        reply_text = (
                            "👋 ¡Hola! Soy un Agente de IA.\n\n"
                            "-Soy una creación del prof. *César Rodríguez* junto con su asistente de código *Gemini Code Assist*.\n"
                            "-Mi base de operaciones está en una PC con GNU/Linux en el hogar del profesor.\n"
                            "-Poseo una memoria persistente local la cual uso para responder tus consultas.\n"
                            "-Si no consigo la respuesta a tus consultas en mi memoria, lanzo la pregunta a varios LLMs externos mediante el uso de APIs.\n"
                            "-Mi tarea principal para el cual estoy siendo diseñado tendrá fines educativos y de investigación apoyando al equipo *Tecnología Venezolana*.\n\n"
                            "Usa /ayuda para ver qué puedo hacer."
                        )

                    elif msg.lower().strip() in ["gracias", "gracias!", "thanks", "thank you"]:
                        reply_text = "¡De nada! Estoy aquí para ayudar. 🤖"

                    # --- CHAT GENERAL (Capa 2: Orquestación) ---
                    elif not reply_text: # Solo si no se ha generado respuesta por un comando anterior
                        # Estrategia "Memory-First":
                        # 1. Intentar responder solo con la memoria local. Es más rápido y barato.
                        print("   🧠 Consultando memoria primero...")
                        mem_response = run_tool("chat_with_llm.py", ["--prompt", msg, "--memory-only"])
                        
                        # 2. Si la memoria tiene una respuesta directa, usarla.
                        if mem_response and "content" in mem_response:
                            reply_text = mem_response["content"]
                        else:
                            # 3. Si no, proceder con la consulta normal al LLM (que también usará RAG).
                            print("   🤔 No hay respuesta directa en memoria, consultando al LLM...")
                            llm_response = run_tool("chat_with_llm.py", ["--prompt", msg])
                            
                            if llm_response and "content" in llm_response:
                                reply_text = llm_response["content"]
                            else:
                                error_msg = llm_response.get('error', 'Respuesta vacía') if llm_response else "Error desconocido"
                                reply_text = f"⚠️ Error del Modelo: {error_msg}"
                    
                    # 3. Enviar respuesta a Telegram
                    if reply_text:
                        print(f"   📤 Enviando respuesta: '{reply_text[:60]}...'")
                        res = run_tool("telegram_tool.py", ["--action", "send", "--message", reply_text, "--chat-id", sender_id])
                        if res and res.get("status") == "error":
                            print(f"   ❌ Error al enviar mensaje: {res.get('message')}")
            
            # Esperar un poco antes del siguiente chequeo para no saturar la CPU/API
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 Desconectando servicio de Telegram.")

if __name__ == "__main__":
    main()