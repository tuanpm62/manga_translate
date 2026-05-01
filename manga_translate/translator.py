from __future__ import annotations

from deep_translator import DeeplTranslator, GoogleTranslator


SUPPORTED_SERVICES = {"google", "deepl"}


def _build_backend(service: str, source: str, target: str, **kwargs):
    if service == "deepl":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("api_key is required for DeepL service")
        return DeeplTranslator(
            api_key=api_key,
            source=source,
            target=target,
            use_free_api=kwargs.get("use_free_api", True),
        )
    return GoogleTranslator(source=source, target=target)


class Translator:
    """Thin wrapper around deep-translator with caching.

    Supports 'google' (no key) and 'deepl' (requires api_key).
    """

    def __init__(
        self,
        source: str = "ja",
        target: str = "en",
        service: str = "google",
        api_key: str | None = None,
        use_free_api: bool = True,
    ) -> None:
        if service not in SUPPORTED_SERVICES:
            raise ValueError(f"service must be one of {SUPPORTED_SERVICES}")
        self.source = source
        self.target = target
        self.service = service
        self._cache: dict[str, str] = {}
        self._translator = _build_backend(
            service, source, target, api_key=api_key, use_free_api=use_free_api
        )

    def translate(self, text: str) -> str:
        """Translate a single string, returning cached result when available."""
        text = text.strip()
        if not text:
            return text
        if text not in self._cache:
            self._cache[text] = self._translator.translate(text)
        return self._cache[text]

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate a list of strings, skipping already-cached entries."""
        uncached = [t for t in texts if t.strip() and t not in self._cache]
        if uncached:
            results = self._translator.translate_batch(uncached)
            for original, translated in zip(uncached, results):
                self._cache[original] = translated
        return [self._cache.get(t, t) for t in texts]
