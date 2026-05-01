from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import config as cfg
from .pipeline import MangaTranslatePipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pipeline_from_ctx(ctx_obj: dict, **overrides) -> MangaTranslatePipeline:
    """Build a pipeline, merging saved config < ctx_obj < overrides."""
    merged = {**ctx_obj, **{k: v for k, v in overrides.items() if v is not None}}
    return MangaTranslatePipeline(
        source_lang=merged.get("source_lang", "ja"),
        target_lang=merged.get("target_lang", "en"),
        service=merged.get("service", "google"),
        api_key=merged.get("api_key"),
        use_free_api=merged.get("use_free_api", True),
        model=merged.get("model", "kha-white/manga-ocr-base"),
        force_cpu=merged.get("force_cpu", False),
        verbose=merged.get("verbose", False),
    )


def _write_result(translated_texts: list[str], write_to: str) -> None:
    """Write translated text to clipboard or append to a file."""
    text = "\n".join(translated_texts)
    if write_to == "clipboard":
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            click.echo("[warn] pyperclip not installed — cannot copy to clipboard.", err=True)
            click.echo(text)
    else:
        with open(write_to, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def _print_result(result, json_output: bool = False) -> None:
    if json_output:
        click.echo(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        for orig, trans in zip(result.original_texts, result.translated_texts):
            click.echo(orig)
            click.echo(f"  -> {trans}\n")


# Shared options applied to every command that needs translation settings
def _translator_options(f):
    for dec in reversed([
        click.option("--source", "-s", default=None, help="Source language [config: source_lang]."),
        click.option("--target", "-t", default=None, help="Target language [config: target_lang]."),
        click.option("--service", default=None,
                     type=click.Choice(["google", "deepl"], case_sensitive=False),
                     help="Translation service [config: service]."),
        click.option("--api-key", "api_key", envvar="DEEPL_API_KEY", default=None,
                     help="DeepL API key, or set DEEPL_API_KEY env var."),
        click.option("--pro", "use_free_api", is_flag=True, default=None, flag_value=False,
                     help="Use DeepL Pro endpoint (default: Free)."),
        click.option("--model", default=None, help="HuggingFace model [config: model]."),
        click.option("--force-cpu", "force_cpu", is_flag=True, default=None,
                     help="Force CPU mode."),
        click.option("--verbose", is_flag=True, default=None,
                     help="Show all warnings."),
    ]):
        f = dec(f)
    return f


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """manga-translate: manga_ocr + translation.

    Run with no subcommand to start clipboard watch mode (same as `watch`).
    """
    ctx.ensure_object(dict)
    ctx.obj = cfg.load()
    if ctx.invoked_subcommand is None:
        ctx.invoke(watch)


# ---------------------------------------------------------------------------
# watch  (mirrors manga_ocr default: read_from=clipboard, write_to=clipboard)
# ---------------------------------------------------------------------------

@main.command()
@_translator_options
@click.option("--write-to", "write_to", default=None,
              help="'clipboard' or path to .txt file [config: write_to].")
@click.option("--delay-secs", "delay_secs", default=None, type=float,
              help="Clipboard poll interval in seconds [config: delay_secs].")
@click.pass_obj
def watch(obj, source, target, service, api_key, use_free_api, model,
          force_cpu, verbose, write_to, delay_secs):
    """Watch clipboard; OCR + translate every new image (default mode)."""
    from .screenshot import watch_clipboard

    c = obj or cfg.load()
    write_to = write_to or c.get("write_to", "clipboard")
    delay = delay_secs if delay_secs is not None else c.get("delay_secs", 0.1)
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    dest = f"file: {write_to}" if write_to != "clipboard" else "clipboard"
    click.echo(f"Watching clipboard -> {dest}  (Ctrl+C to stop)")

    def on_image(img):
        result = pipeline.process_image(img)
        _print_result(result)
        _write_result(result.translated_texts, write_to)

    try:
        watch_clipboard(on_image, poll_interval=delay)
    except KeyboardInterrupt:
        click.echo("\nStopped.")


# ---------------------------------------------------------------------------
# folder  (mirrors manga_ocr: read_from=<dir>, write_to=clipboard|file)
# ---------------------------------------------------------------------------

@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@_translator_options
@click.option("--write-to", "write_to", default=None,
              help="'clipboard' or path to .txt file [config: write_to].")
@click.option("--delay-secs", "delay_secs", default=None, type=float,
              help="Folder poll interval in seconds [config: delay_secs].")
@click.pass_obj
def folder(obj, directory, source, target, service, api_key, use_free_api,
           model, force_cpu, verbose, write_to, delay_secs):
    """Watch DIRECTORY for new images; OCR + translate each one."""
    from .screenshot import watch_folder

    c = obj or cfg.load()
    write_to = write_to or c.get("write_to", "clipboard")
    delay = delay_secs if delay_secs is not None else c.get("delay_secs", 0.1)
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    dest = f"file: {write_to}" if write_to != "clipboard" else "clipboard"
    click.echo(f"Watching {directory} -> {dest}  (Ctrl+C to stop)")

    def on_image(img, img_path):
        click.echo(f"\n[{img_path.name}]")
        result = pipeline.process_image(img)
        _print_result(result)
        _write_result(result.translated_texts, write_to)

    try:
        watch_folder(Path(directory), on_image, poll_interval=delay)
    except KeyboardInterrupt:
        click.echo("\nStopped.")


# ---------------------------------------------------------------------------
# screenshot  (snip region)
# ---------------------------------------------------------------------------

@main.command()
@_translator_options
@click.option("--write-to", "write_to", default=None,
              help="'clipboard' or path to .txt file [config: write_to].")
@click.option("--output", "-o", default=None, help="Save overlaid image to this path.")
@click.option("--json-output", "-j", is_flag=True)
@click.pass_obj
def screenshot(obj, source, target, service, api_key, use_free_api, model,
               force_cpu, verbose, write_to, output, json_output):
    """Snip a screen region, OCR it, and translate.

    Opens a full-screen overlay: drag to select, Esc to cancel.
    """
    from .screenshot import capture_region_interactive

    c = obj or cfg.load()
    write_to = write_to or c.get("write_to", "clipboard")
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    click.echo("Draw a selection (drag), Esc to cancel...")
    img = capture_region_interactive()

    if img is None:
        click.echo("Cancelled.")
        sys.exit(0)

    result = pipeline.process_image(img)
    _print_result(result, json_output)
    _write_result(result.translated_texts, write_to)

    if output:
        pipeline.overlay_translations(img, result, output_path=output)
        click.echo(f"Saved: {output}")


# ---------------------------------------------------------------------------
# translate  (single file)
# ---------------------------------------------------------------------------

@main.command()
@click.argument("image", type=click.Path(exists=True))
@_translator_options
@click.option("--write-to", "write_to", default=None,
              help="'clipboard' or path to .txt file [config: write_to].")
@click.option("--output", "-o", default=None, help="Save overlaid image to this path.")
@click.option("--json-output", "-j", is_flag=True)
@click.pass_obj
def translate(obj, image, source, target, service, api_key, use_free_api,
              model, force_cpu, verbose, write_to, output, json_output):
    """OCR and translate a single IMAGE file."""
    c = obj or cfg.load()
    write_to = write_to or c.get("write_to", "clipboard")
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    result = pipeline.process_image(image)
    _print_result(result, json_output)
    _write_result(result.translated_texts, write_to)

    if output:
        from PIL import Image as PILImage
        pipeline.overlay_translations(PILImage.open(image), result, output_path=output)
        click.echo(f"Saved: {output}")


# ---------------------------------------------------------------------------
# batch  (folder of files, one-shot)
# ---------------------------------------------------------------------------

@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@_translator_options
@click.option("--output-dir", "-o", default=None, help="Save overlaid images here.")
@click.option("--json-output", "-j", is_flag=True)
@click.pass_obj
def batch(obj, directory, source, target, service, api_key, use_free_api,
          model, force_cpu, verbose, output_dir, json_output):
    """OCR and translate all images in DIRECTORY (one-shot, not watching)."""
    c = obj or cfg.load()
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    out_dir = Path(output_dir) if output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = pipeline.process_directory(directory)
    all_data = []

    for result in results:
        all_data.append(result.as_dict())
        if not json_output:
            click.echo(f"\n=== {result.image_path} ===")
            _print_result(result)

        if out_dir and result.image_path != "<PIL.Image>":
            from PIL import Image as PILImage
            src = Path(result.image_path)
            pipeline.overlay_translations(PILImage.open(src), result,
                                          output_path=out_dir / src.name)

    if json_output:
        click.echo(json.dumps(all_data, ensure_ascii=False, indent=2))
    if out_dir:
        click.echo(f"\nOverlaid images saved to: {out_dir}")


# ---------------------------------------------------------------------------
# serve  (WebSocket server)
# ---------------------------------------------------------------------------

@main.command()
@_translator_options
@click.option("--host", default=None, help="Bind host [config: websocket_host].")
@click.option("--port", default=None, type=int, help="Bind port [config: websocket_port].")
@click.pass_obj
def serve(obj, source, target, service, api_key, use_free_api, model,
          force_cpu, verbose, host, port):
    """Start a WebSocket server that accepts images and returns translations.

    Protocol: send a base64-encoded image, receive JSON:
    {"original": ["..."], "translated": ["..."]}
    """
    from . import websocket_server

    c = obj or cfg.load()
    pipeline = _pipeline_from_ctx(c, source_lang=source, target_lang=target,
                                   service=service, api_key=api_key,
                                   use_free_api=use_free_api, model=model,
                                   force_cpu=force_cpu, verbose=verbose)

    ws_host = host or c.get("websocket_host", "localhost")
    ws_port = port or c.get("websocket_port", 7331)
    _verbose = verbose if verbose is not None else c.get("verbose", False)

    websocket_server.run(pipeline, host=ws_host, port=ws_port, verbose=_verbose)


# ---------------------------------------------------------------------------
# config  (manage saved settings)
# ---------------------------------------------------------------------------

@main.command("config")
@click.option("--show", "action", flag_value="show", default=True,
              help="Print current config (default).")
@click.option("--edit", "action", flag_value="edit",
              help="Open config file in system editor.")
@click.option("--reset", "action", flag_value="reset",
              help="Reset config to defaults.")
@click.option("--set", "set_kv", metavar="KEY=VALUE", default=None,
              help="Set a single config value, e.g. --set service=deepl")
@click.option("--path", "action", flag_value="path",
              help="Print config file path.")
def config_cmd(action, set_kv):
    """Manage saved configuration (service, API key, languages, etc.)."""
    if set_kv:
        if "=" not in set_kv:
            raise click.UsageError("--set expects KEY=VALUE format.")
        key, _, value = set_kv.partition("=")
        try:
            cfg.set_value(key.strip(), value.strip())
            click.echo(f"Set {key.strip()} = {value.strip()}")
        except KeyError as e:
            raise click.UsageError(str(e))
        return

    if action == "show":
        current = cfg.load()
        click.echo(f"Config file: {cfg.path()}\n")
        for k, v in current.items():
            marker = " *" if current[k] != cfg.DEFAULT.get(k) else ""
            click.echo(f"  {k:<22} {v}{marker}")
        click.echo("\n* = differs from default")

    elif action == "edit":
        cfg.open_in_editor()
        click.echo(f"Opened: {cfg.path()}")

    elif action == "reset":
        if click.confirm("Reset all settings to defaults?"):
            cfg.save(cfg.DEFAULT.copy())
            click.echo("Config reset to defaults.")

    elif action == "path":
        click.echo(cfg.path())
