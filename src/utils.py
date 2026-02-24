import functools
import re
import os
import json
import hashlib
from pathlib import Path

from utils_data_entitites import InputFormat, Value, Version, VocabEntry, RadicalEntry, KanjiEntry, \
    DatasetEntry, DataSubsetEntry


METADATA_FILE = "/misc/.file_order.json"


def short_uid(text: str, length=8):
    hash_obj = hashlib.sha256(text.encode('utf-8'))  # Hash the input string
    return hash_obj.hexdigest()[:length]


def sanitize_filename(name: str):
    return re.sub(r'\s', "_", str(name).strip())


def hash_id(name: str):
    m = hashlib.md5()
    m.update(name.encode("UTF8"))
    return str(int(m.hexdigest(), 16))[0:12]


def get_item_uid(item: dict):
    return remove_furigana(str(item["guid"]) + str(item['type']))


def order_file_list(file_list: list):
    cached_get_file_order = functools.lru_cache(None)(get_file_order)
    return sorted(file_list, key=cached_get_file_order)


def set_file_order(filename: str, order: int):
    directory = os.path.dirname(filename) or '.'
    metadata_path = os.path.join(directory, METADATA_FILE)

    # Load existing metadata
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metadata = {}

    metadata[filename] = order

    # Save metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def get_file_order(filename: str):
    directory = os.path.dirname(filename) or '.'
    metadata_path = os.path.join(directory, METADATA_FILE)

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return int(metadata.get(filename, float('inf')))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return float('inf')  # Default high value if missing


#### ON MATCHING FURIGANA #########
# We match using: [一-龠ぁ-ゔ0-9０-９々〆〇\s]
# 一-龠   all kanji
# ぁ-ゔ   all hiragana
# 々〆〇  extended kanji symbols
# 0-9    half-width numbers
# ０-９   full-width numbers
# \s     whitespace
###################################


# Function to generate furigana in HTML format (support both > and ＞ for furigana)
def generate_furigana(text):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞][<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]',
                  r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]{1})[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]',
                  r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))


def generate_furigana_custom(text, replaces):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞][<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]',  replaces, str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]{1})[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]', replaces, str(text))


# Function to remove furigana, leaving only the main character
def remove_furigana(text):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞][<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]', r'\1', str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]{1})[<＜]([一-龠々〆〇ぁ-ゔァ-ヴー0-9０-９\s]+)[>＞]', r'\1', str(text))


def retrieve_row_kanjialive_url(item):
    return f"https://app.kanjialive.com/{remove_furigana(item['kanji'])}"


def detect_bom(file_path):
    with open(file_path, 'rb') as file:
        # Read the first 4 bytes to check for BOM
        first_bytes = file.read(4)

    # Detect the BOM and return the appropriate encoding
    if first_bytes.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig"  # UTF-8 BOM
    elif first_bytes.startswith(b'\xff\xfe\x00\x00'):
        return "utf-32-le"  # UTF-32 Little Endian BOM
    elif first_bytes.startswith(b'\x00\x00\xfe\xff'):
        return "utf-32-be"  # UTF-32 Big Endian BOM
    elif first_bytes.startswith(b'\xff\xfe'):
        return "utf-16-le"  # UTF-16 Little Endian BOM
    elif first_bytes.startswith(b'\xfe\xff'):
        return "utf-16-be"  # UTF-16 Big Endian BOM
    else:
        return "utf-8"  # Default to UTF-8 if no BOM is found


