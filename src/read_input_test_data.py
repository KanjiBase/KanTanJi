import json


def read_local_data():
    with open('misc/test-data.json', 'r', encoding='utf-8') as f:
        return json.load(f)
