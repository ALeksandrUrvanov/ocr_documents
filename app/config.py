"""
Настройки проекта.

Все параметры собраны в одном месте.
Менять поведение сервиса — только здесь.
"""
from pathlib import Path

# Корень проекта (папка где лежит app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Пути к моделям
MODELS_DIR = BASE_DIR / "models" / "official_models"
VL_MODEL_DIR = str(MODELS_DIR / "PaddleOCR-VL-1.5")
LAYOUT_MODEL_DIR = str(MODELS_DIR / "PP-DocLayoutV3")

# Временное хранилище (очищается после каждой задачи)
TEMP_DIR = BASE_DIR / "storage" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Допустимые форматы файлов
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg",
    ".tiff", ".tif", ".bmp",
    ".pdf", ".docx",
}

# Лимит размера файла (MB)
MAX_FILE_SIZE_MB = 200

# Сколько документов обрабатывать параллельно
MAX_CONCURRENT_TASKS = 1

# Разрешение при конвертации PDF в изображения.
# 300 — стандарт, 350–400 — лучше мелкий текст/сложные формы, 500–600 — макс. качество, сильно растёт память.
# Практичный максимум для 100 стр.: 400–450; 600 возможен для коротких документов.
PDF_DPI = 400

# Минимальная сторона изображения для апскейла (если меньше — масштабируем для лучшего OCR)
IMAGE_MIN_SIDE = 1200

# Предобработка перед OCR: черно-белое и резкость
PREPROCESS_GRAYSCALE = True   # Привести к оттенкам серого (часто улучшает текст)
PREPROCESS_BINARIZE = False   # True — чисто ч/б (порог 127); может терять детали на фото
PREPROCESS_SHARPNESS = 1.25   # Коэффициент резкости (1.0 = без изменений, 1.2–1.3 = чуть выше)
