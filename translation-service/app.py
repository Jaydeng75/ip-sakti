import gc
import logging
import re
import threading
from collections import OrderedDict
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ip-sakti.indictrans2")

ENGLISH = "eng_Latn"
INDIC_LANGUAGE_CODES = {
    "asm_Beng",
    "ben_Beng",
    "brx_Deva",
    "doi_Deva",
    "gom_Deva",
    "guj_Gujr",
    "hin_Deva",
    "kan_Knda",
    "kas_Arab",
    "kas_Deva",
    "mai_Deva",
    "mal_Mlym",
    "mni_Beng",
    "mni_Mtei",
    "mar_Deva",
    "npi_Deva",
    "ory_Orya",
    "pan_Guru",
    "san_Deva",
    "sat_Olck",
    "snd_Arab",
    "snd_Deva",
    "tam_Taml",
    "tel_Telu",
    "urd_Arab",
}
SUPPORTED_LANGUAGE_CODES = INDIC_LANGUAGE_CODES | {ENGLISH}
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।])\s+")


class Settings(BaseSettings):
    hf_token: str | None = None
    en_indic_model: str = "ai4bharat/indictrans2-en-indic-dist-200M"
    indic_en_model: str = "ai4bharat/indictrans2-indic-en-dist-200M"
    en_indic_revision: str = "main"
    indic_en_revision: str = "main"
    max_loaded_models: int = Field(default=1, ge=1, le=2)
    max_chunk_characters: int = Field(default=700, ge=100, le=2_000)
    max_source_tokens: int = Field(default=256, ge=64, le=1_024)
    max_output_tokens: int = Field(default=256, ge=64, le=1_024)

    model_config = SettingsConfigDict(env_prefix="INDICTRANS_", extra="ignore")


settings = Settings()


class TranslationRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=16)
    source_language: str
    target_language: str


class TranslationResponse(BaseModel):
    translations: list[str]
    provider: str = "IndicTrans2"
    model: str
    source_language: str
    target_language: str
    machine_translated: bool = True


def split_text(text: str, limit: int) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return [""]
    sentences = SENTENCE_BOUNDARY.split(stripped)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        while len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            split_at = sentence.rfind(" ", 0, limit + 1)
            if split_at < limit // 2:
                split_at = limit
            chunks.append(sentence[:split_at].strip())
            sentence = sentence[split_at:].strip()
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def validate_route(source_language: str, target_language: str) -> None:
    if source_language not in SUPPORTED_LANGUAGE_CODES or target_language not in SUPPORTED_LANGUAGE_CODES:
        raise ValueError("Unknown FLORES-200 language code.")
    if source_language == target_language:
        return
    if source_language != ENGLISH and target_language != ENGLISH:
        return
    if source_language == ENGLISH and target_language not in INDIC_LANGUAGE_CODES:
        raise ValueError("The target language is not supported by the English-to-Indic model.")
    if target_language == ENGLISH and source_language not in INDIC_LANGUAGE_CODES:
        raise ValueError("The source language is not supported by the Indic-to-English model.")


class ModelManager:
    def __init__(self) -> None:
        self._models: OrderedDict[str, tuple[Any, Any, Any, str]] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _model_details(source_language: str, target_language: str) -> tuple[str, str]:
        if source_language == ENGLISH and target_language in INDIC_LANGUAGE_CODES:
            return settings.en_indic_model, settings.en_indic_revision
        if source_language in INDIC_LANGUAGE_CODES and target_language == ENGLISH:
            return settings.indic_en_model, settings.indic_en_revision
        raise ValueError("Indic-to-Indic translation must be routed through English.")

    def _load(self, source_language: str, target_language: str) -> tuple[Any, Any, Any, str]:
        model_id, revision = self._model_details(source_language, target_language)
        cache_key = f"{model_id}@{revision}"
        if cache_key in self._models:
            loaded = self._models.pop(cache_key)
            self._models[cache_key] = loaded
            return loaded

        try:
            import torch
            from IndicTransToolkit import IndicProcessor
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("IndicTrans2 runtime dependencies are not installed.") from exc

        logger.info("Loading IndicTrans2 model %s at revision %s", model_id, revision)
        model_kwargs: dict[str, Any] = {
            "revision": revision,
            "token": settings.hf_token or None,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            model_kwargs["torch_dtype"] = torch.float16
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            token=settings.hf_token or None,
            trust_remote_code=True,
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id, **model_kwargs).to(device)
        model.eval()
        loaded = (model, tokenizer, IndicProcessor(inference=True), device)
        self._models[cache_key] = loaded
        while len(self._models) > settings.max_loaded_models:
            _, evicted = self._models.popitem(last=False)
            del evicted
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return loaded

    def _translate_direction(self, texts: list[str], source_language: str, target_language: str) -> tuple[list[str], str]:
        model, tokenizer, processor, device = self._load(source_language, target_language)
        model_id, _ = self._model_details(source_language, target_language)
        import torch

        prepared = processor.preprocess_batch(texts, src_lang=source_language, tgt_lang=target_language)
        batch = tokenizer(
            prepared,
            truncation=True,
            padding="longest",
            max_length=settings.max_source_tokens,
            return_tensors="pt",
            return_attention_mask=True,
        ).to(device)
        with torch.inference_mode():
            generated = model.generate(
                **batch,
                max_length=settings.max_output_tokens,
                num_beams=5,
                do_sample=False,
            )
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return processor.postprocess_batch(decoded, lang=target_language), model_id

    def translate(self, texts: list[str], source_language: str, target_language: str) -> tuple[list[str], str]:
        validate_route(source_language, target_language)
        if source_language == target_language:
            return texts, "identity"
        chunk_groups = [split_text(text, settings.max_chunk_characters) for text in texts]
        flat_chunks = [chunk for group in chunk_groups for chunk in group]
        with self._lock:
            if source_language != ENGLISH and target_language != ENGLISH:
                english, first_model = self._translate_direction(flat_chunks, source_language, ENGLISH)
                translated, second_model = self._translate_direction(english, ENGLISH, target_language)
                model_id = f"{first_model} -> {second_model}"
            else:
                translated, model_id = self._translate_direction(flat_chunks, source_language, target_language)
        rebuilt: list[str] = []
        offset = 0
        for group in chunk_groups:
            rebuilt.append(" ".join(translated[offset : offset + len(group)]).strip())
            offset += len(group)
        return rebuilt, model_id


manager = ModelManager()
app = FastAPI(title="IP-SAKTI IndicTrans2 Service", version="1.0.0")


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str | bool]:
    return {
        "status": "ready-for-model-load",
        "hf_token_configured": bool(settings.hf_token),
        "note": "Model access is verified on the first translation request.",
    }


@app.get("/languages")
def languages() -> dict[str, list[str]]:
    return {"language_codes": sorted(SUPPORTED_LANGUAGE_CODES)}


@app.post("/translate", response_model=TranslationResponse)
def translate(payload: TranslationRequest) -> TranslationResponse:
    if any(len(text) > 12_000 for text in payload.texts):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Each text is limited to 12,000 characters.")
    try:
        translations, model_id = manager.translate(payload.texts, payload.source_language, payload.target_language)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("IndicTrans2 inference failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IndicTrans2 is unavailable. Verify model access, token, memory and network connectivity.",
        ) from exc
    return TranslationResponse(
        translations=translations,
        model=model_id,
        source_language=payload.source_language,
        target_language=payload.target_language,
        machine_translated=model_id != "identity",
    )
