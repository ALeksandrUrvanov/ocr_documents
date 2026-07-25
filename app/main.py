"""
Точка входа.

Порядок:
1. Env-переменные (офлайн)
2. Настройка логирования (ДО импортов!)
3. Startup: загрузка модели + запуск очереди
4. Работа: приём запросов
5. Shutdown: остановка очереди
"""
import os
import sys

# ВАЖНО: Env-переменные ДО импортов
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# КРИТИЧНО: Настройка логирования ДО импорта модулей приложения!
import logging

# Отключаем буферизацию для stdout
sys.stdout.reconfigure(line_buffering=True)

# Создаём handler с немедленной буферизацией
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
handler.setLevel(logging.INFO)

# Настройка корневого логгера
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]  # Заменяем все handlers

# Явная настройка логгера приложения
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)


class EndpointFilter(logging.Filter):
    """Фильтр для скрытия логов GET /status и GET /health."""
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not (
            'GET /api/documents/' in message and '/status' in message or
            'GET /health' in message
        )


# Применяем фильтр к uvicorn логам
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# Импорты приложения ПОСЛЕ настройки логирования
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.core.queue import task_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup и shutdown."""
    logger.info("Запуск сервиса...")
    task_queue.start()
    logger.info("Сервис запущен")
    yield
    logger.info("Остановка сервиса...")
    task_queue.stop()
    logger.info("Сервис остановлен")


app = FastAPI(
    title="OCR Documents Service",
    description="PDF/DOCX/фото → структурированный текст (JSON)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    """Проверка что сервер работает."""
    info = task_queue.get_queue_info()
    return {"status": "ok", **info}
