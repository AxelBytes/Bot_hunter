import subprocess
import json
import os
import requests

# Estos se configuran en GitHub "Secrets"
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def actualizar_lista_objetivos():
    """Descarga los targets de HackerOne y los limpia."""
    print("📡 Descargando targets actualizados de HackerOne...")
    url_json = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/hackerone_data.json"
    try:
        response = requests.get(url_json)
        data = response.json()
        targets_limpios = []
        
        for programa in data:
            # Quitamos el filtro de 'offers_bounties' temporalmente para testear
            targets = programa.get('targets', {}).get('in_scope', [])
            for asset in targets:
                # Aceptamos cualquier cosa que parezca un dominio
                identifier = asset.get('asset_identifier', '')
                if identifier and (asset.get('type') == 'url' or '.' in identifier):
                    clean_url = identifier.replace("*.", "").replace("https://", "").replace("http://", "").strip("/")
                    # Evitamos cosas raras como emails o archivos
                    if "/" not in clean_url and "@" not in clean_url:
                        targets_limpios.append(clean_url)
        
        lista_final = list(set(targets_limpios))
        with open("targets.txt", "w") as f:
            for t in lista_final:
                f.write(f"{t}\n")
        
        print(f"✅ {len(lista_final)} objetivos listos para auditar.")
    except Exception as e:
        print(f"❌ Error al descargar lista: {e}")

def enviar_telegram(mensaje):
    """Envía la alerta formateada a tu celular."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def ejecutar_nuclei():
    """Lanza el motor de escaneo."""
    print("🚀 Iniciando escaneo de vulnerabilidades (Severidad: CRITICAL, HIGH)...")
    
    # -silent: no ensucia el log / -jsonl: salida procesable / -ni: interfaz no interactiva
    comando = ["nuclei", "-list", "targets.txt", "-silent", "-jsonl", "-severity", "critical,high"]
    
    try:
        # Ejecutamos y leemos la salida línea por línea en tiempo real
        process = subprocess.Popen(comando, stdout=subprocess.PIPE, text=True)
        
        for line in process.stdout:
            if line.strip():
                data = json.loads(line)
                info = data.get('info', {})
                vulnerabilidad = info.get('name', 'N/A')
                severidad = info.get('severity', 'unknown').upper()
                target = data.get('matched-at', 'N/A')
                
                # Emoji según severidad
                emoji = "🔴" if severidad == "CRITICAL" else "🟠"
                
                mensaje = (
                    f"{emoji} *HALLAZGO DETECTADO*\n\n"
                    f"*Target:* `{target}`\n"
                    f"*Fallo:* {vulnerabilidad}\n"
                    f"*Severidad:* {severidad}\n\n"
                    f"🔗 [Verificar en HackerOne](https://hackerone.com/programs)"
                )
                
                print(f"🔥 {severidad}: {vulnerabilidad} en {target}")
                enviar_telegram(mensaje)
                
    except Exception as e:
        print(f"❌ Error en el motor Nuclei: {e}")

if __name__ == "__main__":
    if not TOKEN or not CHAT_ID:
        print("❌ Faltan las variables TELEGRAM_TOKEN o CHAT_ID en Secrets.")
    else:
        actualizar_lista_objetivos()
        ejecutar_nuclei()
