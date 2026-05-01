"""Unit tests — no network, GPU, or real OCR model required."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from manga_translate import config as cfg
from manga_translate.ocr import MangaOCRWrapper
from manga_translate.translator import Translator
from manga_translate.pipeline import MangaTranslatePipeline, PageResult


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_defaults():
    defaults = cfg.DEFAULT
    assert defaults["service"] == "google"
    assert defaults["source_lang"] == "ja"
    assert defaults["target_lang"] == "en"
    assert defaults["delay_secs"] == 0.1
    assert defaults["write_to"] == "clipboard"


def test_config_load_missing_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    loaded = cfg.load()
    assert loaded == cfg.DEFAULT


def test_config_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    data = {**cfg.DEFAULT, "service": "deepl", "api_key": "test-key"}
    cfg.save(data)
    loaded = cfg.load()
    assert loaded["service"] == "deepl"
    assert loaded["api_key"] == "test-key"


def test_config_set_value(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    cfg.set_value("target_lang", "vi")
    assert cfg.load()["target_lang"] == "vi"


def test_config_set_unknown_key_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    with pytest.raises(KeyError):
        cfg.set_value("nonexistent_key", "val")


def test_config_set_bool_coercion(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    cfg.set_value("force_cpu", "true")
    assert cfg.load()["force_cpu"] is True
    cfg.set_value("force_cpu", "false")
    assert cfg.load()["force_cpu"] is False


# ---------------------------------------------------------------------------
# OCR wrapper
# ---------------------------------------------------------------------------

def test_ocr_lazy_load():
    wrapper = MangaOCRWrapper()
    assert wrapper._ocr is None


@patch("manga_translate.ocr.MangaOcr")
def test_ocr_passes_model_and_force_cpu(mock_cls):
    mock_cls.return_value = MagicMock(return_value="text")
    wrapper = MangaOCRWrapper(model="custom/model", force_cpu=True)
    wrapper.read(Image.new("RGB", (50, 50)))
    mock_cls.assert_called_once_with(
        pretrained_model_name_or_path="custom/model", force_cpu=True
    )


@patch("manga_translate.ocr.MangaOcr")
def test_ocr_read_regions(mock_cls):
    mock_cls.return_value = MagicMock(return_value="text")
    wrapper = MangaOCRWrapper()
    img = Image.new("RGB", (200, 200))
    results = wrapper.read_regions(img, [(0, 0, 100, 100), (100, 100, 200, 200)])
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Translator — Google
# ---------------------------------------------------------------------------

@patch("manga_translate.translator.GoogleTranslator")
def test_google_caches(mock_cls):
    mock_inst = MagicMock()
    mock_inst.translate.return_value = "Hello"
    mock_cls.return_value = mock_inst

    t = Translator()
    assert t.translate("こんにちは") == "Hello"
    assert t.translate("こんにちは") == "Hello"
    mock_inst.translate.assert_called_once()


@patch("manga_translate.translator.GoogleTranslator")
def test_google_empty(mock_cls):
    mock_cls.return_value = MagicMock()
    t = Translator()
    assert t.translate("") == ""
    assert t.translate("  ") == ""


# ---------------------------------------------------------------------------
# Translator — DeepL
# ---------------------------------------------------------------------------

@patch("manga_translate.translator.DeeplTranslator")
def test_deepl_free(mock_cls):
    mock_inst = MagicMock()
    mock_inst.translate.return_value = "Hello"
    mock_cls.return_value = mock_inst

    t = Translator(service="deepl", api_key="key", use_free_api=True)
    assert t.translate("こんにちは") == "Hello"
    mock_cls.assert_called_once_with(
        api_key="key", source="ja", target="en", use_free_api=True
    )


@patch("manga_translate.translator.DeeplTranslator")
def test_deepl_pro(mock_cls):
    mock_cls.return_value = MagicMock(translate=MagicMock(return_value="Hi"))
    Translator(service="deepl", api_key="pro-key", use_free_api=False)
    mock_cls.assert_called_once_with(
        api_key="pro-key", source="ja", target="en", use_free_api=False
    )


def test_deepl_no_key_raises():
    with pytest.raises(ValueError, match="api_key is required"):
        Translator(service="deepl")


def test_unsupported_service_raises():
    with pytest.raises(ValueError, match="service must be one of"):
        Translator(service="yandex")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@patch("manga_translate.pipeline.Translator")
@patch("manga_translate.pipeline.MangaOCRWrapper")
def test_pipeline_whole_image(mock_ocr_cls, mock_trans_cls):
    mock_ocr = MagicMock()
    mock_ocr.read_regions.return_value = ["日本語"]
    mock_ocr_cls.return_value = mock_ocr

    mock_trans = MagicMock()
    mock_trans.translate_batch.return_value = ["Japanese"]
    mock_trans_cls.return_value = mock_trans

    pipeline = MangaTranslatePipeline()
    img = Image.new("RGB", (300, 400))
    result = pipeline.process_image(img)

    assert result.regions == [(0, 0, 300, 400)]
    assert result.original_texts == ["日本語"]
    assert result.translated_texts == ["Japanese"]


@patch("manga_translate.pipeline.Translator")
@patch("manga_translate.pipeline.MangaOCRWrapper")
def test_pipeline_model_forwarded(mock_ocr_cls, mock_trans_cls):
    mock_ocr_cls.return_value = MagicMock()
    mock_ocr_cls.return_value.read_regions.return_value = ["text"]
    mock_trans_cls.return_value = MagicMock()
    mock_trans_cls.return_value.translate_batch.return_value = ["text"]

    MangaTranslatePipeline(model="custom/model", force_cpu=True, verbose=True)
    mock_ocr_cls.assert_called_once_with(
        model="custom/model", force_cpu=True, verbose=True
    )


@patch("manga_translate.pipeline.Translator")
@patch("manga_translate.pipeline.MangaOCRWrapper")
def test_page_result_as_dict(mock_ocr_cls, mock_trans_cls):
    mock_ocr_cls.return_value = MagicMock()
    mock_ocr_cls.return_value.read_regions.return_value = ["テキスト"]
    mock_trans_cls.return_value = MagicMock()
    mock_trans_cls.return_value.translate_batch.return_value = ["Text"]

    pipeline = MangaTranslatePipeline()
    result = pipeline.process_image(Image.new("RGB", (100, 100)))
    d = result.as_dict()

    assert d["panels"][0]["original"] == "テキスト"
    assert d["panels"][0]["translated"] == "Text"


@patch("manga_translate.pipeline.Translator")
@patch("manga_translate.pipeline.MangaOCRWrapper")
def test_page_result_format_text(mock_ocr_cls, mock_trans_cls):
    mock_ocr_cls.return_value = MagicMock()
    mock_ocr_cls.return_value.read_regions.return_value = ["a", "b"]
    mock_trans_cls.return_value = MagicMock()
    mock_trans_cls.return_value.translate_batch.return_value = ["A", "B"]

    pipeline = MangaTranslatePipeline()
    img = Image.new("RGB", (200, 100))
    result = pipeline.process_image(img, regions=[(0, 0, 100, 100), (100, 0, 200, 100)])
    assert result.format_text(" | ") == "A | B"
