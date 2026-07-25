"""Pydantic-схемы для API."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Block(BaseModel):
    """Блок текста с позицией на странице."""
    label: str = Field(..., description="Тип блока (text, title, list, table, etc)")
    content: str = Field(..., description="Содержимое блока")
    bbox: list[float] = Field(..., description="Координаты [x1, y1, x2, y2]")


class PageResult(BaseModel):
    """Результат обработки одной страницы."""
    page: int = Field(..., description="Номер страницы")
    blocks: list[Block] = Field(default_factory=list, description="Блоки текста на странице")
    text: str = Field(default="", description="Весь текст страницы")


class DocumentResult(BaseModel):
    """Полный результат обработки документа."""
    task_id: str
    filename: str
    status: TaskStatus
    total_pages: int = 0
    processed_pages: int = 0
    pages: list[PageResult] = []
    full_text: str = ""
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Ответ на загрузку документа."""
    task_id: str = Field(..., description="ID задачи для отслеживания")
    filename: str = Field(..., description="Имя загруженного файла")
    size_mb: float = Field(..., description="Размер файла в MB")
    status: str = Field(default="queued", description="Начальный статус")


class StatusResponse(BaseModel):
    """Ответ на запрос статуса."""
    task_id: str
    filename: str
    status: TaskStatus
    total_pages: int = Field(default=0, description="Всего страниц в документе")
    processed_pages: int = Field(default=0, description="Обработано страниц")


class QueueInfoResponse(BaseModel):
    """Информация об очереди."""
    queued: int = Field(..., description="Задач в очереди")
    active_results: int = Field(..., description="Активных результатов в памяти")
