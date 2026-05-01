from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from typing import Callable

from PIL import Image, ImageGrab, ImageTk

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


def capture_fullscreen() -> Image.Image:
    return ImageGrab.grab()


def capture_region_interactive() -> Image.Image | None:
    """Full-screen snipping overlay — drag to select, Esc to cancel."""
    screenshot = ImageGrab.grab()
    selected: dict = {}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(cursor="cross")

    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    tk_image = ImageTk.PhotoImage(screenshot)
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)
    canvas.create_rectangle(
        0, 0, screenshot.width, screenshot.height,
        fill="black", stipple="gray25", outline="",
    )

    start_x = start_y = 0
    rect_id = None

    def on_press(event: tk.Event) -> None:
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        rect_id = canvas.create_rectangle(
            start_x, start_y, start_x, start_y, outline="red", width=2,
        )

    def on_drag(event: tk.Event) -> None:
        if rect_id is not None:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_release(event: tk.Event) -> None:
        x0, y0 = min(start_x, event.x), min(start_y, event.y)
        x1, y1 = max(start_x, event.x), max(start_y, event.y)
        if (x1 - x0) > 5 and (y1 - y0) > 5:
            selected["region"] = (x0, y0, x1, y1)
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda _: root.destroy())
    root.mainloop()

    if "region" not in selected:
        return None
    return screenshot.crop(selected["region"])


def watch_clipboard(
    callback: Callable[[Image.Image], None],
    poll_interval: float = 0.1,
    stop_event=None,
) -> None:
    """Poll clipboard; call callback(image) whenever a new image appears."""
    last_data: bytes | None = None

    while True:
        if stop_event is not None and stop_event.is_set():
            break
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                current = img.tobytes()
                if current != last_data:
                    last_data = current
                    callback(img)
        except Exception:
            pass
        time.sleep(poll_interval)


def watch_folder(
    folder: Path,
    callback: Callable[[Image.Image, Path], None],
    poll_interval: float = 0.1,
    stop_event=None,
) -> None:
    """Poll a folder; call callback(image, path) for each new image file."""
    folder = Path(folder)
    seen = {p.name for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS}

    while True:
        if stop_event is not None and stop_event.is_set():
            break
        try:
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() in IMAGE_EXTS and p.name not in seen:
                    seen.add(p.name)
                    try:
                        callback(Image.open(p), p)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(poll_interval)
