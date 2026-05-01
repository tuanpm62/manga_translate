from __future__ import annotations

import warnings
from pathlib import Path
from typing import Union

from PIL import Image


class MangaOCRWrapper:
    """Lazy-loading wrapper around manga_ocr.MangaOcr."""

    def __init__(
        self,
        model: str = "kha-white/manga-ocr-base",
        force_cpu: bool = False,
        verbose: bool = False,
    ) -> None:
        self._model = model
        self._force_cpu = force_cpu
        self._verbose = verbose
        self._ocr = None

    def _load(self) -> None:
        if self._ocr is not None:
            return
        if not self._verbose:
            warnings.filterwarnings("ignore")
        from manga_ocr import MangaOcr
        self._ocr = MangaOcr(
            pretrained_model_name_or_path=self._model,
            force_cpu=self._force_cpu,
        )
        if not self._verbose:
            warnings.resetwarnings()

    def read(self, image: Union[str, Path, Image.Image]) -> str:
        """Extract Japanese text from a manga image or image region."""
        self._load()
        if isinstance(image, (str, Path)):
            image = Image.open(image)
        return self._ocr(image)

    def read_regions(
        self,
        image: Union[str, Path, Image.Image],
        regions: list[tuple[int, int, int, int]],
    ) -> list[str]:
        """Extract text from multiple bounding-box regions of an image."""
        if isinstance(image, (str, Path)):
            image = Image.open(image)
        return [self.read(image.crop(r)) for r in regions]
