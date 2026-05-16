import asyncio
import hashlib
import os
import re
import subprocess

catalog = [
    {"title": "Dua Lipa - Don't Start Now", "url": "https://www.youtube.com/watch?v=oygrmJFKYZY"},
    {"title": "The Weeknd - Blinding Lights", "url": "https://www.youtube.com/watch?v=4NRXx6U8ABQ"},
    {"title": "Bizarrap & Quevedo - Bzrp Music Sessions, Vol. 52", "url": "https://www.youtube.com/watch?v=A_g3lMcWVy0"},
    {"title": "Rosalía - DESPECHÁ", "url": "https://www.youtube.com/watch?v=5g2hT4GmAGU"},
    {"title": "Shakira - Hips Don't Lie", "url": "https://www.youtube.com/watch?v=DUT5rEU6pqM"},
    {"title": "Queen - Don't Stop Me Now", "url": "https://www.youtube.com/watch?v=HgzGwKwLmgM"},
    {"title": "Luis Fonsi - Despacito", "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk"},
    {"title": "Rihanna - Don't Stop The Music", "url": "https://www.youtube.com/watch?v=yd8jh9QYfEs"},
    {"title": "Bad Bunny - Tití Me Preguntó", "url": "https://www.youtube.com/watch?v=Cr8K88UcO0s"},
    {"title": "Britney Spears - Toxic", "url": "https://www.youtube.com/watch?v=LOZuxwVk7TU"},
    {"title": "Avicii - Wake Me Up", "url": "https://www.youtube.com/watch?v=IcrbM1l_BoI"},
    {"title": "Daddy Yankee - Gasolina", "url": "https://www.youtube.com/watch?v=CCF1_jI8Prk"},
    {"title": "Michael Jackson - Billie Jean", "url": "https://www.youtube.com/watch?v=Zi_XLOBDo_Y"},
    {"title": "ABBA - Dancing Queen", "url": "https://www.youtube.com/watch?v=xFrGuyw1V8s"},
    {"title": "Lady Gaga - Bad Romance", "url": "https://www.youtube.com/watch?v=qrO4YZeyl0I"},
    {"title": "Bruno Mars - Uptown Funk", "url": "https://www.youtube.com/watch?v=OPf0YbXqDm0"},
    {"title": "Daft Punk - Get Lucky", "url": "https://www.youtube.com/watch?v=5NV6Rdv1a3I"},
    {"title": "Whitney Houston - I Wanna Dance With Somebody", "url": "https://www.youtube.com/watch?v=eH3giaIzONA"},
    {"title": "Earth, Wind & Fire - September", "url": "https://www.youtube.com/watch?v=Gs069dndIYk"},
    {"title": "David Guetta ft. Sia - Titanium", "url": "https://www.youtube.com/watch?v=JRfuAukYTKg"}
]

def predownload_catalog():
    print(f"🚀 Iniciando pre-descarga de {len(catalog)} canciones (Modo 100% Local y Directo)...")
    print("⏳ Este proceso puede tardar HORAS dependiendo de tu tarjeta gráfica y Demucs.")
    print("="*50)
    
    os.makedirs("separated_tracks", exist_ok=True)
    
    for index, song in enumerate(catalog):
        print(f"\n[{index+1}/{len(catalog)}] Procesando: {song['title']}")
        print(f"🔗 URL: {song['url']}")
        
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', song["url"])
        job_id = match.group(1) if match else hashlib.md5(song["url"].encode()).hexdigest()[:12]
        
        vocals_path = os.path.join("separated_tracks", "mdx_extra_q", job_id, "vocals.wav")
        inst_path = os.path.join("separated_tracks", "mdx_extra_q", job_id, "no_vocals.wav")
        
        if os.path.exists(vocals_path) and os.path.exists(inst_path):
            print("⏭️  [SALTADO] La canción ya fue descargada y separada previamente.")
            continue

        raw_mp3 = os.path.join("separated_tracks", f"{job_id}.mp3")
        
        if not os.path.exists(raw_mp3):
            print("⬇️  Descargando audio con yt-dlp...")
            try:
                subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", raw_mp3, song["url"]], check=True)
            except Exception as e:
                print(f"❌ Error al descargar con yt-dlp: {e}")
                continue
                
        print("🤖 Procesando con Demucs...")
        try:
            subprocess.run(["demucs", "-n", "mdx_extra_q", "-d", "cuda", "--two-stems", "vocals", "-o", "separated_tracks", raw_mp3], check=True)
            print(f"✅ ¡Separación exitosa para {song['title']}!")
        except Exception as e:
            print(f"❌ Error al procesar con Demucs: {e}")

if __name__ == "__main__":
    predownload_catalog()
