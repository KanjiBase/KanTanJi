"""Centralized UI translations for all generators and the master README.

Every user-facing string outside of `data/radicals/` (which has its own per-
language JSON convention) is looked up here, gated by `config.LANGUAGE`.

Short strings live in the `TRANSLATIONS` dict below, namespaced by source
module (`T['html_generator']['radical_label']`). Long-form markdown blocks
(the project README and the per-dataset README section) live in
`data/i18n/*.md` and are loaded with `load_template(name)`.

Fallback is unified on `cs` (the project's primary audience). The separate
`FALLBACK_LANG = "en"` in `radical_index.py` is for radical *data* and is
intentionally distinct.
"""
from pathlib import Path

import config


REPO_ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = REPO_ROOT / "data" / "i18n"
FALLBACK = "cs"


TRANSLATIONS = {
    "cs": {
        "anki": {
            "usage_label": "使＜つか＞い方＜かた＞",
            "correct_label": "Správně",
            "instruction_outline": "Napiš dle předlohy.",
            "instruction_recall": "Napiš z paměti.",
            "mistakes_prefix": "Chyb: ",
            "done_prefix": "Hotovo ✓  Chyb: ",
            "result_prefix": "Výsledek ✓  Chyb: ",
            "unfinished_with_total": "Nedokončeno: {drawn}/{total} tahů",
            "unfinished_no_total": "Nedokončeno: {drawn} tahů",
            "mistakes_unknown": "Počet chyb neznámý.",
            "no_drawing": "Žádná kresba.",
            "cannot_render": "Nelze vykreslit.",
            "stroke_data_missing": "Chybí data tahů pro: ",
            "package_prefix": "Balíček",
            "basic_pack_label": "základní",
            "advanced_pack_label": "rozšiřující",
        },
        "html_generator": {
            "required_vocab": "Povinná slovíčka",
            "extended_vocab": "Budou v sadě / Rozšiřující",
            "radical_label": "Radikál",
            "show_furigana": "Ukazovat furiganu",
            "always_show_sentences": "Vždy ukazovat věty",
            "show_vocab_props": "Ukazovat vlastnosti slovíček",
            "meaning_label": "Význam",
            "kanji_pages_for": "Kanji Stránky {name}",
        },
        "utils_html": {
            "ichidan_title": "ichidan (..る)",
            "ichidan_detail": "Sloveso má pouze jeden tvar, při skloňování většinou odpadá ~る přípona.",
            "godan_title": "godan (..う)",
            "godan_detail": "Sloveso má pět tvarů jako je pět samohlásek, pro skloňování mají dle typu koncovky různá pravidla.",
            "jidoushi_title": "netranzitivní",
            "jidoushi_detail": "neboli 'じどうし', sloveso popisuje podmět (budova se staví)",
            "tadoushi_title": "tranzitivní",
            "tadoushi_detail": "neboli 'たどうし', sloveso může popisovat předmět (postavili budovu)",
            "i_adj_title": "い - příd. jméno",
            "i_adj_detail": "Koncovka ~い buď zůstává, nebo se nahrazuje např. v záporu za ~くない.",
            "na_adj_title": "な - příd. jméno",
            "na_adj_detail": "Většinou koncovka ~な odpadá (např. při použití s 'です'), pokud se neváže na podstatné jméno.",
            "suru_title": "する sloveso",
            "suru_detail": "Nepravidelná slovesa se chovají podobně dle する tvaru.",
            "fukisokuna_title": "nepravidelné čtení",
            "fukisokuna_detail": "Čtení nelze odvodit ze zápisu kanji.",
            "meishi_title": "podst. jméno",
            "meishi_detail": "Podstatná jména tvoří drtivou většinu japonštiny, label je ukazován jen u slovíček, kde to nemusí být zřejmé.",
        },
        "pdf_generator": {
            "pdf_pages_for": "PDF Stránky {name}",
        },
        "html_pdf_generator": {
            "pdf_pages_for": "PDF Stránky {name}",
        },
        "sentences_pdf_generator": {
            "pdf_pages_for": "PDF Stránky {name}",
        },
        "json_generator": {
            "data_pack_for": "JSON Datový Balíček {name}",
        },
        "main": {
            "available_sets_header": "Dostupné Sady",
            "available_sets_subheader": "Trénování Kanji",
            "no_datasets_defined": "Nejsou žádné dostupné sady. Dataset není definován!",
        },
    },
    "en": {
        "anki": {
            "usage_label": "Usage",
            "correct_label": "Correct",
            "instruction_outline": "Trace the outline.",
            "instruction_recall": "Write from memory.",
            "mistakes_prefix": "Mistakes: ",
            "done_prefix": "Done ✓  Mistakes: ",
            "result_prefix": "Result ✓  Mistakes: ",
            "unfinished_with_total": "Unfinished: {drawn}/{total} strokes",
            "unfinished_no_total": "Unfinished: {drawn} strokes",
            "mistakes_unknown": "Mistakes count unknown.",
            "no_drawing": "No drawing.",
            "cannot_render": "Cannot render.",
            "stroke_data_missing": "Stroke data missing for: ",
            "package_prefix": "Package",
            "basic_pack_label": "basic",
            "advanced_pack_label": "advanced",
        },
        "html_generator": {
            "required_vocab": "Required vocabulary",
            "extended_vocab": "In set / Extended",
            "radical_label": "Radical",
            "show_furigana": "Show furigana",
            "always_show_sentences": "Always show sentences",
            "show_vocab_props": "Show vocabulary properties",
            "meaning_label": "Meaning",
            "kanji_pages_for": "Kanji Pages for {name}",
        },
        "utils_html": {
            "ichidan_title": "ichidan (..る)",
            "ichidan_detail": "Verb has a single form; the ~る suffix is usually dropped on conjugation.",
            "godan_title": "godan (..う)",
            "godan_detail": "Verb has five forms (one per vowel); conjugation rules depend on the ending.",
            "jidoushi_title": "intransitive",
            "jidoushi_detail": "\"じどうし\"; the verb describes the subject (the building is being built)",
            "tadoushi_title": "transitive",
            "tadoushi_detail": "\"たどうし\"; the verb takes an object (they built the building)",
            "i_adj_title": "い-adjective",
            "i_adj_detail": "The ~い ending stays or is replaced (e.g. ~くない in the negative).",
            "na_adj_title": "な-adjective",
            "na_adj_detail": "The ~な ending is usually dropped (e.g. with です) except when modifying a noun.",
            "suru_title": "する verb",
            "suru_detail": "Irregular verbs conjugate similarly to する.",
            "fukisokuna_title": "irregular reading",
            "fukisokuna_detail": "Reading cannot be derived from the kanji spelling.",
            "meishi_title": "noun",
            "meishi_detail": "Nouns dominate Japanese; this label appears only where the part of speech may not be obvious.",
        },
        "pdf_generator": {
            "pdf_pages_for": "PDF Pages for {name}",
        },
        "html_pdf_generator": {
            "pdf_pages_for": "PDF Pages for {name}",
        },
        "sentences_pdf_generator": {
            "pdf_pages_for": "PDF Pages for {name}",
        },
        "json_generator": {
            "data_pack_for": "JSON Data Pack for {name}",
        },
        "main": {
            "available_sets_header": "Available Sets",
            "available_sets_subheader": "Kanji Training",
            "no_datasets_defined": "No sets available. Dataset is not defined!",
        },
    },
}


LANGUAGE = getattr(config, "LANGUAGE", FALLBACK)
T = TRANSLATIONS.get(LANGUAGE, TRANSLATIONS[FALLBACK])


def tr(module, key):
    """Per-key fallback: return the active-language value, or the FALLBACK
    one if a key is missing from the active language. Lets us ship a third
    language with partial coverage without crashes."""
    value = T.get(module, {}).get(key)
    if value is not None:
        return value
    return TRANSLATIONS[FALLBACK][module][key]


def load_template(name, lang=None):
    """Load `data/i18n/<name>.<lang>.md` (falls back to FALLBACK language).
    Templates are returned raw; callers may use `str.format(**kwargs)` for
    placeholder substitution. Don't pass the result through an f-string."""
    if lang is None:
        lang = LANGUAGE
    path = I18N_DIR / f"{name}.{lang}.md"
    if not path.exists():
        path = I18N_DIR / f"{name}.{FALLBACK}.md"
    return path.read_text(encoding="utf-8")
