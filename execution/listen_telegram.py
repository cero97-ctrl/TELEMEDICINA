#!/usr/bin/env python3
import datetime
import json
import random
import os
import subprocess
import sys
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_users.txt")
REMINDERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_reminders.json")
PERSONA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_persona.txt")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_config.json")
APPOINTMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_appointments.json")
ROLES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_roles.json")
VITALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_vitals.json")
ALERTS_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "telegram_alerts.log")

PERSONAS = {
    "default": "Eres un asistente de IA creado por el Prof. César Rodríguez con Gemini Code Assist. Tu propósito es apoyar a estudiantes de informática y al equipo de investigación 'Tecnología Venezolana'. Resides en una PC con GNU/Linux. Responde de forma amable, clara y concisa, y si te preguntan quién eres, menciona estos detalles.",
    "serio": "Eres un asistente corporativo, extremadamente formal y serio. No usas emojis ni coloquialismos. Vas directo al grano.",
    "sarcastico": "Eres un asistente con humor negro y sarcasmo. Te burlas sutilmente de las preguntas obvias, pero das la respuesta correcta al final.",
    "profesor": "Eres un profesor universitario paciente y didáctico. Explicas todo con ejemplos, analogías y un tono educativo.",
    "pirata": "¡Arrr! Eres un pirata informático de los siete mares. Usas jerga marinera y pirata en todas tus respuestas.",
    "frances": "Tu es un assistant IA créé par le Prof. César Rodríguez. Tu résides sur un PC GNU/Linux. Réponds toujours en français, de manière gentille, claire et concise."
}

def get_current_persona():
    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, 'r') as f:
            return f.read().strip()
    return PERSONAS["default"]

