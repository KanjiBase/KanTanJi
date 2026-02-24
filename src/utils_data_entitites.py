import re
import traceback
import hashlib
import os
import json
import time
from enum import Enum
from copy import copy

# Needs full path import - to load the same module as main that initialized it
from src.logging_utils import get_logger
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

    def update(self, key, name, hash_value, junban=None):
        """
        Update the hash record of source file, this has no 'context_name'.
        """
        record = {
            "id": key,
            "name": name,
            "context_name": None,
            "context_id": None,
            "hash": hash_value,
            "stamp": self.stamp,
            "version": VERSION
        }
        if junban is not None:
            record["junban"] = junban
        self.hashes[key] = record


    def invalidate_all(self):
        for key in self.hashes:
            item = self.hashes[key]
            item["stamp"] = ""

    def for_each_entry(self, clbck):
        outdated_hashes = []
        up_to_date_hashes = []
        for key in self.hashes:
            item = self.hashes[key]
            if item["stamp"] != self.stamp:
                outdated_hashes.append(key)
            else:
                up_to_date_hashes.append(key)

        print("Cleaning outdated:", outdated_hashes)
        for key in outdated_hashes:
            item = self.hashes[key]
            clbck(key, item, True)
            del self.hashes[key]
        # Run after outdated, which might delete files
        for key in up_to_date_hashes:
            item = self.hashes[key]
            clbck(key, item, False)

    def save(self):
        with open(self.hash_file_path, "w", encoding='utf-8') as f:
            json.dump(self.hashes, f, ensure_ascii=False)

    def set_kanji_record_and_check_if_modified(self, kanji):
        return self.set_record_and_check_if_modified(kanji["kanji"], "", kanji)

    def set_record_and_check_if_modified(self, id: str, name: str, record, junban=None):
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
        self.update(id, name, current_hash, junban)
        return True

    def get_complementary_id(self, id, context_id):
        if context_id is None:
            raise ValueError(f"Context ID must not be NONE! Accessed with: {id}")
        return f"c-{context_id}-{id}"

    def set_complementary_record_and_check_if_updated(self, id: str, name: str, context_id: str, context_name: str,
                                                      record, junban=None):
        """
        Record existence of complementary dataset - these have no native data and thus
        do not support set_record_and_check_if_modified()
        :param id: the record ID used to identify what record list to compare against in the hash guard history
        :param name: name stored in the guard, for convenience
        :param context_id: parent ID
        :param context_name: name of the complementary dataset context (parent name)
        :param record: value to evaluate for changes (against previous value in history)
        :return:
        """
        key = self.get_complementary_id(id, context_id)
        item = self.hashes.get(key, None)
        # Modified if item missing (=> force generate) or version changed
        modified = True if item is None else item.get("version", "") != VERSION

        if item and (item["name"] != name or item["context_name"] != context_name):
            # If exists & renamed, add outdated entry so it gets cleaned
            entry = {
                "id": id,
                "name": item["name"],
                "context_id": item["context_id"],
                "context_name": item["context_name"],
                "hash": item["hash"],
                "stamp": 0,
                "version": VERSION
            }
            if junban is not None:
                entry["junban"] = junban
            self.hashes[f"{key}_{time.time()}"] = entry
            modified = True

        current_hash = compute_hash(record)
        if not modified and item.get("hash") != current_hash:
            modified = True

        entry = {
            "id": id,
            "name": name,
            "context_name": context_name,
            "context_id": context_id,
            "hash": current_hash,
            "stamp": self.stamp,
            "version": VERSION
        }
        if junban is not None:
            entry["junban"] = junban
        self.hashes[key] = entry
        return modified

    def processing_file_root(self, id_or_item, parent_id=None):
        """Available only to complementary items!"""
        return self.saving_file_root(id_or_item, ".temp", parent_id)

    def saving_file_root(self, id_or_item, parent_folder, parent_id=None):
        """Available only to complementary items!"""
        item = self.hashes[self.get_complementary_id(id_or_item, parent_id)] if type(id_or_item) != dict else id_or_item
        context = item.get("context_id")
        folder_path = parent_folder if context is None else f"{parent_folder}/{context}"
        folder_path = f"{folder_path}/{item['id']}/"
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

    def set_or_get_context_id(self, context_id, dependent_id):
        exists_id = self._context_ids.get(context_id)
        if exists_id is not None:
            return exists_id
        dependent_id = int(dependent_id)
        self._context_ids[context_id] = dependent_id
        return dependent_id

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
        self["kijutsu"] = other_dict.get("kijutsu", None)
        self["guid"] = self["setto"]


