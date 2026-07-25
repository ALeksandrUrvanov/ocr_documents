FROM nvcr.io/nvidia/cuda:12.6.3-base-ubuntu22.04

# Переменные окружения
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# Слой 1: Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip \
    libgl1 libglib2.0-0 libgomp1 \
    poppler-utils libreoffice-writer \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

RUN ln -sf /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# Слой 2: PaddlePaddle GPU
RUN pip install --no-cache-dir \
    paddlepaddle-gpu==3.2.1 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

# Слой 3: PyTorch GPU
RUN pip install --no-cache-dir \
    torch==2.6.0 \
    --index-url https://download.pytorch.org/whl/cu126

# Слой 4: Flash Attention (pre-built wheel)
RUN pip install --no-cache-dir \
    https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.5cxx11abiTRUE-cp310-cp310-linux_x86_64.whl \
    || echo "WARNING: flash-attn installation failed, continuing without it"

# Слой 5: Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y triton torchvision -q 2>/dev/null || true && \
    rm -rf /root/.cache /tmp/* /root/.cargo

# Слой 6: Модели OCR
COPY models/ models/

# Слой 7: Код приложения
COPY app/ app/

# Слой 8: Директория для временных файлов
RUN mkdir -p storage/temp

EXPOSE 8086

# Отключаем буферизацию Python для мгновенного вывода логов в Docker
ENV PYTHONUNBUFFERED=1

# Таймауты: keep-alive для долгих задач, graceful shutdown для завершения активных задач
CMD ["python", "-u", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8086", \
     "--timeout-keep-alive", "3600", \
     "--timeout-graceful-shutdown", "180"]
