import re
import hashlib

from utils_data_entitites import Entry, ValueList, InputFormat, Value, Version


def compute_hash(records):
    hash_obj = hashlib.md5()
    for row in records:
        # Convert each row to a string and encode it
        hash_obj.update(str(row).encode('utf-8'))
    return hash_obj.hexdigest()


def hash_id(name: str):
    m = hashlib.md5()
    m.update(name.encode("UTF8"))
    return str(int(m.hexdigest(), 16))[0:12]


def get_item_id(item):
    type = item['type']
    return str(item["id"]) + str(type) + str(item["guid"])


# Function to generate furigana in HTML format (support both > and ＞ for furigana)
def generate_furigana(text):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠ぁ-ゔ\s]+)[>＞][<＜]([一-龠ぁ-ゔ\s]+)[>＞]',
                  r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([一-龠ぁ-ゔ\s]{1})[<＜]([一-龠ぁ-ゔ\s]+)[>＞]',
                  r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))


def generate_furigana_custom(text, replaces):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠ぁ-ゔ\s]+)[>＞][<＜]([一-龠ぁ-ゔ\s]+)[>＞]',  replaces, str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([一-龠ぁ-ゔ\s]{1})[<＜]([一-龠ぁ-ゔ\s]+)[>＞]', replaces, str(text))


# Function to remove furigana, leaving only the main character
def remove_furigana(text):
    # Match exactly one character followed by furigana in <> or ＜＞ and remove the furigana part
    return re.sub(r'[<＜]([一-龠ぁ-ゔ\s]+)[>＞][<＜]([一-龠ぁ-ゔ\s]+)[>＞]', r'\1', str(text))


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




def sort_kanji_keys(structured_dataset):
    keys = list(structured_dataset.keys())
    keys.sort(key=lambda x: x)
    return keys


def sort_kanji_set(structured_dataset):
    # Actually, do not sort vocabulary, prefer the entry order in the data
    # for id in structured_dataset:
    #     data = structured_dataset[id]
    #     data.sort_vocabulary()
    return sort_kanji_keys(structured_dataset)


def find_kanji(all_data: dict, id: str):
    for dataset_name in all_data:
        dataset = all_data[dataset_name]
        kanji = dataset["content"].get(id)
        if kanji:
            return kanji, dataset
    return None, None


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


def process_row(row: list):
    """
    Process data row that comes in
    :param row: even-length row with data items to process: key-value column pairs
    :return: parsed row ready for further processing
    """
    # Todo solve extra
    item = Entry({"onyomi": ValueList(), "kunyomi": ValueList(), "usage": ValueList(), "extra": {}, "references": {},
                  "properties": [], "type": ""})

    if len(row) < 1:
        return None, False

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
        if type(value) == "string":
            value = value.strip()
        else:
            value = f"{value}"

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
                    print(f" --parse-- ERROR unsupported format {data_format} for {key}")
            else:
                print(f" --parse-- WARNING key starts with '[' but match format not found {key}")

        if key == 'kanji':
            if len(value) != 1:
                print(f" --parse-- ERROR kanji value '{value}' longer than 1")
            if item.get("kanji", False):
                print(f" --parse-- ERROR kanji redefinition, only one value allowed!")
            else:
                item["type"] = 'kanji'
                item["kanji"] = Value(value, key_significance, data_format)
                item["guid"] = str(hash(value))
        elif key == 'tango':
            item["type"] = 'tango'
            item["word"] = Value(value, key_significance, data_format)
            item["guid"] = str(hash(value))
        elif key == 'radical':
            item["type"] = 'radical'
            item["radical"] = Value(value, key_significance, data_format)
            item["guid"] = str(hash(value))
        elif key == 'setto':
            item["type"] = 'dataset'
            item["dataset"] = Value(value, key_significance, data_format)
            item["guid"] = str(hash(value))

        elif key == 'raberu':
            if value not in ["ichidan", "godan", "tadoushi", "jidoushi", "i", "na"]:
                print(" --parse-- Invalid value for vocab property: ", value)
            else:
                item["properties"].append(Value(value, key_significance, data_format))

        elif key == 'id':
            if key_significance > 0:
                print(" --parse-- Warning: ID cannot have lesser significance! Ignoring the property.", value)
            item["id"] = Value(Version(value), key_significance, data_format)
        elif key == "ids":
            if key_significance > 0:
                print(" --parse-- Warning: IDS cannot have lesser significance! Ignoring the property.", value)
            item["ids"] = Value(Version(value), key_significance, data_format)
        elif key == 'ref':
            # todo parse ref from its syntax
            values = value.split("-")
            if len(values) != 2:
                print(f" --parse-- ERROR reference '{value}' invalid syntax - ignoring!")
                continue

            name = values[0]
            id = values[1]

            ref = item["references"].get(name)
            if not ref:
                ref = []
                item["references"][name] = ref
            ref.append(id)

        elif key == 'onyomi':
            item["onyomi"].append(Value(value, key_significance, data_format))
        elif key == 'kunyomi':
            item["kunyomi"].append(Value(value, key_significance, data_format))
        elif key == 'imi':
            item["meaning"] = Value(value, key_significance, data_format)

        elif key == 'tsukaikata':
            item["usage"].append(Value(value, key_significance, data_format))

        else:
            # TODO does not support chaining
            item["extra"][original_key] = Value(value, key_significance, data_format)

    if not item.get("guid", False):
        print(" --parse-- IGNORES: invalid data:", row)
        return None, False

    item["guid"] = get_item_id(item)
    return item
