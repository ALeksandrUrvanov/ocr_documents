"""
OCR Engine — обёртка над PaddleOCR-VL. Синглтон, модель загружается при старте.
"""
import os
import re
import time
import warnings
import logging

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

from app.config import VL_MODEL_DIR, LAYOUT_MODEL_DIR
from app.schemas.documents import Block, PageResult

logger = logging.getLogger(__name__)


class OCREngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Инициализация атрибутов (выполняется только один раз)
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self.pipeline = None

    def initialize(self):
        """Ленивая загрузка модели OCR при первом использовании."""
        if self._initialized:
            return
        logger.info("Загрузка OCR модели...")
        start = time.time()
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU: {gpu_name}")
        
        from paddleocr import PaddleOCRVL
        
        # PaddleOCRVL автоматически использует flash-attn если он установлен
        self.pipeline = PaddleOCRVL(
            layout_detection_model_dir=LAYOUT_MODEL_DIR,
            vl_rec_model_dir=VL_MODEL_DIR,
        )
        self._initialized = True
        logger.info(f"OCR модель готова ({time.time() - start:.1f}s)")

    def recognize_page(self, image_path: str, page_num: int = 1) -> PageResult:
        output = self.pipeline.predict(image_path)
        blocks = []
        
        for result in output:
            res = None
            if hasattr(result, "res"):
                res = result.res
            elif isinstance(result, dict) and "res" in result:
                res = result["res"]
            elif isinstance(result, dict) and "parsing_res_list" in result:
                res = result
            else:
                continue
            
            if isinstance(res, dict) and "parsing_res_list" in res:
                for block in res["parsing_res_list"]:
                    if hasattr(block, 'content') and block.content:
                        content = block.content
                        if _is_junk_block(content):
                            continue
                        blocks.append(
                            Block(label=block.label, content=content, bbox=block.bbox)
                        )
        
        text = "\n".join(b.content for b in blocks)
        return PageResult(page=page_num, blocks=blocks, text=text)


def _is_junk_block(content: str) -> bool:
    """Проверка на мусорный блок (повторяющиеся LaTeX формулы, пустые данные)."""
    if not content or len(content.strip()) < 3:
        return True
    
    # Проверка на повторяющиеся LaTeX формулы типа $ x_{1} $, $ x_{2} $
    latex_pattern = r'\$\s*[a-z]_\{\d+\}\s*\$'
    matches = re.findall(latex_pattern, content)
    if len(matches) > 10:  # Если больше 10 одинаковых формул - это мусор
        return True
    
    # Проверка на блоки с только пробелами/переносами
    if len(content.strip()) < 5 and not any(c.isalnum() for c in content):
        return True
    
    return False


engine = OCREngine()
