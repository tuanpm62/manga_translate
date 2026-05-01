from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

from .ocr import MangaOCRWrapper
from .translator import Translator


@dataclass
class PageResult:
    image_path: str
    regions: list[tuple[int, int, int, int]]
    original_texts: list[str]
    translated_texts: list[str]

    def as_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "panels": [
                {"region": r, "original": o, "translated": t}
                for r, o, t in zip(self.regions, self.original_texts, self.translated_texts)
            ],
        }

    def format_text(self, separator: str = "\n") -> str:
        """Return translated texts joined by separator."""
        return separator.join(self.translated_texts)


@dataclass
class MangaTranslatePipeline:
    """End-to-end OCR + translation pipeline for manga pages."""

    source_lang: str = "ja"
    target_lang: str = "en"
    service: str = "google"
    api_key: str | None = None
    use_free_api: bool = True
    model: str = "kha-white/manga-ocr-base"
    force_cpu: bool = False
    verbose: bool = False
    font_path: str | None = None
    font_size: int = 18
    _ocr: MangaOCRWrapper = field(default=None, init=False, repr=False)
    _translator: Translator = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._ocr = MangaOCRWrapper(
            model=self.model,
            force_cpu=self.force_cpu,
            verbose=self.verbose,
        )
        self._translator = Translator(
            source=self.source_lang,
            target=self.target_lang,
            service=self.service,
            api_key=self.api_key,
            use_free_api=self.use_free_api,
        )

    def process_image(
        self,
        image: Union[str, Path, Image.Image],
        regions: list[tuple[int, int, int, int]] | None = None,
    ) -> PageResult:
        """OCR and translate one image.

        When regions is None the whole image is treated as one panel.
        """
        path_str = str(image) if not isinstance(image, Image.Image) else "<PIL.Image>"
        if isinstance(image, (str, Path)):
            image = Image.open(image)

        if regions is None:
            regions = [(0, 0, image.width, image.height)]

        originals = self._ocr.read_regions(image, regions)
        translated = self._translator.translate_batch(originals)

        return PageResult(
            image_path=path_str,
            regions=regions,
            original_texts=originals,
            translated_texts=translated,
        )

    def process_directory(
        self,
        directory: Union[str, Path],
        extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp"),
    ) -> list[PageResult]:
        """Process every image in a directory (sorted by name)."""
        directory = Path(directory)
        images = sorted(p for p in directory.iterdir() if p.suffix.lower() in extensions)
        return [self.process_image(img) for img in images]

    def overlay_translations(
        self,
        image: Union[str, Path, Image.Image],
        result: PageResult,
        output_path: Union[str, Path] | None = None,
        fill_color: tuple[int, int, int] = (255, 255, 255),
        text_color: tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        """Paint translated text over each region and optionally save."""
        if isinstance(image, (str, Path)):
            image = Image.open(image).convert("RGB")
        else:
            image = image.copy().convert("RGB")

        draw = ImageDraw.Draw(image)
        try:
            font = (
                ImageFont.truetype(self.font_path, self.font_size)
                if self.font_path
                else ImageFont.load_default()
            )
        except (IOError, OSError):
            font = ImageFont.load_default()

        for region, text in zip(result.regions, result.translated_texts):
            draw.rectangle(region, fill=fill_color)
            draw.text((region[0] + 2, region[1] + 2), text, fill=text_color, font=font)

        if output_path:
            image.save(output_path)
        return image
