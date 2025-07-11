import genanki
import hashlib
import uuid
import markdown

from utils import generate_furigana, retrieve_row_kanjialive_url, sanitize_filename
from utils_data_entitites import InputFormat
from utils_html import parse_item_props_html

import json

def export_kanji_to_json(key, data):
    keys = data["order"]
    content = data["content"]

    result = []

    for k in keys:
        item = content[k]
        if item.get("kanji").significance > 0:
            continue

        kanji_entry = {
            "kanji": str(item["kanji"]),
            "kunyomi": ", ".join(map(str, item.get("kunyomi").get_equal(0))) if item.get("kunyomi").get_equal(0) else "",
            "onyomi": ", ".join(map(str, item.get("onyomi").get_equal(0))) if item.get("onyomi").get_equal(0) else "",
            "vocab": []
        }

        for vocab_item in item.vocabulary():
            kanji_entry["vocab"].append({
                "tango": vocab_item["tango"],
                "imi": vocab_item["imi"]
            })

        result.append(kanji_entry)

    return result

def save_json(key, data, file):
    with open(file, "w", encoding="UTF-8") as f:
        json.dump(data, f, ensure_ascii=False)


def generate(key, data, metadata, folder_getter, is_debug_run):
    # Anki packs only read data, so if not modified do not re-generate
    if not data["modified"] and not is_debug_run:
        return False
    anki = export_kanji_to_json(key, data)

    if not is_debug_run:
        save_json(key, anki, f"{folder_getter(key)}/{sanitize_filename(key)}.json")
    return True
