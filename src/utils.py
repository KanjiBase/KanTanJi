import re
import os
import json
import time
import hashlib
from copy import copy


class Entry(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_equal(self, target, significance_level=0):
        target = self[target]
        if type(target) == ValueList:
            return target.get_equal(significance_level)
        if type(target) == Value and target.significance == significance_level:
            return Value
        return None

    def get_below(self, target, below_significance):
        target = self[target]
        if type(target) == ValueList:
            return target.get_equal(below_significance)
        if type(target) == Value and target.significance >= below_significance:
            return Value
        return None

class Value:
    def __init__(self, value, significance=0):
        self.value = value
        self.significance = significance

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"Value({repr(self.value)})"

    def __bool__(self):
        return bool(self.value)


class ValueList(list):
    def __init__(self, values=None):
        # Initialize the list with optional values
        super().__init__(values or [])

    def get_equal(self, significance_level=0):
        return ValueList(filter(lambda x: x.significance == significance_level, self))

    def get_below(self, below_significance):
        return ValueList(filter(lambda x: x.significance >= below_significance, self))

    def join(self, separator):
        return separator.join(str(x) for x in self)

    def __copy__(self):
        return self.__class__(copy(self))


def compute_hash(records):
    hash_obj = hashlib.md5()
    for row in records:
        # Convert each row to a string and encode it
        hash_obj.update(str(row).encode('utf-8'))
    return hash_obj.hexdigest()


# Function to generate furigana in HTML format (support both > and ＞ for furigana)
def generate_furigana(text):
    # First match any pairs and replace them as whole
    text = re.sub(r'[<＜]([一-龠ぁ-ゔ\s]+)[>＞][<＜]([一-龠ぁ-ゔ\s]+)[>＞]', r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return  re.sub(r'([一-龠ぁ-ゔ\s]{1})[<＜]([一-龠ぁ-ゔ\s]+)[>＞]', r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', str(text))


# Function to remove furigana, leaving only the main character
def remove_furigana(text):
    # Match exactly one character followed by furigana in <> or ＜＞ and remove the furigana part
    return re.sub(r'[<>＜＞]([^/<>＜＞]+)[<>＜＞]', r'\1', str(text))


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
        (item, _) = row
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


class HashGuard:
    def __init__(self, context_name):
        self.hash_file_path = f"misc/update_guard_{context_name}.json"
        if os.path.exists(self.hash_file_path):
            with open(self.hash_file_path, 'r') as f:
                self.hashes = json.load(f)
        else:
            self.hashes = {}
        self.stamp = time.time()

    def get(self, key, name):
        item = self.hashes.get(key, None)
        if item is not None:
            item["stamp"] = self.stamp
            if item["name"] != name:
                item["hash"] = ""
        return item

    def update(self, key, name, hash_value):
        item = self.hashes.get(key, None)
        if item and item["name"] != name:
            # If exists & renamed, add outdated entry so it gets cleaned
            self.hashes[f"{key}_{time.time()}"] = {
                "name": item["name"],
                "hash": item["hash"],
                "stamp": 0
            }

        self.hashes[key] = {
            "name": name,
            "hash": hash_value,
            "stamp": self.stamp
        }

    def for_entries(self, clbck):
        for key in self.hashes:
            item = self.hashes[key]
            if item["stamp"] != self.stamp:
                clbck(item, True)
                del self.hashes[key]
            else:
                clbck(item, False)

    def save(self):
        with open(self.hash_file_path, "w") as f:
            json.dump(self.hashes, f)
