FROM python:3.11-slim

# Instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copiar archivos
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY cerebro.py .

# Correr el bot
CMD ["python", "cerebro.py"]