# Function to create a GUID based on content (useful for avoiding duplicate cards)
def create_guid(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_or_crete_entry(ddict, key, default):
    node = ddict.get(key, None)
    if node is None:
        node = default
        ddict[key] = node
    return node


def structure_data_vocabulary_below_kanji(data):
    structured_data = {}
    for row in data:
        item = row
        if not item:
            continue

        id = str(item["id"])

        node = get_or_crete_entry(structured_data, id, {})
        ttype = item.get("type")
        if ttype == "kanji":
            structured_data[id] = {**node, **item}
        else:
            vocab = get_or_crete_entry(node, "vocabulary", [])
            vocab.append(item)
    return structured_data


def parse_ids(ids: str):
    id_list = ids.split(',')

    output = []
    for uid in id_list:
        output.append(uid.strip())
    return output


def dict_read_create(ddict, key, default):
    node = ddict.get(key)
    if node is None:
        node = default
        ddict[key] = node
    return node


def create_dataset_readme(file_list: list, set_name: str, item_name=None):
    """
    :param file_list:
    :param set_name:
    :param item_name: if set to none, the output is space-separated list, else bulletpoint names are used
    :return:
    """
    if not item_name and len(file_list) > 1:
        return (f"\n#### {set_name}\n" +
                "  ".join(map(lambda f: f"<a href=\"{f}\">{Path(f).stem}</a>", file_list)))

    if len(file_list) > 1:
        output = f"""
<details>
<summary>
{set_name}
</summary>
        """
        for file in file_list:
            output += f"\n  - <a href=\"{file}\">{item_name} {Path(file).stem}</a>\n"

        output += "</details>"
        return output
    if len(file_list) == 1:
        return f" - <a href=\"{file_list[0]}\">{set_name if item_name else Path(file_list[0]).stem}</a>\n"
    print("Warning: invalid dataset - no output files!", set_name, item_name)


def process_row(row: list):
    """
    Process data row that comes in
    :param row: even-length row with data items to process: key-value column pairs
    :return: parsed row ready for further processing
    """
    row = list(filter(bool, row))
    if len(row) < 1:
        return None

    if (len(row) % 2) == 1:
        print(" --parse-- IGNORES: invalid input: odd length", row)
        return None

    # First step: parse values, no meaning yet assumed
    item = {"onyomi": [], "kunyomi": [], "tsukaikata": [], "extra": {}, "references": {}, "raberu": []}
    for i in range(0, len(row), 2):
        key = row[i]
        if type(key) == "string":
            key = (row[i]).strip()
        else:
            key = f"{key}"
        original_key = key
        key = key.lower()
        if len(key) < 1:
            continue
        if key[0] == "$":
            key = key[1:len(key)]
        value = row[i + 1]
        if type(value) != "string":
            value = str(value)
        value = value.strip()

        key_significance = 0
        if key.endswith("-"):
            temp = key.rstrip('-')
            key_significance = len(key) - len(temp)
            key = temp

        data_format = InputFormat.PLAINTEXT

        if key.startswith("["):
            match = re.match(r'^\s*\[([^\]]*?)\]\s*', key)
            if match:
                cur_format = match.group(1).strip().lower()
                key = key[match.end():]
                original_key = original_key[match.end():]

                if cur_format == "md" or cur_format == "markdown":
                    data_format = InputFormat.MARKDOWN
                else:
                    print(f" --parse-- ERROR unsupported format {data_format} for {key}", row)
            else:
                print(f" --parse-- WARNING key starts with '[' but match format not found {key}", row)

        if key == 'kanji':
            if len(value) != 1:
                print(f" --parse-- ERROR kanji value '{value}' longer than 1", row)
            if item.get("kanji", False):
                print(f" --parse-- ERROR kanji redefinition, only one value allowed!", row)
            else:
                item["kanji"] = Value(value, key_significance, data_format)
        elif key == 'raberu':
            if value not in ["ichidan", "godan", "tadoushi", "jidoushi", "suru", "i", "na", "fukisokuna", "meishi"]:
                print(" --parse-- Invalid value", value, "for vocab property", row)
            else:
                item["raberu"].append(Value(value, key_significance, data_format))
        elif key == 'id':
            if key_significance > 0:
                print(" --parse-- Warning: ID cannot have lesser significance! Ignoring the property.", row)
            item["id"] = Value(Version(value), 0, data_format)
        elif key == "subid":
            item["subid"] = Value(Version(value), key_significance, data_format)
        elif key == "ids":
            if key_significance > 0:
                print(" --parse-- Warning: IDS cannot have lesser significance! Ignoring the property.", row)
                # todo optional should extend existing
            item["ids"] = Value(Version(value), key_significance, data_format)
        elif key == 'ref':
            # todo parse ref from its syntax
            values = value.split("-")
            if len(values) != 2:
                print(f" --parse-- ERROR reference '{value}' invalid syntax - ignoring!", row)
                continue

            name = values[0]
            id = values[1]

            ref = item["references"].get(name)
            if not ref:
                ref = []
                item["references"][name] = ref
            ref.append(id)

        elif key in ['onyomi', 'kunyomi']:
            # with kanji readings, replace dot with middle dot
            values = map(lambda x: Value(x.strip().replace('.', '・'), key_significance, data_format),
                         filter(None, re.split(r"[,、]+", value)))
            item[key].extend(values)
        elif key in ['tsukaikata']:
            item[key].append(Value(value, key_significance, data_format))
        elif key in ['junban']:
            item[key] = Value(int(value), key_significance, data_format)
        elif key in ['imi', 'tango', 'radical', 'setto', 'kijutsu']:
            item[key] = Value(value, key_significance, data_format)
        else:
            # TODO does not support chaining
            item["extra"][original_key] = Value(value, key_significance, data_format)

    # Second step, derive meaning
    if item.get("tango"):
        if not item.get("imi") or not item.get("kanji"):
            print(" --parse-- IGNORES: tango", item.get("tango"), "does not specify required field 'imi' or 'kanji'", row)
            return None
        output = VocabEntry()
    elif item.get("kanji"):
        if not item.get("imi"):
            # Keep the kanji in play since it still defines the derived property
            # print(" --parse-- WARNING: kanji", item.get("kanji"), "does not specify required field 'imi'")
            item["kanji"].significance += 1
        output = KanjiEntry()
    elif item.get("radical"):
        output = RadicalEntry()
    elif item.get("subid"):
        output = DataSubsetEntry()
    elif item.get('setto'):
        output = DatasetEntry()
    else:
        print(" --parse-- IGNORES: invalid input: unknown type", row)
        return None

    output.fill(item)
    output["guid"] = get_item_uid(output)
    return output
