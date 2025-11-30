# Dockerfile para análisis de emociones - Compatible Windows/Linux
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Dependencias del sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.txt

# Copiar proyecto
COPY config/ ./config/
COPY manage.py .
COPY main.py .

# Crear directorios y migrar base de datos
RUN mkdir -p /app/data && \
    python manage.py migrate --run-syncdb

# Descargar modelo YOLO
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')" || echo "YOLO skipped"

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
