"""
Очередь задач: upload → temp → OCR → результат в памяти → клиент забирает → очистка.
"""
import logging
import threading
import time
import traceback
from collections import deque

from app.config import TEMP_DIR, MAX_CONCURRENT_TASKS
from app.schemas.documents import DocumentResult, TaskStatus
from app.core.ocr_engine import engine
from app.core.converter import file_to_images
from app.core.cleanup import full_cleanup

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self):
        self._queue: deque[str] = deque()
        self._results: dict[str, DocumentResult] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(MAX_CONCURRENT_TASKS)
        self._running = False
        self._active_workers: set[threading.Thread] = set()
        self._workers_lock = threading.Lock()

    def start(self):
        engine.initialize()
        self._running = True
        thread = threading.Thread(target=self._dispatcher, daemon=False, name="TaskDispatcher")
        thread.start()
        logger.info(f"Очередь запущена (макс. задач: {MAX_CONCURRENT_TASKS})")

    def stop(self):
        """Graceful shutdown: дожидается завершения всех активных задач."""
        logger.info("Остановка очереди...")
        self._running = False
        
        # Ждём завершения всех активных worker threads
        with self._workers_lock:
            active = list(self._active_workers)
        
        if active:
            logger.info(f"Ожидание завершения {len(active)} активных задач...")
            for worker in active:
                worker.join(timeout=60)  # Даём 60 секунд на завершение каждой задачи
                if worker.is_alive():
                    logger.warning(f"Задача {worker.name} не завершилась вовремя")
        
        logger.info("Очередь остановлена")

    def add_task(self, task_id: str, filename: str):
        with self._lock:
            self._results[task_id] = DocumentResult(
                task_id=task_id, filename=filename, status=TaskStatus.queued
            )
            self._queue.append(task_id)

    def get_result(self, task_id: str) -> DocumentResult | None:
        with self._lock:
            return self._results.get(task_id)

    def pop_result(self, task_id: str) -> DocumentResult | None:
        with self._lock:
            result = self._results.pop(task_id, None)
        
        # АГРЕССИВНАЯ очистка GPU/RAM после отдачи результата клиенту
        if result:
            import gc
            gc.collect(generation=2)  # Полная сборка мусора всех поколений
            gc.collect(generation=1)
            gc.collect(generation=0)
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    torch.cuda.ipc_collect()
                    torch.cuda.empty_cache()  # Второй раз для надёжности
            except (ImportError, RuntimeError):
                pass
        
        return result

    def get_queue_info(self) -> dict:
        with self._lock:
            return {"queued": len(self._queue), "active_results": len(self._results)}

    def _dispatcher(self):
        while self._running:
            task_id = None
            with self._lock:
                if self._queue:
                    task_id = self._queue.popleft()
            if task_id is None:
                time.sleep(0.5)
                continue
            self._semaphore.acquire()
            thread = threading.Thread(target=self._process_task, args=(task_id,), daemon=False, name=f"Worker-{task_id}")
            with self._workers_lock:
                self._active_workers.add(thread)
            thread.start()

    def _process_task(self, task_id: str):
        task_dir = str(TEMP_DIR / task_id)
        temp_images = []
        try:
            with self._lock:
                result = self._results[task_id]
                result.status = TaskStatus.processing
            file_path = str(TEMP_DIR / task_id / result.filename)
            logger.info(f"[{task_id}] Начало: {result.filename}")
            temp_images = file_to_images(file_path)
            with self._lock:
                result.total_pages = len(temp_images)
            
            all_pages = []
            total_blocks = 0
            task_start = time.time()
            
            for i, img_path in enumerate(temp_images):
                page_result = engine.recognize_page(img_path, page_num=i + 1)
                all_pages.append(page_result)
                total_blocks += len(page_result.blocks)
                with self._lock:
                    result.processed_pages = i + 1
                
                # Принудительная очистка памяти каждые 5 страниц
                if i > 0 and i % 5 == 0:
                    import gc
                    gc.collect()
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                    except (ImportError, RuntimeError):
                        # torch может быть недоступен или CUDA ошибка
                        pass
            
            full_text = "\n\n".join(f"--- Страница {p.page} ---\n{p.text}" for p in all_pages)
            with self._lock:
                result.pages = all_pages
                result.full_text = full_text
                result.status = TaskStatus.completed
            
            elapsed = time.time() - task_start
            logger.info(f"[{task_id}] Завершено: {len(temp_images)} стр., {total_blocks} блоков, {elapsed:.1f}s")
        except Exception as e:
            logger.error(f"[{task_id}] Failed: {e}")
            logger.error(traceback.format_exc())
            with self._lock:
                if task_id in self._results:
                    self._results[task_id].status = TaskStatus.failed
                    self._results[task_id].error = str(e)
        finally:
            # Очистка файлов и временных данных
            full_cleanup(task_dir, temp_images)
            
            self._semaphore.release()
            with self._workers_lock:
                self._active_workers.discard(threading.current_thread())


task_queue = TaskQueue()
