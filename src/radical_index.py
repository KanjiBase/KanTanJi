"""Build the kanji→RadicalEntry index from bundled data + per-language translations.

Bundled data lives in `data/radicals/`:
- `kangxi-214.json` — the 214 Kangxi radicals with stroke counts, readings, and
  an English meaning baked in as `meaning_en` (used as fallback).
- `kangxi-214.<lang>.json` — flat `{number_str: meaning}` translation files,
  one per language. The active language is selected by `config.LANGUAGE`.
- `generate/kanjidic2.xml` (or `.xml.gz`) — the upstream KANJIDIC2 dump from
  EDRDG. Parsed directly each run to extract the classical radical number per
  kanji (~0.3 s for ~13k characters). No derived JSON is kept.
"""
import gzip
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from utils_data_entitites import RadicalEntry
from config import LANGUAGE


REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = REPO_ROOT / "data" / "radicals"
KANGXI_PATH = BUNDLE_DIR / "kangxi-214.json"
KANJIDIC2_DIR = BUNDLE_DIR / "generate"
KANJIDIC2_CANDIDATES = ("kanjidic2.xml", "kanjidic2.xml.gz")
FALLBACK_LANG = "en"

# Cache the kanji→radical map across calls within a single process so multi-
# dataset builds don't re-parse KANJIDIC2 each time.
_KANJI_TO_RADICAL_CACHE = None


def _translations_path(lang):
    return BUNDLE_DIR / f"kangxi-214.{lang}.json"


def _kanjidic2_path():
    for name in KANJIDIC2_CANDIDATES:
        p = KANJIDIC2_DIR / name
        if p.exists():
            return p
    raise FileNotFoundError(
        f"KANJIDIC2 source not found. Place kanjidic2.xml or kanjidic2.xml.gz "
        f"under {KANJIDIC2_DIR} (see data/radicals/README.md for the upstream URL)."
    )


def _open_kanjidic2(path):
    return gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")


def _parse_kanji_to_radical(path):
    out = {}
    with _open_kanjidic2(path) as f:
        for _, elem in ET.iterparse(f, events=("end",)):
            if elem.tag != "character":
                continue
            literal = elem.findtext("literal")
            rad = elem.find(".//rad_value[@rad_type='classical']")
            if literal and rad is not None and rad.text:
                try:
                    out[literal] = int(rad.text)
                except ValueError:
                    pass
            elem.clear()
    return out


def load_kanji_to_radical():
    """Return the kanji→Kangxi-number mapping, parsing KANJIDIC2 on first call."""
    global _KANJI_TO_RADICAL_CACHE
    if _KANJI_TO_RADICAL_CACHE is None:
        path = _kanjidic2_path()
        _KANJI_TO_RADICAL_CACHE = _parse_kanji_to_radical(path)
    return _KANJI_TO_RADICAL_CACHE


def load_bundled():
    with open(KANGXI_PATH, "r", encoding="utf-8") as f:
        kangxi = json.load(f)
    bundle_by_num = {int(k): v for k, v in kangxi.items()}
    kanji_to_num = load_kanji_to_radical()
    return bundle_by_num, kanji_to_num


def load_translations(lang):
    """Return (translations_by_num, effective_lang).

    Looks up `data/radicals/kangxi-214.<lang>.json`. Falls back to English if
    the requested file is missing.
    """
    path = _translations_path(lang)
    effective = lang
    if not path.exists():
        if lang != FALLBACK_LANG:
            print(f" --radicals-- No translations for language {lang!r}; falling back to {FALLBACK_LANG!r}.")
        path = _translations_path(FALLBACK_LANG)
        effective = FALLBACK_LANG
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}, effective


def build_radical_index(kanji_dictionary, lang=None):
    """Return (radical_index, stats).

    radical_index: dict[kanji_char -> RadicalEntry], one entry per kanji in
    `kanji_dictionary` that has a known Kangxi radical.
    """
    bundle_by_num, kanji_to_num = load_bundled()
    if lang is None:
        lang = LANGUAGE
    translations, effective_lang = load_translations(lang)

    translated = sum(1 for n in bundle_by_num if n in translations)
    total = len(bundle_by_num)
    if translated < total:
        print(f" --radicals-- Translations [{effective_lang}]: {translated}/{total} "
              f"({total - translated} missing — English fallback used)")
    else:
        print(f" --radicals-- Translations [{effective_lang}]: {translated}/{total}")

    radical_index = {}
    missing = []
    for kanji_char in kanji_dictionary.keys():
        num = kanji_to_num.get(kanji_char)
        if num is None:
            missing.append(kanji_char)
            continue
        bundled = bundle_by_num.get(num)
        if bundled is None:
            print(f" --radicals-- Kanji {kanji_char!r} maps to unknown Kangxi number {num}")
            continue
        merged = dict(bundled)
        # imi = localised meaning, with English fallback
        merged["imi"] = translations.get(num) or bundled.get("meaning_en")
        entry = RadicalEntry()
        entry.fill(merged)
        radical_index[kanji_char] = entry

    stats = {
        "missing_kanji": missing,
        "language": effective_lang,
        "translated": translated,
        "total": total,
        "covered_kanji": len(radical_index),
    }
    return radical_index, stats


def count_legacy_refs(kanji_dictionary):
    """Count kanji rows that still carry a legacy `ref: radical-N` reference."""
    count = 0
    for entry in kanji_dictionary.values():
        refs = entry.get("references", {}) if isinstance(entry, dict) else {}
        if refs.get("radical"):
            count += 1
    return count
