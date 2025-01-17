import re
import os
import json
import time
import shutil
import traceback
import hashlib
from copy import copy
from enum import Enum

from config import VERSION


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

    def __repr__(self):
        return f"Entry({super().__repr__()})"


class InputFormat(Enum):
    PLAINTEXT = 1
    MARKDOWN = 2


class Value:
    def __init__(self, value, significance=0, format=InputFormat.PLAINTEXT):
        self.value = value
        self.format = format
        self.significance = significance

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"Value{'-' * self.significance}({repr(self.value)})"

    def __bool__(self):
        return bool(self.value)


class Version:
    def __init__(self, value):
        # TODO nice printing fails reference comparison on IDs :/
        # self.value = str(value).split(".")
        self.value = value

    def __str__(self):
        return str(self.value)
        # return ". ".join(self.value)

    def __repr__(self):
        return f"Version({repr(self.value)})"

    def __bool__(self):
        return bool(len(self.value))

    def __eq__(self, other):
        return str(self.value) == str(other)


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


class KanjiEntry(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vocab = []

    def add_vocabulary_entry(self, value):
        if not isinstance(value, dict) or not value.get("word"):
            raise ValueError("Argument must be a tango dict.")
        self._vocab.append(value)

    def vocabulary(self):
        return self._vocab

    def set_context_id(self, context_id, id):
        self[f"_id-{context_id}_"] = id

    def get_context_id(self, context_id):
        return self.get(f"_id-{context_id}_")

    def sort_vocabulary(self):
        self._vocab.sort(key=lambda x: str(x["id"]) + str(x["word"]))

    def set_kanji(self, other_dict):
        """Extends the dictionary with key-value pairs from another dictionary."""
        if not isinstance(other_dict, dict) or not other_dict.get("kanji"):
            raise TypeError("Argument must be a kanji dict.")
        for key, value in other_dict.items():
            self[key] = value

    # def __copy__(self):
    #     new_instance = type(self)(self)
    #     # Ensure vocab is also copied, we will modify the significance levels
    #     new_instance._vocab = [copy(vocab_entry) for vocab_entry in self._vocab]
    #     return new_instance


class DataSet:
    _processors = []

    def __init__(self, parent_context_id, context_name=None):
        if context_name is None:
            self.parent_context_id = parent_context_id
            self.context_name = parent_context_id
        else:
            self.context_name = context_name
            self.parent_context_id = parent_context_id
        self.data = {}
        self.default = False

    def set_is_default(self):
        self.default = True

    @staticmethod
    def register_processor(name: str, processor):
        DataSet._processors.append((name, processor))

    def adjust_vocabulary_significance(self, kanji_dictionary):
        # Here we deduct significance levels automatically for vocabulary entries, these
        # are dependent on whether they contain already learnt kanji
        kanji_regex = r'[\u4e00-\u9faf]|[\u3400-\u4dbf]'
        for dataset_name in self.data:
            dataset_spec = self.data[dataset_name]
            dataset = dataset_spec["content"]
            for kanji_id in dataset:
                kanji = dataset[kanji_id]

                kanji_id = kanji.get_context_id(self.parent_context_id)
                # Find last in this set
                last_kanji_id = dataset_spec["order"][-1]
                last_kanji_id = int(str(dataset[last_kanji_id]["id"]))

                for vocab in kanji.vocabulary():
                    try:
                        match_len = 0
                        match = re.findall(kanji_regex, str(vocab["word"]))
                        for m in match:
                            contains_kanji = kanji_dictionary.get(m)
                            contains_kanji_id = None if contains_kanji is None \
                                else contains_kanji.get_context_id(self.parent_context_id)

                            if contains_kanji_id is None:
                                match_len = None
                                break
                            if contains_kanji_id <= kanji_id:
                                match_len = match_len + 1
                            elif contains_kanji_id > last_kanji_id:
                                match_len = None
                                break

                        if match_len is None:
                            vocab["word"].significance = 2
                        elif match_len == len(match):
                            vocab["word"].significance = 0
                        else:
                            vocab["word"].significance = 1

                    except Exception as e:
                        vocab["_used_kanjis_"] = []
                        print("Error when dealing with vocab item in Kanji", kanji_id,
                              "skipping significance modification...",
                              e)



    def process(self, metadata, guard):
        for proc_name, processor in DataSet._processors:
            for key in self.data:
                data_spec = self.data[key]
                name = data_spec["name"]
                output_path = guard.processing_file_root(data_spec["id"]) \
                    if self.default else \
                    guard.complementary_processing_file_root(data_spec["id"])

                try:
                    if processor(name, data_spec, metadata, lambda _: output_path):
                        print(f"[{name}]  {proc_name} - generated.")
                    else:
                        print(f"[{name}]  {proc_name} - unchanged.")
                except Exception as e:
                    print(f"Failed to write file to ", output_path, e)
                    print(traceback.format_exc())


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
        """
        Update the hash record of source file, this has no 'context_name'
        for complementary datasets, set_complementary_record is to be used.
        """
        item = self.hashes.get(key, None)
        if item and item["name"] != name:
            # If exists & renamed, add outdated entry so it gets cleaned
            self.hashes[f"{key}_{time.time()}"] = {
                "name": item["name"],
                "context_name": None,
                "hash": item["hash"],
                "stamp": 0,
                "version": VERSION
            }

        self.hashes[key] = {
            "name": name,
            "context_name": None,
            "hash": hash_value,
            "stamp": self.stamp,
            "version": VERSION
        }

    def invalidate_all(self):
        for key in self.hashes:
            item = self.hashes[key]
            item["stamp"] = ""

    def for_each_entry(self, clbck):
        outdated_hashes = []
        for key in self.hashes:
            item = self.hashes[key]
            if item["stamp"] != self.stamp:
                outdated_hashes.append(key)
            else:
                clbck(item, False)

        print("Cleaning outdated:", outdated_hashes)
        for key in outdated_hashes:
            item = self.hashes[key]
            clbck(item, True)
            del self.hashes[key]

    def save(self):
        with open(self.hash_file_path, "w") as f:
            json.dump(self.hashes, f)

    def set_record_and_check_if_modified(self, id: str, name: str, record_list: list):
        """
        Check if data has changed on dataset that is not complementary. Records also existence of the record,
        which is necessary due to file maintenance.
        :param id: the record ID used to identify what record list to compare against in the hash guard history
        :param name: name stored in the guard, for convenience
        :param record_list: any value that, when stringified, properly captures the data contents (e.g. it is not
           serialized as Class object at <...> etc.)
        :return:
        """
        hash_record = self.get(id, name)
        hash_value = False
        if hash_record is not None and type(hash_record) != str:
            hash_value = hash_record.get("hash", None)
        current_hash = compute_hash(record_list)

        if hash_record is not None and hash_value == current_hash:
            # Return False if not modified (false if versions equal)
            return hash_record.get("version", "") != VERSION
        self.update(id, name, current_hash)
        return True

    def get_complementary_id(self, id):
        return f"c-rec-{id}"

    def set_complementary_record_and_check_if_updated(self, id: str, name: str, context_name: str, definition_list: list):
        """
        Record existence of complementary dataset - these have no native data and thus
        do not support set_record_and_check_if_modified()
        :param id: the record ID used to identify what record list to compare against in the hash guard history
        :param name: name stored in the guard, for convenience
        :param context_name: name of the complementary dataset context (parent name)
        :return:
        """
        key = self.get_complementary_id(id)
        item = self.hashes.get(key, None)
        # Modified if item missing (=> force generate) or version changed
        modified = True if item is None else item.get("version", "") != VERSION

        if item and (item["name"] != name or item["context_name"] != context_name):
            # If exists & renamed, add outdated entry so it gets cleaned
            self.hashes[f"{key}_{time.time()}"] = {
                "name": item["name"],
                "context_name": item["context_name"],
                "hash": item["hash"],
                "stamp": 0,
                "version": VERSION
            }
            modified = True

        current_hash = compute_hash(definition_list)
        if not modified and item.get("hash") != current_hash:
            modified = True

        self.hashes[key] = {
            "name": name,
            "context_name": context_name,
            "hash": current_hash,
            "stamp": self.stamp,
            "version": VERSION
        }
        return modified

    def complementary_processing_file_root(self, id):
        return self.processing_file_root(self.get_complementary_id(id))

    def complementary_saving_file_root(self, id, parent_folder):
        return self.saving_file_root(self.get_complementary_id(id), parent_folder)

    def processing_file_root(self, id_or_item):
        return self.saving_file_root(id_or_item, ".temp")

    def saving_file_root(self, id_or_item, parent_folder):
        item = self.hashes[id_or_item] if type(id_or_item) != dict else id_or_item
        context_name = item.get("context_name")
        folder_path = parent_folder if context_name is None else f"{parent_folder}/{context_name}"
        folder_path = f"{folder_path}/{item['name']}/"
        os.makedirs(folder_path, exist_ok=True)
        return folder_path


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
                  "properties": {}, "type": ""})

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

        elif key == 'doushi':
            if value not in ["ichidan", "godan", "tadoushi", "jidoushi"]:
                print(" --parse-- Invalid value for verb property: ", value)
            else:
                verb_props = dict_read_create(item["properties"], "verb", [])
                verb_props.append(Value(value, key_significance, data_format))

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


