import json

def read_local_data():

    out = {}
    with open('misc/test-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        key = "kanji"
        out[key] = {
            "data": data,
            "id": key,
            "name": key
        }

    # radicals table
    with open('misc/test-radicals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        key = "radical"
        out[key] = {
            "data": data,
            "id": key,
            "name": key
        }

    # testing complementary datasets
    with open('misc/test-data-set.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        key = "complementary-set"
        out[key] = {
            "data": data,
            "id": key,
            "name": key
        }

    with open('misc/real-set-test-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        key = "real-data"
        out[key] = {
            "data": data,
            "id": key,
            "name": key
        }

    return out
