import os
import re
import httpx

UPLOAD_URL = "https://greenbase.arielcapdevila.com/upload"
BASE_DIR = "separated_tracks/mdx_extra_q"
HTML_FILE = "index.html"

def upload_file(filepath):
    print(f"Subiendo {filepath}...")
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'application/octet-stream')}
            response = httpx.post(UPLOAD_URL, files=files, timeout=600.0)
            response.raise_for_status()
            return response.json()['id']
    except Exception as e:
        print(f"Error al subir {filepath}: {e}")
        return None

def main():
    if not os.path.exists(HTML_FILE):
        print("No se encontró index.html")
        return
        
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    yt_ids = re.findall(r'ytId:\s*"([^"]+)"', html_content)
    
    print(f"Encontradas {len(set(yt_ids))} canciones en el catálogo.")
    
    for ytId in set(yt_ids):
        vocals_path = os.path.join(BASE_DIR, ytId, "vocals.wav")
        inst_path = os.path.join(BASE_DIR, ytId, "no_vocals.wav")
        
        if os.path.exists(vocals_path) and os.path.exists(inst_path):
            print(f"\nProcesando {ytId}...")
            
            # Verificar si ya está modificado
            if f'ytId: "{ytId}", vocalsId' in html_content:
                 print(f"  Ya está subido {ytId}. Saltando...")
                 continue
                 
            vocals_id = upload_file(vocals_path)
            inst_id = upload_file(inst_path)
            
            if vocals_id and inst_id:
                old_str = f'ytId: "{ytId}"'
                new_str = f'ytId: "{ytId}", vocalsId: "{vocals_id}", instId: "{inst_id}"'
                
                html_content = html_content.replace(old_str, new_str)
                
                print(f"  => OK! vocals: {vocals_id}, inst: {inst_id}")
                
                with open(HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html_content)
            else:
                print(f"  => Falla al subir archivos de {ytId}")
        else:
            print(f"\nNo se encontraron los audios para {ytId} (saltando)")

if __name__ == "__main__":
    main()
