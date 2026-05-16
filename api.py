# Requiere: pip install fastapi uvicorn httpx demucs soundfile
# Y configurar PyTorch para CUDA: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import subprocess
import uuid
import traceback
import hashlib
import re

app = FastAPI(title="Neon SingStar API con Demucs (Verbose)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

YTMP_API_BASE = "https://ytmp.arielcapdevila.com"

TRACKS_DIR = "separated_tracks"
os.makedirs(TRACKS_DIR, exist_ok=True)
app.mount("/tracks", StaticFiles(directory=TRACKS_DIR), name="tracks")

# WebRTC Signaling Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            target_id = data.get("target")
            if target_id:
                await manager.send_message(data, target_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)

@app.get("/api/search")
async def search_youtube(query: str = Query(...), limit: int = Query(6)):
    print(f"🔍 [BÚSQUEDA] Buscando en YouTube: '{query}' (Límite: {limit})")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{YTMP_API_BASE}/api/search", params={"query": query, "limit": limit})
            r.raise_for_status()
            print(f"✅ [BÚSQUEDA] Resultados obtenidos para '{query}'")
            return r.json()
        except httpx.HTTPError as e:
            print(f"❌ [BÚSQUEDA] Error en API: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream")
async def stream_media(url: str = Query(...), type: str = Query("video")):
    print(f"▶️ [STREAM] Solicitando enlace directo para: {url}")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{YTMP_API_BASE}/api/stream", params={"url": url, "type": type})
            r.raise_for_status()
            print(f"✅ [STREAM] Enlace de video obtenido")
            return r.json()
        except httpx.HTTPError as e:
            print(f"❌ [STREAM] Error en API: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/process_karaoke")
async def process_karaoke(url: str = Query(...)):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    job_id = match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]
    
    raw_mp3_path = os.path.join(TRACKS_DIR, f"{job_id}.mp3")

    # Mapeo de rutas de caché
    output_vocals = f"/tracks/mdx_extra_q/{job_id}/vocals.wav"
    output_inst = f"/tracks/mdx_extra_q/{job_id}/no_vocals.wav"
    local_vocals_path = os.path.join(TRACKS_DIR, "mdx_extra_q", f"{job_id}", "vocals.wav")
    local_inst_path = os.path.join(TRACKS_DIR, "mdx_extra_q", f"{job_id}", "no_vocals.wav")

    if os.path.exists(local_vocals_path) and os.path.exists(local_inst_path):
        print(f"⚡ [CACHE HIT] La canción {job_id} ya está separada. Retornando caché al instante.")
        return {
            "vocals": output_vocals,
            "inst": output_inst
        }

    print(f"\n" + "="*50)
    print(f"🎵 [KARAOKE INIT] Nueva solicitud de separación")
    print(f"🔗 [URL] {url}")
    print(f"🆔 [JOB ID] {job_id}")
    print("="*50)

    # Aumentado a 300 segundos por si la canción es muy larga
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            print(f"⏳ [PASO 1] Pidiendo enlace de descarga a ytmp.arielcapdevila.com...")
            dl_res = await client.get(f"{YTMP_API_BASE}/api/download", params={"url": url, "format": "mp3"})
            dl_res.raise_for_status()
            
            content_type = dl_res.headers.get("content-type", "")
            
            if "application/json" in content_type:
                dl_data = dl_res.json()
                mp3_url = dl_data.get("url") or dl_data.get("file")
                print(f"✅ [PASO 1] URL final del MP3 obtenida. Iniciando descarga...")
                
                with open(raw_mp3_path, "wb") as f:
                    async with client.stream("GET", mp3_url) as r:
                        # Descarga por bloques para no saturar la RAM
                        async for chunk in r.aiter_bytes():
                            f.write(chunk)
            else:
                print(f"⚠️ [PASO 1] El servidor devolvió el audio directamente. Guardando...")
                with open(raw_mp3_path, "wb") as f:
                    f.write(dl_res.content)
            
            print(f"✅ [PASO 2] Archivo guardado localmente en: {raw_mp3_path}")
            print(f"🚀 [PASO 3] Iniciando IA (Demucs). Modelo: mdx_extra_q | Hardware: CUDA")
            print(f"👇 --- SALIDA EN TIEMPO REAL DE DEMUCS --- 👇\n")

            try:
                # El argumento "--two-stems vocals" es LA CLAVE.
                # Obliga a Demucs a mezclar bass, drums y other en un archivo llamado "no_vocals.wav"
                process = subprocess.run(
                    ["demucs", "-n", "mdx_extra_q", "-d", "cuda", "--two-stems", "vocals", "-o", TRACKS_DIR, raw_mp3_path]
                )
            except FileNotFoundError:
                print("\n❌ [ERROR CRÍTICO] Comando 'demucs' no encontrado en el PATH.")
                print("⚠️ Retornando audio original como fallback.")
                return {"vocals": f"/tracks/raw_{job_id}.mp3", "inst": f"/tracks/raw_{job_id}.mp3"}

            print(f"\n👆 --- FIN DE DEMUCS --- 👆")

            if process.returncode != 0:
                print(f"❌ [PASO 3 FALLIDO] Demucs devolvió el código de error: {process.returncode}")
                print("⚠️ Retornando audio original como fallback.")
                return {"vocals": f"/tracks/raw_{job_id}.mp3", "inst": f"/tracks/raw_{job_id}.mp3"}

            base_name = os.path.splitext(os.path.basename(raw_mp3_path))[0]
            print(f"✅ [PASO 4] Separación exitosa. Mapeando rutas...")
            
            # Ahora, gracias a --two-stems vocals, garantizamos que existan estos dos archivos exactos
            output_vocals = f"/tracks/mdx_extra_q/{base_name}/vocals.wav"
            output_inst = f"/tracks/mdx_extra_q/{base_name}/no_vocals.wav"
            
            print(f"🎤 [VOCES] {output_vocals}")
            print(f"🎸 [PISTA] {output_inst}")
            print(f"🎉 [FIN] Proceso completado. Enviando rutas al navegador.")
            print("="*50 + "\n")

            return {
                "vocals": output_vocals,
                "inst": output_inst
            }

        except Exception as e:
            print(f"\n💥 [EXCEPCIÓN NO CONTROLADA]")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def home():
    print(f"🌐 [FRONTEND] Sirviendo index.html al usuario")
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    print(f"❌ [FRONTEND] No se encontró el archivo index.html")
    return HTMLResponse("<h1>Frontend no encontrado</h1>")

@app.get("/mic", response_class=HTMLResponse)
async def mic():
    if os.path.exists("mic.html"):
        with open("mic.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>mic.html no encontrado</h1>")

if __name__ == "__main__":
    import uvicorn
    print("🌟 [SERVER] Arrancando servidor Neon SingStar en modo Verbose...")
    uvicorn.run(app, host="0.0.0.0", port=8000)