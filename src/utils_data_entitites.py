import re
import traceback
import hashlib
import os
import json
import time
from enum import Enum
from copy import copy

from config import VERSION



class Entry(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filled = False
        self._name = "Entry"

    def get_equal(self, target, significance_level=0):
        target = self.get(target)
        if type(target) == ValueList:
            return target.get_equal(significance_level)
        if type(target) == Value and target.significance == significance_level:
            return Value
        return None

    def get_below(self, target, below_significance):
        target = self.get(target)
        if type(target) == ValueList:
            return target.get_equal(below_significance)
        if type(target) == Value and target.significance >= below_significance:
            return Value
        return None

    def fill(self, other_dict):
        if not isinstance(other_dict, dict):
            raise TypeError("Fill entry argument must be a dict.")
        self["references"] = other_dict.get("references", {})
        self["extra"] = other_dict.get("extra", {})
        self.filled = True

    def __repr__(self):
        return f"{self._name}({super().__repr__()})"

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, Value):
            return str(value)
        return value


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

    def __json__(self):
        return str(self.value) + str(self.significance)


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

    def __json__(self):
        return str(self.value)


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



class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Value) or isinstance(obj, Version):
            return obj.__json__()
        return super().default(obj)


def compute_hash(records):
    hash_obj = hashlib.md5()
    serial = json.dumps(records, sort_keys=True, ensure_ascii=False, cls=CustomEncoder)
    hash_obj.update(serial.encode('utf-8'))
    return hash_obj.hexdigest()


class HashGuard:
    def __init__(self, context_name):
        self.hash_file_path = f"misc/update_guard_{context_name}.json"
        if os.path.exists(self.hash_file_path):
            with open(self.hash_file_path, 'r', encoding='utf-8') as f:
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
        Update the hash record of source file, this has no 'context_name'.
        """
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
        with open(self.hash_file_path, "w", encoding='utf-8') as f:
            json.dump(self.hashes, f, ensure_ascii=False)

    def set_kanji_record_and_check_if_modified(self, kanji):
        return self.set_record_and_check_if_modified(kanji["kanji"], "", kanji)

    def set_record_and_check_if_modified(self, id: str, name: str, record):
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
        current_hash = compute_hash(record)

        if hash_record is not None and hash_value == current_hash and hash_record.get("version", "") == VERSION:
            return False
        # Update even if version mismatch!
        self.update(id, name, current_hash)
        return True

    def get_complementary_id(self, id):
        return f"c-rec-{id}"

    def set_complementary_record_and_check_if_updated(self, id: str, name: str, context_name: str, record):
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

        current_hash = compute_hash(record)
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

    def processing_file_root(self, id_or_item):
        """Available only to complementary items!"""
        return self.saving_file_root(id_or_item, ".temp")

    def saving_file_root(self, id_or_item, parent_folder):
        """Available only to complementary items!"""
        item = self.hashes[self.get_complementary_id(id_or_item)] if type(id_or_item) != dict else id_or_item
        context_name = item.get("context_name")
        folder_path = parent_folder if context_name is None else f"{parent_folder}/{context_name}"
        folder_path = f"{folder_path}/{item['name']}/"
        os.makedirs(folder_path, exist_ok=True)
        return folder_path


class KanjiEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["_vocab_"] = []
        self._modif_flag = None
        self._context_ids = {}
        self._name = "KanjiEntry"

    def add_vocabulary_entry(self, value):
        if not isinstance(value, VocabEntry):
            raise ValueError("Argument must be a tango dict.")
        self.get("_vocab_").append(value)

    def vocabulary(self):
        return self.get("_vocab_")

    def set_or_get_context_id(self, context_id, id):
        exists_id = self._context_ids.get(context_id)
        if exists_id is not None:
            return exists_id
        self._context_ids[context_id] = id
        return id

    def get_context_id(self, context_id):
        return self._context_ids.get(context_id)

    def get_was_modified(self, guard: HashGuard):
        return self._modif_flag if self._modif_flag is not None else guard.set_kanji_record_and_check_if_modified(self)

    def sort_vocabulary(self):
        self.get("_vocab_").sort(key=lambda x: str(x["id"]) + str(x["tango"]))

    def fill(self, other_dict):
        """Extends the dictionary with key-value pairs from another dictionary."""
        super().fill(other_dict)

        self["type"] = "kanji"
        self["kanji"] = other_dict.get("kanji")
        self["imi"] = other_dict.get("imi")
        self["onyomi"] = ValueList(other_dict.get("onyomi", []))
        self["kunyomi"] = ValueList(other_dict.get("kunyomi", []))

        if isinstance(other_dict, KanjiEntry):
            self._modif_flag = other_dict._modif_flag

        self["guid"] = str(self["kanji"])

    # def __copy__(self):
    #     new_instance = type(self)(self)
    #     # Ensure vocab is also copied, we will modify the significance levels
    #     new_instance._vocab = [copy(vocab_entry) for vocab_entry in self._vocab]
    #     return new_instance


class VocabEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = "VocabEntry"

    def fill(self, other_dict):
        super().fill(other_dict)
        self["type"] = "tango"
        self["tango"] = other_dict.get("tango")
        self["imi"] = other_dict.get("imi")
        self["kanji"] = other_dict.get("kanji")
        self["tsukaikata"] = ValueList(other_dict.get("tsukaikata", []))
        self["raberu"] = ValueList(other_dict.get("raberu", []))

        self["guid"] = self["kanji"] + "." + self["tango"]


class RadicalEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def fill(self, other_dict):
        super().fill(other_dict)
        self["type"] = "radical"
        self["radical"] = other_dict.get("radical")
        self["id"] = other_dict.get("id")
        self["imi"] = other_dict.get("imi")
        self["kunyomi"] = ValueList(other_dict.get("kunyomi", []))

        self["guid"] = self["radical"]


class DatasetEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = "DatasetEntry"

    def fill(self, other_dict):
        super().fill(other_dict)
        self["type"] = "dataset"
        self["setto"] = other_dict.get("setto")
        self["id"] = other_dict.get("id")
        self["ids"] = other_dict.get("ids", None)

        self["guid"] = self["setto"]



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
                last_kanji_id = dataset[last_kanji_id].get_context_id(self.parent_context_id)

                for vocab in kanji.vocabulary():
                    try:
                        match_len = 0
                        match = re.findall(kanji_regex, vocab["tango"])
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
                            vocab.get("tango").significance = 2
                        elif match_len == len(match):
                            vocab.get("tango").significance = 0
                        else:
                            vocab.get("tango").significance = 1

                    except Exception as e:
                        vocab["_used_kanjis_"] = []
                        print("Error when dealing with vocab item in Kanji", kanji_id,
                              "skipping significance modification...",
                              e)

    def process(self, metadata, guard: HashGuard):
        for proc_name, processor in DataSet._processors:
            for key in self.data:
                data_spec = self.data[key]
                if data_spec["ignored"]:
                    continue

                name = data_spec["name"]
                output_path = guard.processing_file_root(data_spec["id"])

                try:
                    if processor(name, data_spec, metadata, lambda _: output_path):
                        print(f"[{name}]  {proc_name} - generated.")
                    else:
                        print(f"[{name}]  {proc_name} - unchanged.")
                except Exception as e:
                    print(f"Failed to write file to ", output_path, e)
                    print(traceback.format_exc())