class DataSubsetEntry(Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = "DataSubsetEntry"

    def fill(self, other_dict):
        super().fill(other_dict)
        self["type"] = "subset"
        self["setto"] = other_dict.get("setto")
        self["id"] = other_dict.get("id")
        self["subid"] = other_dict.get("subid")
        self["junban"] = other_dict.get("junban")
        self["ids"] = other_dict.get("ids", [])
        self["guid"] = f"{self['setto']}.{self['subid']}"


class DataSet:
    _processors = []
    _production = False

    def __init__(self, parent_context_id, context_name=None):
        if context_name is None:
            self.parent_context_id = parent_context_id
            self.context_name = parent_context_id
        else:
            self.context_name = context_name
            self.parent_context_id = parent_context_id
        self.description = None
        self.data = {}
        self.default = False
        self._order = None
        self._initialized = False

    def set_context_name(self, value, description=None):
        if self._initialized:
            raise ValueError(f"Redefinition of a set! {value}")
        self._initialized = True
        self.context_name = value
        self.description = description

    def is_initialized(self):
        return self._initialized

    def set_is_default(self):
        self.default = True

    def append(self, key, dataset):
        if self.data.get(key) is not None:
            raise ValueError(f"Redefinition of a subset! {key}")
        try:
            key = int(key)
        except (ValueError, TypeError):
            print("E: JunBan should be integer!", key, dataset["name"])
        self.data[key] = dataset
        self._order = None

    def overwrite(self, key, dataset):
        self.data[key] = dataset

    @staticmethod
    def register_processor(name: str, processor):
        DataSet._processors.append((name, processor))

    @staticmethod
    def set_mode_production(production: bool):
        DataSet._production = production

    def data_range(self):
        # TODO DIRTY: we are setting tuples (dict, orig data) as values and later overwriting by dict!
        if not self._order:
            # Access junban by .get() to avoid conversion to str
            self._order = [k for k, v in sorted(self.data.items(), key=lambda item: item[1][0].get('junban').value)]
        return self._order

    def adjust_vocabulary_significance(self, kanji_dictionary):
        # Here we deduct significance levels automatically for vocabulary entries, these
        # are dependent on whether they contain already learnt kanji
        kanji_regex = r'[\u4e00-\u9faf]|[\u3400-\u4dbf]|[々〆〇]'
        logger = get_logger()

        was_significance_test_configured = False
        per_dataset_id = False
        last_kanji_id = None

        for dataset_id in self.data_range():
            dataset_spec = self.data[dataset_id]
            dataset = dataset_spec["content"]

            # How to setup last_kanji_id: if we have more than 50 kanjis, let's keep it per subset
            #  else decide globally
            if not was_significance_test_configured:
                was_significance_test_configured = True
                per_dataset_id = len(dataset) < 50
                if not per_dataset_id:
                    last_spec = self.data[self.data_range()[-1]]
                    last_dataset = last_spec["content"]
                    last_kanji_id = last_dataset[last_spec["order"][-1]].get_context_id(self.parent_context_id)

                    if type(last_kanji_id) != int:
                        print(f"E: Attempt to derive last kanji for the whole dataset failed: invalid id or type: {last_kanji_id}", last_spec)


            logger.info("Adjust vocabulary: %s (%s) (per dataset: %s, last %s)",
                        dataset_spec["name"], dataset_id, per_dataset_id, last_kanji_id)

            for kanji_id in dataset:
                kanji = dataset[kanji_id]

                kanji_id = kanji.get_context_id(self.parent_context_id)
                if per_dataset_id:
                    # Find last in this set
                    last_kanji_id = dataset[dataset_spec["order"][-1]].get_context_id(self.parent_context_id)

                for vocab in kanji.vocabulary():
                    try:
                        match_len = 0
                        match = re.findall(kanji_regex, vocab["tango"])
                        ignore_reason = None
                        for m in match:
                            contains_kanji = kanji_dictionary.get(m)
                            contains_kanji_id = None if contains_kanji is None \
                                else contains_kanji.get_context_id(self.parent_context_id)

                            if contains_kanji_id is None:
                                ignore_reason = f"kanji {m} undefined"
                                break
                            if contains_kanji_id <= kanji_id:
                                match_len = match_len + 1
                            elif contains_kanji_id > last_kanji_id:
                                ignore_reason = f"kanji {m} in far lesson"
                                break

                        logger.info("  Tango: %s, matched %s, match length %d (r: %s)",
                                    vocab["tango"], match, match_len, ignore_reason)
                        if ignore_reason:
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
                        logger.error("Origin:", e)

    def process(self, metadata, guard: HashGuard, path_getter: callable = None):
        print("Generating:", self.context_name)
        for proc_name, processor in DataSet._processors:
            print(proc_name, end="...\n")
            self.process_using(processor, metadata, guard, path_getter)

    def process_using(self, processor: callable, metadata, guard: HashGuard, path_getter: callable):
        for key in self.data:
            data_spec = self.data[key]
            if data_spec["ignored"]:
                continue

            name = data_spec["name"]
            output_path = guard.processing_file_root(data_spec["id"], data_spec["context_id"]) \
                if path_getter is None else path_getter(data_spec["id"])

            try:
                if processor(name, data_spec, metadata, lambda _: output_path, not self._production):
                    print(f"[○ {name}]", end="")
                else:
                    print(f"[🞪 {name}]", end="")
                print()
            except Exception as e:
                print()
                print(f"Failed to write file to ", output_path, e)
                print(traceback.format_exc())
