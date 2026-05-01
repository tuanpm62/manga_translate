from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

DEFAULT: dict = {
    "service": "google",
    "api_key": None,
    "use_free_api": True,
    "source_lang": "ja",
    "target_lang": "en",
    "model": "kha-white/manga-ocr-base",
    "force_cpu": False,
    "delay_secs": 0.1,
    "write_to": "clipboard",
    "verbose": False,
    "websocket_host": "localhost",
    "websocket_port": 7331,
}


def path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "manga_translate" / "config.json"


def load() -> dict:
    cfg_path = path()
    if not cfg_path.exists():
        return DEFAULT.copy()
    try:
        with open(cfg_path, encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULT, **saved}
    except Exception:
        return DEFAULT.copy()


def save(cfg: dict) -> None:
    cfg_path = path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def ensure_exists() -> Path:
    cfg_path = path()
    if not cfg_path.exists():
        save(DEFAULT.copy())
    return cfg_path


def set_value(key: str, value) -> None:
    if key not in DEFAULT:
        raise KeyError(f"Unknown config key: {key!r}. Valid keys: {list(DEFAULT)}")
    cfg = load()
    # coerce type to match default
    default_val = DEFAULT[key]
    if default_val is not None:
        try:
            if isinstance(default_val, bool):
                value = str(value).lower() in ("1", "true", "yes")
            elif isinstance(default_val, int):
                value = int(value)
            elif isinstance(default_val, float):
                value = float(value)
        except (ValueError, TypeError):
            pass
    cfg[key] = value
    save(cfg)


def open_in_editor() -> None:
    cfg_path = ensure_exists()
    if os.name == "nt":
        os.startfile(str(cfg_path))
    else:
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(cfg_path)])
