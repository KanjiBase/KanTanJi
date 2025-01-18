import re
import traceback
from enum import Enum
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


class KanjiEntry(Entry):
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