def delete_filesystem_node(node):
    if os.path.exists(node):
        if os.path.isdir(node):
            shutil.rmtree(node)
        else:
            os.remove(node)


def merge_trees(source, target):
    """
    Merge the directory tree of `source` into `target`. Files in `source` replace those in `target`.
    """
    if not os.path.exists(source):
        raise ValueError(f"Source directory '{source}' does not exist.")

    if not os.path.exists(target):
        os.makedirs(target)

    for root, dirs, files in os.walk(source):
        relative_path = os.path.relpath(root, source)
        target_root = os.path.join(target, relative_path)
        os.makedirs(target_root, exist_ok=True)

        # Replace files in the target
        for file_name in files:
            source_file = os.path.join(root, file_name)
            target_file = os.path.join(target_root, file_name)
            shutil.copy2(source_file, target_file)  # Replace file in target

        for dir_name in dirs:
            target_subdir = os.path.join(target_root, dir_name)
            os.makedirs(target_subdir, exist_ok=True)



def get_smart_label(title, details, color="#d73a49"):
    return f"""
<span onclick="this.querySelector('span').style.display = (this.querySelector('span').style.display === 'none' || this.querySelector('span').style.display === '') ? 'block' : 'none';" style="display: inline-block; background-color: {color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; font-family: Arial, sans-serif; cursor: pointer; position: relative; margin-right: 8px;">
    {title}
    <span style="display: none; position: absolute; top: 120%; left: 0; background-color: white; color: black; border: 1px solid {color}; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-family: Arial, sans-serif; z-index: 10; min-width: 150px;">
        {details}
    </span>
</span>    
"""


def verb_prop_html(prop):
    match str(prop):
        case "ichidan":
            return get_smart_label("ichidan (る)", "Sloveso má pouze jeden tvar, při skloňování většinou odpadá ~る přípona.")
        case "godan":
            return get_smart_label("godan (..う)", "Sloveso má pět tvarů jako je pět samohlášek, pro skloňování mají dle typu koncovky různá pravidla.")
        case "jidoushi":
            return get_smart_label("tranzitivní", "neboli 'tadoushi', sloveso může popisovat předmět (postavili budovu)")
        case "tadoushi":
            return get_smart_label("netranzitivní", "neboli 'jidoushi', sloveso popisuje podmět (budova byla postavena)")
    raise ValueError(f"Property does not allowed in verbs: {prop}")