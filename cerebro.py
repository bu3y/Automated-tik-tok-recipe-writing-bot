import os
import base64
import subprocess
import yt_dlp
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==========================================
# CONFIGURACIÓN
# ==========================================
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_URL     = os.environ.get("RENDER_URL")  # ← nueva variable
RUTA_CARPETA   = "/tmp"
FFMPEG         = "ffmpeg"

client_groq = Groq(api_key=GROQ_API_KEY)

# ==========================================
# FUNCIONES DE PROCESAMIENTO
# ==========================================

def extraer_audio(url, prefijo):
    ruta_mp3 = os.path.join(RUTA_CARPETA, f"audio_{prefijo}.mp3")
    opciones = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(RUTA_CARPETA, f'audio_{prefijo}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        ydl.download([url])
    return ruta_mp3

def descargar_video(url, prefijo):
    ruta_video = os.path.join(RUTA_CARPETA, f"video_{prefijo}.mp4")
    opciones = {
        'format': 'best',
        'outtmpl': os.path.join(RUTA_CARPETA, f'video_{prefijo}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        ydl.download([url])
    return ruta_video

def transcribir_audio(ruta_audio):
    with open(ruta_audio, "rb") as file:
        transcription = client_groq.audio.transcriptions.create(
            file=(ruta_audio, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription.strip()

def extraer_frames(ruta_video, prefijo, n_frames=6):
    frames = []
    for i in range(n_frames):
        ruta_frame = os.path.join(RUTA_CARPETA, f"frame_{prefijo}_{i}.jpg")
        subprocess.run(
            [FFMPEG, "-i", ruta_video, "-ss", str(i * 2), "-vframes", "1", ruta_frame, "-y"],
            capture_output=True
        )
        if os.path.exists(ruta_frame):
            frames.append(ruta_frame)
    return frames

def imagen_a_base64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def leer_receta_visual(frames):
    contenido = [{
        "type": "text",
        "text": (
            "Estas imágenes son frames de un TikTok de receta de cocina. "
            "El video no tiene narración. Extrae la receta y estructura así:\n\n"
            "🍳 [NOMBRE]\n\n🛒 INGREDIENTES:\n- (lista)\n\n👨‍🍳 PASOS:\n1. (numerados)"
        )
    }]
    for frame in frames:
        contenido.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{imagen_a_base64(frame)}"}
        })
    response = client_groq.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": contenido}],
        temperature=0.3,
        max_tokens=1024
    )
    return response.choices[0].message.content

def dar_formato_receta(texto):
    response = client_groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un chef profesional. Estructura recetas claramente.\n"
                    "Formato:\n🍳 [NOMBRE]\n\n🛒 INGREDIENTES:\n- (lista)\n\n👨‍🍳 PASOS:\n1. (numerados)"
                )
            },
            {"role": "user", "content": f"Estructura esta receta:\n\n{texto}"}
        ],
        temperature=0.3,
        max_tokens=1024
    )
    return response.choices[0].message.content

def limpiar(archivos):
    for f in archivos:
        if f and os.path.exists(f):
            os.remove(f)

def procesar_link(url, prefijo):
    ruta_mp3, ruta_video, frames = None, None, []
    try:
        ruta_mp3 = extraer_audio(url, prefijo)
        texto = transcribir_audio(ruta_mp3)
        if texto and len(texto) > 30:
            return dar_formato_receta(texto)
        else:
            ruta_video = descargar_video(url, prefijo)
            frames = extraer_frames(ruta_video, prefijo)
            if not frames:
                raise Exception("No se pudieron extraer frames.")
            return leer_receta_visual(frames)
    finally:
        limpiar([ruta_mp3, ruta_video] + frames)

# ==========================================
# BOT DE TELEGRAM
# ==========================================

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    user_id = update.message.from_user.id

    if "tiktok.com" not in texto:
        await update.message.reply_text(
            "👋 ¡Hola! Soy *El Pinche de Cocina*.\n\n"
            "Mándame un link de TikTok con una receta y te la escribo bonita 🍳",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Procesando tu receta, espera tantito...")

    try:
        receta = procesar_link(texto, str(user_id))
        await update.message.reply_text(receta)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Algo salió mal:\n`{e}`\n\nVerifica que el link sea válido.",
            parse_mode="Markdown"
        )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    print("🤖 Bot corriendo con webhook...")

    # ✅ Webhook en lugar de polling — sin conflictos posibles
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"https://{RENDER_URL}/webhook"
    )

if __name__ == "__main__":
    main()
