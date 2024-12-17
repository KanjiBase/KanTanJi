import json

from utils import HashGuard

def read_local_data():
    guard = HashGuard("test")
    with open('misc/test-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        key = "test-kanji"
        guard.update(key, key, "test")
        return {
            key: data
        }, guard
