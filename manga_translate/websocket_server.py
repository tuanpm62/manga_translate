from __future__ import annotations

import asyncio
import base64
import io
import json

from PIL import Image


async def _handle(websocket, pipeline, verbose: bool) -> None:
    """Handle a single WebSocket connection.

    Protocol:
      - Client sends: base64-encoded image (PNG/JPEG/etc.)
      - Server replies: JSON  {"original": [...], "translated": [...]}
    """
    async for message in websocket:
        try:
            img_bytes = base64.b64decode(message)
            img = Image.open(io.BytesIO(img_bytes))
            result = pipeline.process_image(img)
            response = json.dumps(
                {"original": result.original_texts, "translated": result.translated_texts},
                ensure_ascii=False,
            )
            await websocket.send(response)
        except Exception as exc:
            if verbose:
                print(f"[ws] error: {exc}")
            try:
                await websocket.send(json.dumps({"error": str(exc)}))
            except Exception:
                pass


def run(pipeline, host: str = "localhost", port: int = 7331, verbose: bool = False) -> None:
    """Start the WebSocket server (blocking)."""
    try:
        import websockets
    except ImportError:
        raise ImportError("Run: pip install websockets")

    async def serve() -> None:
        handler = lambda ws: _handle(ws, pipeline, verbose)
        async with websockets.serve(handler, host, port):
            print(f"WebSocket server on ws://{host}:{port}")
            print("Send base64-encoded images; receive JSON with original + translated text.")
            print("Ctrl+C to stop.")
            await asyncio.Future()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nServer stopped.")
