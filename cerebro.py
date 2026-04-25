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

def extraer_frames(ruta_video, prefijo, n_fra
