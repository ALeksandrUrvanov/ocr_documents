"""
Очистка памяти и файлов после каждой задачи.
"""
import gc
import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_files(*paths: str):
    for path in paths:
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                p.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"Failed to cleanup {path}: {e}")


def cleanup_temp_images(image_paths: list[str], original_path: str):
    dirs_to_remove = set()
    for path in image_paths:
        if path != original_path:
            try:
                os.remove(path)
                dirs_to_remove.add(os.path.dirname(path))
            except OSError:
                pass
    for dir_path in dirs_to_remove:
        try:
            if dir_path and os.path.isdir(dir_path) and not os.listdir(dir_path):
                os.rmdir(dir_path)
        except OSError:
            pass


def cleanup_gpu():
    """Принудительная очистка GPU памяти."""
    try:
        import torch
        if torch.cuda.is_available():
            # Множественная очистка для надёжности
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # Дожидаемся завершения операций
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.debug("GPU cache cleared")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"GPU cleanup failed: {e}")


def cleanup_ram():
    """Принудительная сборка мусора."""
    gc.collect()
    gc.collect()  # Двойной вызов для циклических ссылок
    logger.debug("RAM garbage collected")


def full_cleanup(task_dir: str, temp_images: list[str] | None = None):
    """Полная очистка: файлы + GPU + RAM."""
    cleanup_files(task_dir)
    if temp_images:
        cleanup_temp_images(temp_images, "")
    cleanup_gpu()
    cleanup_ram()
