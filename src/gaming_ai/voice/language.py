

class LanguageDetector:
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "ur": "Urdu",
        "mr": "Marathi",
        "gu": "Gujarati",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
    }

    def __init__(self) -> None:
        self._fallback = "en"

    def normalize(self, language_code: str | None) -> str:
        if language_code is None:
            return self._fallback

        code = language_code.lower().strip()

        if code in self.SUPPORTED_LANGUAGES:
            return code

        short = code.split("-")[0] if "-" in code else code
        if short in self.SUPPORTED_LANGUAGES:
            return short

        logger = __import__("logging").getLogger(__name__)
        logger.warning("Unrecognized language code %r, falling back to en", language_code)
        return self._fallback

    def is_hindi(self, language_code: str) -> bool:
        return self.normalize(language_code) == "hi"

    def is_code_switched(self, text: str) -> bool:
        import re

        devanagari = bool(re.search(r"[\u0900-\u097F]", text))
        latin = bool(re.search(r"[a-zA-Z]", text))
        return devanagari and latin
