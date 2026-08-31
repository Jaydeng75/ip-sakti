import logging
from dataclasses import dataclass

import httpx

from config import settings

logger = logging.getLogger("ip-sakti.translation")

LANGUAGE_CODES = {
    "english": "eng_Latn",
    "assamese": "asm_Beng",
    "bengali": "ben_Beng",
    "bodo": "brx_Deva",
    "dogri": "doi_Deva",
    "gujarati": "guj_Gujr",
    "hindi": "hin_Deva",
    "kannada": "kan_Knda",
    "kashmiri": "kas_Arab",
    "konkani": "gom_Deva",
    "maithili": "mai_Deva",
    "malayalam": "mal_Mlym",
    "manipuri": "mni_Mtei",
    "marathi": "mar_Deva",
    "nepali": "npi_Deva",
    "odia": "ory_Orya",
    "punjabi": "pan_Guru",
    "sanskrit": "san_Deva",
    "santali": "sat_Olck",
    "sindhi": "snd_Arab",
    "tamil": "tam_Taml",
    "telugu": "tel_Telu",
    "urdu": "urd_Arab",
}


@dataclass(frozen=True)
class TranslationResult:
    text: str
    provider: str
    status: str
    source_language: str
    target_language: str
    model: str | None = None
    machine_translated: bool = False

    def public(self) -> dict[str, str | bool | None]:
        return {
            "provider": self.provider,
            "status": self.status,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "model": self.model,
            "machine_translated": self.machine_translated,
        }


def normalize_language(language: str) -> tuple[str, str]:
    name = language.strip().lower()
    if name not in LANGUAGE_CODES:
        supported = ", ".join(item.title() for item in LANGUAGE_CODES)
        raise ValueError(f"Unsupported language '{language}'. Supported languages: {supported}.")
    return name.title(), LANGUAGE_CODES[name]


async def translate_text(text: str, source_language: str, target_language: str) -> TranslationResult:
    source_name, source_code = normalize_language(source_language)
    target_name, target_code = normalize_language(target_language)
    if source_code == target_code:
        return TranslationResult(text, "none", "identity", source_name, target_name)
    if not settings.translation_enabled:
        return TranslationResult(text, "IndicTrans2", "disabled", source_name, target_name)

    try:
        timeout = httpx.Timeout(settings.translation_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.translation_url.rstrip('/')}/translate",
                json={
                    "texts": [text],
                    "source_language": source_code,
                    "target_language": target_code,
                },
            )
            response.raise_for_status()
            payload = response.json()
            translations = payload.get("translations", [])
            if len(translations) != 1 or not isinstance(translations[0], str):
                raise ValueError("Translation service returned an invalid response.")
            return TranslationResult(
                translations[0],
                "IndicTrans2",
                "translated",
                source_name,
                target_name,
                payload.get("model"),
                True,
            )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("IndicTrans2 translation unavailable: %s", exc)
        return TranslationResult(text, "IndicTrans2", "unavailable", source_name, target_name)
