from .pipeline import MangaTranslatePipeline, PageResult
from .ocr import MangaOCRWrapper
from .translator import Translator
from . import config

__version__ = "0.2.0"
__all__ = ["MangaTranslatePipeline", "PageResult", "MangaOCRWrapper", "Translator", "config"]
