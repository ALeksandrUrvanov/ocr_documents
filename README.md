# OCR Documents

OCR для PDF / DOCX / изображений на PaddleOCR-VL + PP-DocLayoutV3. FastAPI, очередь, один воркер.

## Stack

- Python, FastAPI, Uvicorn, Pydantic
- PaddleOCR 3.x (`PaddleOCR-VL-1.5`), PP-DocLayoutV3
- transformers, accelerate, pdf2image, Pillow, python-docx, aiofiles
- Docker, GPU, порт `8086`

## Pipeline

1. `POST /api/documents/upload` → `task_id`.
2. Воркер: документ → изображения → OCR.
3. `GET .../result` отдаёт текст и очищает результат из памяти.

## Run

```bash
# нужны локальные веса в models/official_models/
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8086
# или Docker-образ (GPU)
```

## API

- `GET /health`
- `POST /api/documents/upload`
- `GET /api/documents/{task_id}/status`
- `GET /api/documents/{task_id}/result`
- `GET /api/documents/queue/info`

## Notes

- Веса моделей в репозиторий не входят.
- Очередь и результаты — in-memory, один воркер.
