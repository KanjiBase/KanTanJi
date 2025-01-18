import os
import json
import time

from config import VERSION
from utils import compute_hash

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