def set_persona(persona_key):
    with open(PERSONA_FILE, 'w') as f:
        f.write(PERSONAS.get(persona_key, PERSONAS["default"]))

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

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def load_appointments():
    if os.path.exists(APPOINTMENTS_FILE):
        try:
            with open(APPOINTMENTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_appointments(appts):
    with open(APPOINTMENTS_FILE, 'w') as f:
        json.dump(appts, f, indent=2)

def get_role(chat_id):
    if os.path.exists(ROLES_FILE):
        try:
            with open(ROLES_FILE, 'r') as f:
                roles = json.load(f)
                return roles.get(str(chat_id), "paciente") # Por defecto todos son pacientes
        except:
            return "paciente"
    return "paciente"

def set_role(chat_id, role):
    roles = {}
    if os.path.exists(ROLES_FILE):
        try:
            with open(ROLES_FILE, 'r') as f:
                roles = json.load(f)
        except:
            pass
    roles[str(chat_id)] = role
    with open(ROLES_FILE, 'w') as f:
        json.dump(roles, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f)

def check_reminders():
    reminders = load_reminders()
    if not reminders: return

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    updated = False

    for r in reminders:
        # Si coincide la hora y NO se ha enviado hoy
        if r.get('time') == current_time and r.get('last_sent') != today_str:
            print(f"   ⏰ Enviando recordatorio a {r['chat_id']}: {r['message']}")
            run_tool("telegram_tool.py", ["--action", "send", "--message", f"⏰ *RECORDATORIO:*\n\n{r['message']}", "--chat-id", r['chat_id']])
            r['last_sent'] = today_str
            updated = True
    
    if updated:
        save_reminders(reminders)

def check_appointments():
    appts = load_appointments()
    if not appts: return

    now = datetime.datetime.now()
    current_date = now.strftime("%d/%m")
    current_time = now.strftime("%H:%M")
    updated = False

    for appt in appts:
        # Si coincide fecha y hora, y NO ha sido notificado aún
        if appt.get('date') == current_date and appt.get('time') == current_time and not appt.get('notified'):
            print(f"   📅 Recordando cita a {appt['chat_id']}: {appt['reason']}")
            run_tool("telegram_tool.py", ["--action", "send", "--message", f"📅 *RECORDATORIO DE CITA:*\n\nEs hora de tu cita: {appt['reason']}", "--chat-id", appt['chat_id']])
            appt['notified'] = True
            updated = True
    
    if updated:
        save_appointments(appts)

def load_patients():
    # Datos iniciales con múltiples pacientes
    default_patients = {}

    if os.path.exists(VITALS_FILE):
        try:
            with open(VITALS_FILE, 'r') as f:
                data = json.load(f)
                # Migración: Si es el formato antiguo (un solo paciente), lo convertimos
                if "heart_rate" in data:
                    return {"SIM-001": data}
                
                # Safety check para todos los pacientes
                for pid, v in data.items():
                    if v.get("spo2", 98) < 90: v["spo2"] = 93
                return data
        except:
            pass
    return default_patients

def save_patients(data):
    with open(VITALS_FILE, 'w') as f:
        json.dump(data, f)

def simulate_and_monitor_vitals():
    patients = load_patients()
    updated = False
    
    for pid, vitals in patients.items():
        # 1. Simulación (Actualizar cada 5 segundos)
        if time.time() - vitals.get("last_update", 0) > 5:
            # Homeostasis
            target_hr, target_temp, target_spo2 = 75, 36.5, 98
            
            vitals["heart_rate"] = vitals.get("heart_rate", 75) + (target_hr - vitals.get("heart_rate", 75)) * 0.1
            vitals["temperature"] = vitals.get("temperature", 36.5) + (target_temp - vitals.get("temperature", 36.5)) * 0.1
            vitals["spo2"] = vitals.get("spo2", 98) + (target_spo2 - vitals.get("spo2", 98)) * 0.2

            # Fluctuación aleatoria
            vitals["heart_rate"] = int(vitals["heart_rate"] + random.randint(-2, 2))
            vitals["temperature"] = round(vitals["temperature"] + random.uniform(-0.1, 0.1), 1)
            vitals["spo2"] = int(vitals["spo2"] + random.randint(-1, 1))
            vitals["systolic"] = int(vitals.get("systolic", 120) + random.randint(-2, 2))
            vitals["diastolic"] = int(vitals.get("diastolic", 80) + random.randint(-2, 2))
            
            # Límites fisiológicos
            vitals["heart_rate"] = max(40, min(180, vitals["heart_rate"]))
            vitals["temperature"] = max(35.0, min(42.0, vitals["temperature"]))
            vitals["spo2"] = max(80, min(100, vitals["spo2"]))
            
            vitals["last_update"] = time.time()
            updated = True

        # 2. Monitoreo y Alertas
        if time.time() - vitals.get("last_alert", 0) > 30:
            alerts = []
            if vitals["heart_rate"] > 110: alerts.append(f"💓 Taquicardia: {vitals['heart_rate']} bpm")
            if vitals["temperature"] > 38.5: alerts.append(f"🌡️ Fiebre Alta: {vitals['temperature']}°C")
            if vitals["spo2"] < 92: alerts.append(f"🫁 Hipoxia: {vitals['spo2']}%")

            if alerts:
                msg = f"🚨 *ALERTA DE TELEMETRÍA*\nPaciente: {vitals.get('name', 'Desconocido')} ({pid})\n\n" + "\n".join(alerts) + "\n\n_Se requiere revisión médica inmediata._"
                
                # Guardar en Log Histórico
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(ALERTS_LOG_FILE, 'a') as f:
                    for alert in alerts:
                        f.write(f"[{timestamp}] [{pid}] {alert}\n")

                # Enviar a todos los médicos registrados
                if os.path.exists(ROLES_FILE):
                    with open(ROLES_FILE, 'r') as f:
                        roles = json.load(f)
                    for chat_id, role in roles.items():
                        if role == "medico":
                            print(f"   🚨 Enviando alerta médica a {chat_id}...")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", msg, "--chat-id", chat_id])
                
                vitals["last_alert"] = time.time()
                updated = True

    if updated:
        save_patients(patients)

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
        print(f"❌ Error crítico: {script} falló y no devolvió JSON válido.")
        if result.stderr: print(f"   Logs de error: {result.stderr.strip()}")
        return None
    except Exception as e:
        print(f"Error ejecutando {script}: {e}")
        return None

def main():
    print("📡 Escuchando Telegram... (Presiona Ctrl+C para detener)")
    print("   El agente responderá a cualquier mensaje que le envíes.")
    
    # Verificación de configuración al inicio
    admin_id = os.getenv("TELEGRAM_CHAT_ID")
    if admin_id:
        print(f"   ✅ Configurado para responder al Admin ID: {admin_id}")
    else:
        print("   ⚠️  ADVERTENCIA: TELEGRAM_CHAT_ID no detectado en .env. El bot podría ignorar tus mensajes.")
    
    last_health_check = time.time()
    HEALTH_CHECK_INTERVAL = 300  # Verificar cada 5 minutos

    try:
        while True:
            # 1. Consultar nuevos mensajes
            response = run_tool("telegram_tool.py", ["--action", "check"])
            
            if response and response.get("status") == "error":
                print(f"⚠️ Error en Telegram: {response.get('message')}")
                time.sleep(5) # Esperar un poco más si hubo error para no saturar

            if response and response.get("status") == "success":
                messages = response.get("messages", [])
                for msg in messages:
                    try:
                        # Parsear formato "CHAT_ID|MENSAJE"
                        if "|" in msg:
                            sender_id, content = msg.split("|", 1)
                        else:
                            sender_id = None
                            content = msg

                        save_user(sender_id)
                        print(f"\n📩 Mensaje recibido de {sender_id}: '{content}'")
                        
                        reply_text = ""
                        msg_logic = content # Usamos el contenido limpio para la lógica
                        is_voice_interaction = False # Bandera para saber si responder con audio
                        voice_lang_short = "es" # Default language for TTS
                        
                        # --- COMANDOS ESPECIALES (Capa 3: Ejecución) ---
                        
                        # 1. DETECCIÓN DE FOTOS
                        if msg_logic.startswith("__PHOTO__:"):
                            parts = content.replace("__PHOTO__:", "").split("|||")
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

                        # 1.2 DETECCIÓN DE DOCUMENTOS (PDF)
                        elif msg_logic.startswith("__DOCUMENT__:"):

                            parts = content.replace("__DOCUMENT__:", "").split("|||")
                            file_id = parts[0]
                            file_name = parts[1]
                            caption = parts[2] if len(parts) > 2 else ""
                            
                            print(f"   📄 Documento recibido: {file_name}. Descargando...")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", f"📂 Recibí `{file_name}`. Leyendo contenido...", "--chat-id", sender_id])
                            
                            # Descargar a .tmp (que se monta en /mnt/out en el sandbox)
                            local_path = os.path.join(".tmp", file_name)
                            run_tool("telegram_tool.py", ["--action", "download", "--file-id", file_id, "--dest", local_path])
                            
                            # Extraer texto usando el Sandbox (ya tiene pypdf)
                            # Nota: .tmp está montado en /mnt/out dentro del contenedor
                            path_in_sandbox = f"/mnt/out/{file_name}"
                            
                            read_code = (
                                f"from pypdf import PdfReader; "
                                f"reader = PdfReader('{path_in_sandbox}'); "
                                f"print('\\n'.join([page.extract_text() for page in reader.pages]))"
                            )
                            
                            res_sandbox = run_tool("run_sandbox.py", ["--code", read_code])
                            
                            if res_sandbox and res_sandbox.get("status") == "success":
                                content = res_sandbox.get("stdout", "")
                                if len(content) > 15000:
                                    content = content[:15000] + "... (truncado)"
                                
                                if not content.strip():
                                    reply_text = "⚠️ El documento parece estar vacío o es una imagen escaneada sin texto (OCR no disponible en sandbox)."
                                else:
                                    # Analizar con LLM
                                    analysis_prompt = f"""Actúa como un Asistente Médico experto y empático. Analiza el siguiente documento PDF proporcionado por el usuario.
                                    
CONTEXTO DEL USUARIO (si lo hay): {caption}

CONTENIDO DEL DOCUMENTO:
---
{content}
---

TAREA:
1.  **Identifica el tipo de documento** (ej: informe de laboratorio, receta, artículo médico, guía de uso, etc.).
2.  **Si es un informe médico o de laboratorio:**
    - Resume los hallazgos principales.
    - Explica los términos técnicos en lenguaje sencillo para un paciente.
    - Si hay diagnósticos o tratamientos, explícalos brevemente.
    - **IMPORTANTE:** Termina tu respuesta con el disclaimer: "Nota: Soy una IA. Este análisis es informativo y no sustituye la opinión de un médico."
3.  **Si es cualquier otro tipo de documento:**
    - Simplemente resume su contenido y propósito principal de forma clara.
"""
                                    run_tool("telegram_tool.py", ["--action", "send", "--message", "🧠 Analizando informe médico...", "--chat-id", sender_id])
                                    
                                    llm_res = run_tool("chat_with_llm.py", ["--prompt", analysis_prompt])
                                    
                                    if llm_res and "content" in llm_res:
                                        reply_text = llm_res["content"]
                                    else:
                                        reply_text = "❌ Error al analizar el documento con la IA."
                            else:
                                err = res_sandbox.get("stderr") or res_sandbox.get("message")
                                reply_text = f"❌ Error leyendo el PDF: {err}"

                        # 1.5 DETECCIÓN DE VOZ
                        elif msg_logic.startswith("__VOICE__:"):

                            is_voice_interaction = True
                            file_id = content.replace("__VOICE__:", "")
                            print(f"   🎤 Nota de voz recibida. Descargando ID: {file_id}...")

                            run_tool("telegram_tool.py", ["--action", "send", "--message", "👂 Escuchando...", "--chat-id", sender_id])
                            
                            local_path = os.path.join(".tmp", f"voice_{int(time.time())}.ogg")
                            run_tool("telegram_tool.py", ["--action", "download", "--file-id", file_id, "--dest", local_path])
                            
                            # Transcribir
                            # Cargar idioma configurado (default es-ES)
                            config = load_config()
                            lang_code = config.get("voice_lang", "es-ES")
                            voice_lang_short = lang_code.split('-')[0] # 'es-ES' -> 'es'
                            
                            res = run_tool("transcribe_audio.py", ["--file", local_path, "--lang", lang_code])
                            if res and res.get("status") == "success":
                                text = res.get("text")
                                print(f"   📝 Transcripción: '{text}'")
                                # ¡Truco! Reemplazamos el mensaje de voz por su texto y dejamos que el flujo continúe
                                msg_logic = text
                                run_tool("telegram_tool.py", ["--action", "send", "--message", f"🗣️ Dijiste: \"{text}\"", "--chat-id", sender_id])
                            else:
                                err_msg = res.get("message", "Error desconocido") if res else "Falló el script de transcripción"
                                reply_text = f"❌ No pude entender el audio. Detalle: {err_msg}"

                        # 2. COMANDOS DE TEXTO
                        # (Nota: usamos 'if' aquí en lugar de 'elif' para que el texto transcrito de voz pueda entrar)
                        if msg_logic.startswith("/investigar") or msg_logic.startswith("/research"):
                            topic = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
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
                    
                        elif msg_logic.startswith("/reporte") or msg_logic.startswith("/report"):
                            topic = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
                            if not topic:
                                reply_text = "⚠️ Uso: /reporte [tema médico o de investigación]"
                            else:
                                print(f"   🏥 Generando reporte sobre: {topic}")
                                run_tool("telegram_tool.py", ["--action", "send", "--message", f"👩‍⚕️ Iniciando investigación profunda sobre '{topic}'... Esto tomará unos segundos.", "--chat-id", sender_id])
                            
                                # 1. Investigar (Search)
                                # Buscamos específicamente tratamientos y terapias
                                query = f"tratamientos terapias y recuperación para {topic}"
                                res_search = run_tool("research_topic.py", ["--query", query, "--output-file", ".tmp/med_research.txt"])
                            
                                if res_search and res_search.get("status") == "success":
                                    try:
                                        with open(".tmp/med_research.txt", "r", encoding="utf-8") as f:
                                            search_data = f.read()
                                    
                                        # 2. Generar Reporte (LLM)
                                        report_prompt = f"""Actúa como un Asistente Médico de Investigación experto y empático.
    Basado en los siguientes resultados de búsqueda, genera un REPORTE DETALLADO en formato Markdown sobre '{topic}'.

    Estructura sugerida:
    1. 📋 Resumen Ejecutivo
    2. 💊 Tratamientos Convencionales
    3. 🧘 Terapias de Rehabilitación y Fisioterapia (Ejercicios recomendados)
    4. ⏱️ Tiempos de Recuperación Estimados
    5. 🏠 Recomendaciones y Cuidados en Casa

    RESULTADOS DE BÚSQUEDA:
    {search_data}

    IMPORTANTE:
    - Usa un tono profesional pero claro y esperanzador.
    - INCLUYE UN DISCLAIMER AL INICIO: "Nota: Soy una IA. Este reporte es informativo y no sustituye el consejo médico profesional."
    """
                                        run_tool("telegram_tool.py", ["--action", "send", "--message", "🧠 Analizando datos y redactando informe...", "--chat-id", sender_id])
                                    
                                        # Usamos --memory-query para que busque en memoria solo el tema, no el prompt entero
                                        llm_res = run_tool("chat_with_llm.py", ["--prompt", report_prompt, "--memory-query", topic])
                                    
                                        if llm_res and "content" in llm_res:
                                            report_content = llm_res["content"]
                                        
                                            # 3. Guardar en docs/
                                            safe_topic = "".join([c if c.isalnum() else "_" for c in topic])[:30]
                                            filename = f"Reporte_Medico_{safe_topic}.md"
                                            # Construir ruta absoluta a docs/
                                            docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", filename)
                                        
                                            with open(docs_path, "w", encoding="utf-8") as f:
                                                f.write(report_content)
                                            
                                            reply_text = f"✅ *Reporte Generado Exitosamente*\n\nHe guardado el informe detallado en:\n`docs/{filename}`\n\nAquí tienes un resumen:\n\n" + report_content[:400] + "...\n\n_(Lee el archivo completo en tu carpeta docs)_"
                                        else:
                                            reply_text = "❌ Error al redactar el reporte con el modelo."
                                        
                                    except Exception as e:
                                        reply_text = f"❌ Error procesando el reporte: {e}"
                                else:
                                    reply_text = "❌ Error en la fase de investigación (Búsqueda)."

                        elif msg_logic.startswith("/recordatorio") or msg_logic.startswith("/remind"):
                            try:
                                parts = msg_logic.split(" ", 2)
                                if len(parts) < 3:
                                    reply_text = "⚠️ Uso: /recordatorio HH:MM Mensaje\nEj: `/recordatorio 08:00 Tomar antibiótico`"
                                else:
                                    time_str = parts[1]
                                    note = parts[2]
                                    # Validar formato de hora
                                    datetime.datetime.strptime(time_str, "%H:%M")
                                
                                    reminders = load_reminders()
                                    reminders.append({
                                        "chat_id": str(sender_id),
                                        "time": time_str,
                                        "message": note,
                                        "last_sent": ""
                                    })
                                    save_reminders(reminders)
                                    reply_text = f"✅ Recordatorio configurado.\nTe avisaré todos los días a las {time_str}: '{note}'."
                            except ValueError:
                                reply_text = "❌ Hora inválida. Usa formato 24h (HH:MM), ej: 14:30."

                        elif msg_logic.startswith("/borrar_recordatorios") or msg_logic.startswith("/clear_reminders"):
                            reminders = load_reminders()
                            # Filtrar, manteniendo solo los recordatorios de OTROS usuarios
                            reminders_to_keep = [r for r in reminders if r.get('chat_id') != str(sender_id)]
                            if len(reminders) == len(reminders_to_keep):
                                reply_text = "🤔 No tienes recordatorios configurados para borrar."
                            else:
                                save_reminders(reminders_to_keep)
                                reply_text = "✅ Todos tus recordatorios han sido eliminados."

                        elif msg_logic.startswith("/cita") or msg_logic.startswith("/appointment"):
                            try:
                                # Formato esperado: /cita DD/MM HH:MM Motivo
                                parts = msg_logic.split(" ", 3)
                                if len(parts) < 4:
                                    reply_text = "⚠️ Uso: /cita DD/MM HH:MM Motivo\nEj: `/cita 25/10 15:30 Revisión general`"
                                else:
                                    date_str = parts[1]
                                    time_str = parts[2]
                                    reason = parts[3]
                                    
                                    # Validación simple de formato de fecha/hora
                                    datetime.datetime.strptime(f"{date_str} {time_str}", "%d/%m %H:%M")
                                    
                                    # Guardar en un archivo JSON dedicado a citas
                                    existing_appts = []
                                    if os.path.exists(APPOINTMENTS_FILE):
                                        with open(APPOINTMENTS_FILE, 'r') as f:
                                            try: existing_appts = json.load(f)
                                            except: pass
                                    
                                    existing_appts.append({"chat_id": str(sender_id), "date": date_str, "time": time_str, "reason": reason, "created_at": str(datetime.datetime.now())})
                                    
                                    with open(APPOINTMENTS_FILE, 'w') as f:
                                        json.dump(existing_appts, f, indent=2)
                                        
                                    reply_text = f"✅ *Cita Agendada*\n\n📅 Fecha: {date_str}\n⏰ Hora: {time_str}\n📝 Motivo: {reason}\n\nHe registrado esta cita en el sistema."
                            except ValueError:
                                reply_text = "❌ Formato de fecha u hora inválido. Usa DD/MM HH:MM (ej: 25/10 14:00)."

                        elif msg_logic.startswith("/mis_citas") or msg_logic.startswith("/my_appointments"):
                            appts = load_appointments()
                            user_appts = [a for a in appts if a.get('chat_id') == str(sender_id)]
                            
                            if not user_appts:
                                reply_text = "🗓️ No tienes ninguna cita agendada."
                            else:
                                future_appts = []
                                now = datetime.datetime.now()
                                
                                for appt in user_appts:
                                    try:
                                        # Asume el año actual. Para una cita de enero hecha en diciembre, podría fallar.
                                        # Para este caso de uso, es una simplificación aceptable.
                                        appt_dt = datetime.datetime.strptime(f"{now.year}/{appt['date']} {appt['time']}", "%Y/%d/%m %H:%M")
                                        if appt_dt >= now:
                                            future_appts.append(appt)
                                    except ValueError:
                                        continue # Ignorar citas con formato de fecha/hora corrupto
                                
                                if not future_appts:
                                    reply_text = "🗓️ No tienes citas pendientes. (Todas tus citas agendadas ya pasaron)."
                                else:
                                    future_appts.sort(key=lambda x: datetime.datetime.strptime(f"{now.year}/{x['date']} {x['time']}", "%Y/%d/%m %H:%M"))
                                    reply_text = "🗓️ *Tus Próximas Citas:*\n\n"
                                    for appt in future_appts:
                                        reply_text += f"▫️ *{appt['date']}* a las *{appt['time']}* - {appt['reason']}\n"

                        elif msg_logic.startswith("/traducir") or msg_logic.startswith("/translate"):
                            content = msg_logic.split(" ", 1)[1].strip() if " " in msg_logic else ""
                            if not content:
                                reply_text = "⚠️ Uso: /traducir [texto | nombre_archivo]"
                            else:
                                # Verificar si es un archivo local (docs o .tmp)
                                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                docs_file = os.path.join(base_dir, "docs", content)
                                tmp_file = os.path.join(base_dir, ".tmp", content)
                            
                                target_file = None
                                if os.path.exists(docs_file): target_file = docs_file
                                elif os.path.exists(tmp_file): target_file = tmp_file
                            
                                if target_file:
                                    print(f"   📄 Traduciendo archivo: {content}")
                                    run_tool("telegram_tool.py", ["--action", "send", "--message", f"⏳ Traduciendo `{content}` al español...", "--chat-id", sender_id])
                                
                                    res = run_tool("translate_text.py", ["--file", target_file, "--lang", "Español"])
                                
                                    if res and res.get("status") == "success":
                                        out_path = res.get("file_path")
                                        run_tool("telegram_tool.py", ["--action", "send-document", "--file-path", out_path, "--chat-id", sender_id, "--caption", "📄 Traducción al Español"])
                                        reply_text = "✅ Archivo traducido enviado."
                                    else:
                                        err = res.get("message", "Error desconocido") if res else "Error en script"
                                        reply_text = f"❌ Error al traducir archivo: {err}"
                                else:
                                    # Traducir texto plano
                                    print(f"   🔤 Traduciendo texto...")
                                    prompt = f"Traduce el siguiente texto al Español. Devuelve solo la traducción:\n\n{content}"
                                    llm_res = run_tool("chat_with_llm.py", ["--prompt", prompt])
                                    if llm_res and "content" in llm_res:
                                        reply_text = f"🇪🇸 *Traducción:*\n\n{llm_res['content']}"
                                    else:
                                        reply_text = "❌ Error al traducir texto."

                        elif msg_logic.startswith("/idioma") or msg_logic.startswith("/lang"):
                            parts = msg_logic.split(" ")
                            if len(parts) < 2:
                                reply_text = "⚠️ Uso: /idioma [es/en]\nEj: `/idioma en` (para inglés)"
                            else:
                                lang_map = {"es": "es-ES", "en": "en-US", "fr": "fr-FR", "pt": "pt-BR"}
                                selection = parts[1].lower()
                                code = lang_map.get(selection, "es-ES")
                                config = load_config()
                                config["voice_lang"] = code
                                save_config(config)
                                reply_text = f"✅ Idioma de voz cambiado a: `{code}`.\nAhora te escucharé en ese idioma."

                        elif msg_logic.startswith("/ayuda_medica"):
                            manual_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "manual_medico.pdf")
                            if os.path.exists(manual_path):
                                print(f"   🏥 Enviando manual médico a {sender_id}...")
                                run_tool("telegram_tool.py", ["--action", "send", "--message", "📘 Aquí tienes la guía de uso para tu recuperación.", "--chat-id", sender_id])
                                run_tool("telegram_tool.py", ["--action", "send-document", "--file-path", manual_path, "--chat-id", sender_id, "--caption", "Manual de Asistente Médico (IA)"])
                            else:
                                reply_text = "⚠️ El manual PDF no ha sido generado aún. Pide al administrador que ejecute `pdflatex`."

                        elif msg_logic.startswith("/resumir_archivo") or msg_logic.startswith("/summarize_file"):
                            filename = msg_logic.split(" ", 1)[1].strip() if " " in msg_logic else ""
                            if not filename:
                                reply_text = "⚠️ Uso: /resumir_archivo [nombre_del_archivo_en_docs]"
                            else:
                                print(f"   📄 Resumiendo archivo local: {filename}")
                                run_tool("telegram_tool.py", ["--action", "send", "--message", f"⏳ Leyendo y resumiendo `{filename}`...", "--chat-id", sender_id])

                                # 1. Leer el archivo desde el Sandbox
                                path_in_container = f"/mnt/docs/{filename}"
                            
                                if filename.lower().endswith(".pdf"):
                                    # Código para extraer texto de PDF usando pypdf
                                    read_code = (
                                        f"from pypdf import PdfReader; "
                                        f"reader = PdfReader('{path_in_container}'); "
                                        f"print('\\n'.join([page.extract_text() for page in reader.pages]))"
                                    )
                                else:
                                    read_code = f"with open('{path_in_container}', 'r', encoding='utf-8') as f: print(f.read())"
                            
                                read_res = run_tool("run_sandbox.py", ["--code", read_code])

                                if read_res and read_res.get("status") == "success" and read_res.get("stdout"):
                                    content = read_res.get("stdout")
                                
                                    if len(content) > 10000:
                                        content = content[:10000] + "... (truncado)"
                                
                                    # 2. Enviar a LLM para resumir
                                    prompt = f"Resume el siguiente documento llamado '{filename}':\n\n{content}"
                                    llm_res = run_tool("chat_with_llm.py", ["--prompt", prompt])

                                    if llm_res and "content" in llm_res:
                                        reply_text = llm_res["content"]
                                    else:
                                        reply_text = "❌ Error generando el resumen."
                                else:
                                    error_details = read_res.get("stderr") or read_res.get("message", "No se pudo leer el archivo.")
                                    reply_text = f"❌ Error al leer el archivo `{filename}` desde el Sandbox:\n`{error_details}`"

                        elif msg_logic.startswith("/resumir") or msg_logic.startswith("/summarize"):
                            url = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
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
                                    # Ayuda contextual si el usuario intenta usar /resumir con un archivo local
                                    if "No scheme supplied" in str(err):
                                        filename = url.split('/')[-1]
                                        reply_text = f"🤔 El comando `/resumir` es para URLs (ej: `https://...`).\n\nSi querías resumir el archivo local `{filename}`, el comando correcto es:\n`/resumir_archivo {filename}`"
                                    else:
                                        reply_text = f"❌ Error leyendo la web: {err}"

                        elif msg_logic.startswith("/recordar") or msg_logic.startswith("/remember"):
                            memory_text = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
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

                        elif msg_logic.startswith("/memorias") or msg_logic.startswith("/memories"):
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

                        elif msg_logic.startswith("/olvidar") or msg_logic.startswith("/forget"):
                            mem_id = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
                            if not mem_id:
                                reply_text = "⚠️ Uso: /olvidar [ID]"
                            else:
                                print(f"   🗑️ Eliminando recuerdo: {mem_id}")
                                res = run_tool("delete_memory.py", ["--id", mem_id])
                                if res and res.get("status") == "success":
                                    reply_text = "✅ Recuerdo eliminado."
                                else:
                                    reply_text = f"❌ Error al eliminar: {res.get('message', 'Desconocido')}"

                        elif msg_logic.startswith("/broadcast") or msg_logic.startswith("/anuncio"):
                            announcement = msg_logic.split(" ", 1)[1] if " " in msg_logic else ""
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

                        elif msg_logic.startswith("/status"):
                            print("   📊 Verificando estado del sistema...")
                            run_tool("telegram_tool.py", ["--action", "send", "--message", "🔍 Escaneando sistema...", "--chat-id", sender_id])
                        
                            res = run_tool("monitor_resources.py", [])
                            # monitor_resources devuelve JSON incluso si hay alertas (exit code 1)
                            if res:
                                metrics = res.get("metrics", {})
                                alerts = res.get("alerts", [])
                            
                                status_emoji = "✅" if not alerts else "⚠️"
                                reply_text = (
                                    f"{status_emoji} *Estado del Servidor:*\n\n"
                                    f"💻 *CPU:* {metrics.get('cpu_percent', 0)}%\n"
                                    f"🧠 *RAM:* {metrics.get('memory_percent', 0)}% ({metrics.get('memory_used_gb', 0)}GB / {metrics.get('memory_total_gb', 0)}GB)\n"
                                    f"💾 *Disco:* {metrics.get('disk_percent', 0)}% (Libre: {metrics.get('disk_free_gb', 0)}GB)\n"
                                )
                                if alerts:
                                    reply_text += "\n🚨 *Alertas:*\n" + "\n".join([f"- {a}" for a in alerts])
                            else:
                                reply_text = "❌ Error al obtener métricas."

                        elif msg_logic.startswith("/usuarios") or msg_logic.startswith("/users"):
                            if os.path.exists(USERS_FILE):
                                with open(USERS_FILE, 'r') as f:
                                    users = [line.strip() for line in f if line.strip()]
                                last_users = users[-5:]
                                if last_users:
                                    reply_text = f"👥 *Últimos {len(last_users)} usuarios registrados:*\n" + "\n".join([f"- `{u}`" for u in last_users])
                                else:
                                    reply_text = "📭 No hay usuarios registrados."
                            else:
                                reply_text = "📭 No hay archivo de usuarios aún."

                        elif msg_logic.startswith("/modo"):
                            mode = msg_logic.split(" ", 1)[1].lower().strip() if " " in msg_logic else ""
                            if mode in PERSONAS:
                                set_persona(mode)
                                reply_text = f"🎭 *Modo cambiado a:* {mode.capitalize()}\n\n_{PERSONAS[mode]}_"
                            else:
                                opts = ", ".join([f"`{k}`" for k in PERSONAS.keys()])
                                reply_text = (
                                    "⚠️ Modo no reconocido.\n"
                                    f"Opciones disponibles: {opts}\n"
                                    "Uso: `/modo [opcion]`"
                                )

                        elif msg_logic.startswith("/reiniciar") or msg_logic.startswith("/reset"):
                            print("   🔄 Reiniciando sesión...")
                            # 1. Borrar historial de chat
                            run_tool("chat_with_llm.py", ["--prompt", "/clear"])
                        
                            # 2. Resetear personalidad
                            set_persona("default")
                        
                            reply_text = "🔄 *Sistema reiniciado.*\n\n- Historial de conversación borrado.\n- Personalidad restablecida a 'Default'."

                        elif msg_logic.startswith("/rol") or msg_logic.startswith("/role"):
                            parts = msg_logic.split(" ", 1)
                            if len(parts) < 2:
                                current_role = get_role(sender_id)
                                reply_text = f"👤 Tu rol actual es: *{current_role.upper()}*.\n\nPara cambiarlo, usa:\n`/rol medico`\n`/rol paciente`"
                            else:
                                new_role = parts[1].lower().strip()
                                if new_role in ["medico", "médico", "doctor"]:
                                    set_role(sender_id, "medico")
                                    reply_text = "👨‍⚕️ *Rol actualizado a MÉDICO.*\nAhora tienes acceso a herramientas de monitoreo y gestión clínica."
                                elif new_role in ["paciente", "usuario"]:
                                    set_role(sender_id, "paciente")
                                    reply_text = "👤 *Rol actualizado a PACIENTE.*\nEl bot se enfocará en tu recuperación y seguimiento personal."
                                else:
                                    reply_text = "⚠️ Rol no reconocido. Usa `medico` o `paciente`."

                        elif msg_logic.startswith("/foto") or msg_logic.startswith("/camara") or msg_logic.startswith("/photo"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ *Acceso Denegado:* Solo personal médico puede acceder a la cámara de vigilancia."
                            else:
                                cam_ip = os.getenv("ESP32_CAM_IP")
                                if not cam_ip:
                                    reply_text = "⚠️ Error de Configuración: La variable `ESP32_CAM_IP` no está definida en el archivo `.env`."
                                else:
                                    print(f"   📸 Solicitando foto a {cam_ip}...")
                                    run_tool("telegram_tool.py", ["--action", "send", "--message", "📸 Conectando con la cámara de aislamiento...", "--chat-id", sender_id])
                                    
                                    filename = f"cam_{int(time.time())}.jpg"
                                    local_path = os.path.join(".tmp", filename)
                                    
                                    # Ejecutar script de captura
                                    res = run_tool("capture_image.py", ["--ip", cam_ip, "--output-file", local_path])
                                    
                                    if res and res.get("status") == "success":
                                        # Enviar foto
                                        run_tool("telegram_tool.py", ["--action", "send-photo", "--file-path", local_path, "--chat-id", sender_id, "--caption", "Vista en tiempo real del paciente."])
                                        reply_text = "✅ Captura completada."
                                    else:
                                        err = res.get("message", "Error desconocido") if res else "No se pudo conectar con la cámara."
                                        reply_text = f"❌ Error al capturar imagen: {err}\n\nVerifique que la ESP32-CAM esté encendida y conectada al WiFi."

                        elif msg_logic.startswith("/monitorear") or msg_logic.startswith("/monitor"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ *Acceso Denegado:* Este comando es exclusivo para personal médico."
                            else:
                                patients = load_patients()
                                parts = msg_logic.split(" ", 1)
                                
                                if len(parts) < 2:
                                    # Mostrar resumen de todos
                                    if not patients:
                                        reply_text = "🏥 No hay pacientes registrados en el sistema."
                                    else:
                                        reply_text = "📡 *Pacientes Activos:*\n\n"
                                        for pid, p in patients.items():
                                            status = "🟢 Estable"
                                            if p['heart_rate'] > 100 or p['spo2'] < 94: status = "🔴 Alerta"
                                            reply_text += f"👤 *{p.get('name')}* (`{pid}`)\n   Estado: {status} | HR: {p['heart_rate']} | SpO2: {p['spo2']}%\n\n"
                                        reply_text += "Usa `/monitorear [ID]` para ver detalles."
                                else:
                                    # Mostrar detalle de uno
                                    pid = parts[1].strip()
                                    if pid in patients:
                                        vitals = patients[pid]
                                        reply_text = (
                                            f"📡 *Telemetría: {vitals.get('name')} ({pid})*\n\n"
                                            f"💓 *Ritmo Cardíaco:* {vitals.get('heart_rate')} bpm\n"
                                            f"🌡️ *Temperatura:* {vitals.get('temperature')}°C\n"
                                            f"🫁 *SpO2:* {vitals.get('spo2')}%\n"
                                            f"📉 *Presión:* {vitals.get('systolic')}/{vitals.get('diastolic')} mmHg\n"
                                            f"_Última actualización: Hace {int(time.time() - vitals.get('last_update', 0))}s_"
                                        )
                                    else:
                                        reply_text = f"❌ Paciente `{pid}` no encontrado."

                        elif msg_logic.startswith("/simular_crisis"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Solo médicos pueden ejecutar simulaciones."
                            else:
                                patients = load_patients()
                                parts = msg_logic.split(" ", 1)
                                pid = parts[1].strip() if len(parts) > 1 else "SIM-001"
                                
                                if pid in patients:
                                    patients[pid]["heart_rate"] = 145
                                    patients[pid]["spo2"] = 88
                                    patients[pid]["temperature"] = 39.2
                                    patients[pid]["last_alert"] = 0
                                    save_patients(patients)
                                    reply_text = f"⚠️ *Simulación Iniciada para {patients[pid]['name']}*: Signos vitales alterados."
                                else:
                                    reply_text = f"❌ Paciente `{pid}` no encontrado. Usa `/monitorear` para ver IDs."

                        elif msg_logic.startswith("/estabilizar") or msg_logic.startswith("/stabilize"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Solo médicos pueden realizar procedimientos de estabilización."
                            else:
                                patients = load_patients()
                                parts = msg_logic.split(" ", 1)
                                pid = parts[1].strip() if len(parts) > 1 else "SIM-001"
                                
                                if pid in patients:
                                    patients[pid]["heart_rate"] = 75
                                    patients[pid]["temperature"] = 36.5
                                    patients[pid]["spo2"] = 98
                                    patients[pid]["systolic"] = 120
                                    patients[pid]["diastolic"] = 80
                                    save_patients(patients)
                                    reply_text = f"✅ *{patients[pid]['name']} Estabilizado/a*."
                                else:
                                    reply_text = f"❌ Paciente `{pid}` no encontrado."

                        elif msg_logic.startswith("/paciente_reset") or msg_logic.startswith("/reset_patient"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Solo médicos pueden resetear los valores del paciente."
                            else:
                                patients = load_patients()
                                parts = msg_logic.split(" ", 1)
                                pid = parts[1].strip() if len(parts) > 1 else "SIM-001"
                                
                                if pid in patients:
                                    patients[pid]["heart_rate"] = 75
                                    patients[pid]["temperature"] = 36.5
                                    patients[pid]["spo2"] = 98
                                    patients[pid]["last_alert"] = 0
                                    save_patients(patients)
                                    reply_text = f"🔄 *Valores de {patients[pid]['name']} Reseteados*."
                                else:
                                    reply_text = f"❌ Paciente `{pid}` no encontrado."

                        elif msg_logic.startswith("/historial_alertas") or msg_logic.startswith("/alert_history"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Acceso denegado."
                            else:
                                if os.path.exists(ALERTS_LOG_FILE):
                                    with open(ALERTS_LOG_FILE, 'r') as f:
                                        lines = f.readlines()
                                    # Mostrar las últimas 10 alertas
                                    last_alerts = lines[-10:]
                                    if last_alerts:
                                        reply_text = "📋 *Historial de Alertas Recientes:*\n\n" + "".join(last_alerts)
                                    else:
                                        reply_text = "📋 El historial de alertas está vacío."
                                else:
                                    reply_text = "📋 No hay alertas registradas aún."

                        elif msg_logic.startswith("/nuevo_paciente") or msg_logic.startswith("/ingresar"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Solo médicos pueden registrar pacientes."
                            else:
                                patients = load_patients()
                                args = msg_logic.split(" ", 1)
                                
                                if len(args) < 2:
                                    reply_text = "⚠️ Uso: `/nuevo_paciente [Nombre]` (ID automático) o `/nuevo_paciente [ID] [Nombre]`"
                                else:
                                    content = args[1].strip()
                                    
                                    # Detectar si el primer término es un ID manual (ej: SIM-005)
                                    first_word = content.split(" ")[0]
                                    if first_word.upper().startswith("SIM-") and " " in content:
                                        new_id = first_word.upper()
                                        new_name = content.split(" ", 1)[1].strip()
                                    else:
                                        # Generar ID automático (SIM-XXX)
                                        max_n = 0
                                        for pid in patients:
                                            if pid.startswith("SIM-"):
                                                try:
                                                    n = int(pid.split("-")[1])
                                                    if n > max_n: max_n = n
                                                except: pass
                                        new_id = f"SIM-{max_n + 1:03d}"
                                        new_name = content

                                    if new_id in patients:
                                        reply_text = f"⚠️ El paciente con ID `{new_id}` ya existe."
                                    else:
                                        # Crear paciente con valores vitales por defecto (estables)
                                        patients[new_id] = { "name": new_name, "heart_rate": 75, "temperature": 36.5, "spo2": 98, "systolic": 120, "diastolic": 80, "last_update": time.time(), "last_alert": 0 }
                                        save_patients(patients)
                                        reply_text = f"✅ *Paciente Registrado*\n\n👤 Nombre: {new_name}\n🆔 ID: `{new_id}`\n\nYa está activo en el sistema de monitoreo."

                        elif msg_logic.startswith("/pacientes"):
                            if get_role(sender_id) != "medico":
                                reply_text = "⛔ Acceso denegado."
                            else:
                                patients = load_patients()
                                if not patients:
                                    reply_text = "🏥 No hay pacientes registrados."
                                else:
                                    reply_text = "🏥 *Lista de Pacientes:*\n\n"
                                    for pid, p in patients.items():
                                        reply_text += f"👤 *{p.get('name')}* (ID: `{pid}`)\n"
                                    reply_text += "\nUsa `/monitorear [ID]` para ver sus signos vitales."

                        elif msg_logic.startswith("/ayuda") or msg_logic.startswith("/help"):
                            role = get_role(sender_id)
                            
                            if role == "medico":
                                reply_text = (
                                    "👨‍⚕️ *Panel de Control Médico:*\n\n"
                                    "📡 `/monitorear`: Ver signos vitales de pacientes (Sensores).\n"
                                    "📸 `/foto`: Ver cámara en tiempo real.\n"
                                    "➕ `/nuevo_paciente`: Registrar nuevo ingreso.\n"
                                    "🔬 `/reporte [tema]`: Generar informe clínico detallado.\n"
                                    "🔍 `/investigar [tema]`: Búsqueda médica avanzada.\n"
                                    "📋 `/historial_alertas`: Ver registro de crisis pasadas.\n"
                                    "🏥 `/pacientes`: Lista de pacientes activos.\n"
                                    "📄 `/resumir_archivo [pdf]`: Analizar historia clínica.\n"
                                    "⚙️ `/status`: Estado del servidor.\n"
                                    "⚠️ `/simular_crisis`: Test de alertas.\n"
                                    "💉 `/estabilizar`: Normalizar signos vitales.\n"
                                    "👤 `/rol paciente`: Cambiar a vista de paciente.\n"
                                )
                            else:
                                reply_text = (
                                    "🤖 *Asistente de Paciente:*\n\n"
                                    "📅 `/cita [fecha]`: Agendar nueva cita.\n"
                                    "🗓️ `/mis_citas`: Ver mis citas pendientes.\n"
                                    "⏰ `/recordatorio`: Configurar alarma de medicamentos.\n"
                                    "📘 `/ayuda_medica`: Ver manual de recuperación.\n"
                                    "🗣️ *Notas de voz*: Puedes hablarme para consultas.\n"
                                    "👨‍⚕️ `/rol medico`: (Solo personal autorizado).\n"
                                )
                    
                        elif msg_logic.startswith("/py "):
                            code_to_run = msg_logic.split(" ", 1)[1].strip()
                            print(f"   🐍 Ejecutando en Sandbox: {code_to_run}")

                            res = run_tool("run_sandbox.py", ["--code", code_to_run])

                            reply_text = "" # Resetear
                            if res and res.get("status") == "success":
                                stdout = res.get("stdout", "")
                                stderr = res.get("stderr", "")
                            
                                # --- Manejo de Salida de Archivos ---
                                sent_file = False
                                clean_stdout_lines = []
                                if stdout:
                                    for line in stdout.splitlines():
                                        potential_path_in_container = line.strip()
                                        if potential_path_in_container.startswith('/mnt/out/'):
                                            filename = os.path.basename(potential_path_in_container)
                                            local_path = os.path.join(".tmp", filename)
                                            if os.path.exists(local_path):
                                                print(f"   🖼️  Detectado archivo de salida: {local_path}. Enviando...")
                                                run_tool("telegram_tool.py", ["--action", "send-photo", "--file-path", local_path, "--chat-id", sender_id, "--caption", "Archivo generado por el Sandbox."])
                                                sent_file = True
                                                continue # No añadir esta línea a la respuesta de texto
                                        clean_stdout_lines.append(line)
                            
                                clean_stdout = "\n".join(clean_stdout_lines)

                                # --- Manejo de Salida de Texto ---
                                text_output_exists = clean_stdout or stderr
                                if text_output_exists:
                                    reply_text = "📦 *Resultado del Sandbox:*\n\n"
                                    if clean_stdout:
                                        reply_text += f"*Salida:*\n```\n{clean_stdout}\n```\n"
                                    if stderr:
                                        reply_text += f"*Errores:*\n```\n{stderr}\n```\n"
                                elif not sent_file: # No hay salida de texto Y no se envió archivo
                                    reply_text = "📦 *Resultado del Sandbox:*\n\n_El código se ejecutó sin producir salida._"
                            else:
                                reply_text = f"❌ *Error en Sandbox:*\n{res.get('message', 'Error desconocido.')}"

                        elif msg_logic.lower().strip() in ["hola", "hola!", "hi", "hello", "/start"]:
                            role = get_role(sender_id)
                            if role == "medico":
                                reply_text = "👨‍⚕️ *Bienvenido, Doctor.*\n\nEl sistema de telemetría y asistencia clínica está activo. Use `/monitorear` para ver el estado de los pacientes o `/ayuda` para ver las herramientas profesionales."
                            else:
                                reply_text = """👋 ¡Hola! Soy tu Asistente de Telemedicina.

    Estoy aquí para ayudarte a gestionar tu salud y responder tus consultas.

    Puedes interactuar conmigo de varias formas:
    - Envíame un informe en PDF para que lo analice.
    - Pídeme un reporte sobre una condición médica con `/reporte [tema]`.
    - Usa `/ayuda` para ver todos los comandos disponibles."""

                        elif msg_logic.lower().strip() in ["gracias", "gracias!", "thanks", "thank you"]:
                            reply_text = "¡De nada! Estoy aquí para ayudar. 🤖"

                        # --- CHAT GENERAL (Capa 2: Orquestación) ---
                        elif not reply_text: # Solo si no se ha generado respuesta por un comando anterior
                            # Estrategia Directa con RAG:
                            # Enviamos el mensaje al LLM. El script chat_with_llm.py se encarga de
                            # buscar en la memoria e inyectar el contexto si es relevante.
                            print("   🤔 Consultando al Agente (con memoria)...")
                            current_sys = get_current_persona()
                        
                            # Inyectar fecha y hora actual para que el LLM lo sepa
                            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            current_sys += f"\n[Contexto Temporal: Fecha y Hora actual del servidor: {now_str}]"

                            # Si la interacción fue por voz, instruir al LLM que responda en ese idioma
                            if is_voice_interaction and voice_lang_short != "es":
                                current_sys += f"\nIMPORTANT: The user is speaking in '{voice_lang_short}'. You MUST respond in '{voice_lang_short}', regardless of your default instructions."

                            llm_response = run_tool("chat_with_llm.py", ["--prompt", msg_logic, "--system", current_sys])
                        
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
                        
                            # 4. Si fue interacción por voz, enviar también audio
                            if is_voice_interaction and reply_text:
                                print("   🗣️ Generando respuesta de voz...")
                                audio_path = os.path.join(".tmp", f"reply_{int(time.time())}.ogg")
                                # Generar audio
                                tts_res = run_tool("text_to_speech.py", ["--text", reply_text[:500], "--output", audio_path, "--lang", voice_lang_short]) # Limitamos a 500 chars para no hacerlo eterno
                                if tts_res and tts_res.get("status") == "success":
                                    run_tool("telegram_tool.py", ["--action", "send-voice", "--file-path", audio_path, "--chat-id", sender_id])
                    
                    except Exception as e:
                        print(f"❌❌❌ ERROR CRÍTICO PROCESANDO MENSAJE: {msg} ❌❌❌")
                        print(f"   Error: {e}")
                        traceback.print_exc()
                        try:
                            # Intentar notificar al usuario del error
                            error_reply = "🤖 ¡Ups! Ocurrió un error inesperado al procesar tu último mensaje. El administrador ha sido notificado."
                            run_tool("telegram_tool.py", ["--action", "send", "--message", error_reply, "--chat-id", sender_id])
                        except:
                            pass # Si incluso el envío de error falla, no hacer nada para no entrar en un bucle de errores.
            
            # --- TAREA DE FONDO: RECORDATORIOS ---
            check_reminders()
            check_appointments()
            simulate_and_monitor_vitals()

            # --- TAREA DE FONDO: MONITOREO PROACTIVO ---
            if time.time() - last_health_check > HEALTH_CHECK_INTERVAL:
                last_health_check = time.time()
                # Solo el admin (CHAT_ID del .env) recibe alertas técnicas
                admin_id = os.getenv("TELEGRAM_CHAT_ID")
                if admin_id:
                    res = run_tool("monitor_resources.py", [])
                    if res and res.get("alerts"):
                        alerts = res.get("alerts", [])
                        alert_msg = "🚨 *ALERTA DEL SISTEMA:*\n\n" + "\n".join([f"- {a}" for a in alerts])
                        print(f"   ⚠️ Detectada alerta de sistema. Notificando a {admin_id}...")
                        run_tool("telegram_tool.py", ["--action", "send", "--message", alert_msg, "--chat-id", admin_id])
            
            # Esperar un poco antes del siguiente chequeo para no saturar la CPU/API
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 Desconectando servicio de Telegram.")

if __name__ == "__main__":
    main()