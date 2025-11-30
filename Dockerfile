# Dockerfile para proyecto de análisis de emociones con DeepFace + YOLO
# Soporte para GPU NVIDIA

FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libboost-all-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.docker.txt requirements.txt

# Instalar dependencias de Python (sin CUDA para imagen base)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Descargar modelo YOLO si no existe
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')" || true

# Crear directorio para base de datos
RUN mkdir -p /app/data

# Puerto para Daphne/Django
EXPOSE 8000

# Variables de entorno
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV DJANGO_SETTINGS_MODULE=config.settings

# Comando por defecto - Daphne para WebSocket + HTTP
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
