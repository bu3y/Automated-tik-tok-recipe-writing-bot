FROM python:3.11-slim

# Instalar ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar TODO lo del repo
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "cerebro.py"]
