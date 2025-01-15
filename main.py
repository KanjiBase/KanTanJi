import traceback
from pathlib import Path
import os
import copy

from src.utils import (process_row, HashGuard, delete_filesystem_node, merge_trees, hash_id, dict_read_create,
                       sort_kanji_set, KanjiEntry, parse_ids, find_kanji, DataSet, sort_kanji_keys)
from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data

from src.pdf_generator import generate as generate_pdf
from src.anki_generator import generate as generate_anki
from src.html_generator import generate as generate_html

DataSet.register_processor("Anki Decks", generate_anki)
DataSet.register_processor("PDF Materials", generate_pdf)
DataSet.register_processor("HTML Kanji Pages", generate_html)


def try_read_data(getter, message, output, success_read):
    if not success_read:
        try:
            print(message)
            out = getter()
            return out, getter.__name__
        except FileNotFoundError:
            pass
    return output, success_read


# Read data provides in desired order here

success_read_method = None
data = None

# Google Sheets API
data, success_read_method = try_read_data(read_sheets_google_api,
                                          "Google Services: Reading data...", data, success_read_method)

# Fallback test data
uses_test_data = not success_read_method
data, success_read_method = try_read_data(read_local_data,
                                          "No data provider configured: using local test demo data.", data,
                                          success_read_method)

if not success_read_method:
    print("Error: Unable to read input data!")
    exit(1)

if not data:
    print("No data found to process: all is up to date.")
    exit(0)

# Create hash guard in the context of method that succeeded reading the input data
data_modification_guard = HashGuard(success_read_method)
_data_ = DataSet("default")
_data_.set_is_default()
default_dataset = _data_.data
parsed_metadata = {}
complementary_datasets = {}
for dataset_name in data:
    structured_output = {}
    entry = data[dataset_name]

    # Publish object ignored
    if dataset_name.lower() == "publish":
        continue

    for row in entry["data"]:
        try:
            item = process_row(row)

            if not item:
                continue

            id = str(item['id'])
            ttype = item['type']
            if ttype == 'kanji' or ttype == 'tango':
                node = structured_output.get(id)
                if node is None:
                    node = KanjiEntry()
                    structured_output[id] = node

                if ttype == "kanji":
                    node.set_kanji(item)
                else:
                    node.add_vocabulary_entry(item)

            elif ttype == 'dataset':
                node = complementary_datasets.get(id)
                if node is None:
                    node = DataSet()
                    complementary_datasets[id] = node
                ids = item.get("ids")
                set_name = str(item.get("dataset"))
                if set_name is None:
                    print(" --parse dataset-- Error dataset without name!")
                    continue

                if ids is not None:
                    node.data[hash_id(set_name)] = item
                else:
                    node.context_name = set_name

            else:
                # custom type, add to the dataset
                dataset = parsed_metadata.get(ttype)
                if not dataset:
                    dataset = ([], [])
                    parsed_metadata[ttype] = dataset
                dataset[0].append(item)
                dataset[1].append(row)

        except Exception as e:
            print(f"Error on line {row}", e)
            print(traceback.format_exc())

    if len(structured_output):
        # Checking on 'output' never yields the same hash, there is dynamic content
        modified = data_modification_guard.set_record_and_check_if_modified(entry["id"], entry["name"], entry["data"])

        key_order = sort_kanji_set(structured_output)
        print(f"Loaded dataset {dataset_name} - {'needs update' if modified else 'unchanged'}.")
        default_dataset[dataset_name] = {
            "id": entry["id"],
            "name": entry["name"],
            "content": structured_output,
            "order": key_order,
            "modified": modified
        }
    else:
        print(f"Skipping {dataset_name} - not a data source.")

# Now parse datasets if any
for did in complementary_datasets:
    dataset = complementary_datasets[did]
    name = dataset.context_name

    incremental_id = 1
    for dsid in dataset.data:
        data_subset = dataset.data[dsid]
        subset_name = str(data_subset["dataset"])
        modified = False
        output = {}
        try:
            order = parse_ids(str(data_subset["ids"]))
            for kanji_id in order:
                kanji, parent_set = find_kanji(default_dataset, kanji_id)
                if kanji is None:
                    raise ValueError(f"Invalid kanji ID {kanji_id} in dataset {name} > {subset_name}.")
                modified = modified or parent_set["modified"]

                # Updates are consistent, e.g. anki packs use GUID which does not change. Here we create
                # IDs that follow definition order in the dataset.
                kanji_copy = copy.copy(kanji)
                kanji_copy["id"] = incremental_id
                output[str(kanji_copy["id"])] = kanji_copy
                incremental_id += 1

            # Modification can also be caused by name change
            modified = data_modification_guard.set_complementary_record(dsid, subset_name, name) or modified
            dataset.data[dsid] = {
                "id": dsid,
                "name": subset_name,
                "content": output,
                "order": sort_kanji_keys(output),
                "modified": modified
            }

        except Exception as e:
            print(f" --parse dataset-- Error: dataset {subset_name} ignored", e)

data = _data_
del default_dataset, _data_

metadata = {}
# Compute guard also for metadata
for name in parsed_metadata:
    metadata_entries, original_metadata = parsed_metadata[name]
    metadata[name] = {
        "name": name,
        "content": metadata_entries,
        "modified": data_modification_guard.set_record_and_check_if_modified(name, name, original_metadata)
    }
del parsed_metadata

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
"""

os.makedirs(".temp", exist_ok=True)
# First process the default data
data.process(metadata=metadata, guard=data_modification_guard)
# Then process all datasets
for dataset in complementary_datasets:
    complementary_datasets[dataset].process(metadata=metadata, guard=data_modification_guard)

target_folder_to_output = None
readme_contents = {}


def clean_files(item, outdated):
    global target_folder_to_output, metadata, readme_contents
    try:
        # Skip metadata - do not create such files
        name = item["name"]
        if not outdated and name in metadata:
            return

        source = data_modification_guard.processing_file_root(item)
        target = data_modification_guard.saving_file_root(item, target_folder_to_output)

        if outdated:
            delete_filesystem_node(source)
            delete_filesystem_node(target)
            print("Removing ", name, source, target)
        else:
            merge_trees(source, target)
            delete_filesystem_node(source)
            print("Moving ", name, source, target)

            context = item["context_name"]
            if context is None:
                context = ""

            node = dict_read_create(readme_contents, context, [])
            node.append(target)

    except Exception as e:
        print(f"ERROR: Could not clean files for {item}", e)
        print(traceback.format_exc())


def get_readme_contents():
    global readme_contents, target_folder_to_output
    pdf_file_entries = {}
    anki_file_entries = {}
    html_file_entries = {}

    abs_target_folder_to_output = os.path.abspath(target_folder_to_output)

    def create_dataset_readme(path_root, file_list, set_name, item_name):
        if not path_root or path_root == ".":
            path_root = target_folder_to_output
        else:
            path_root = f"{target_folder_to_output}/{path_root}"

        if len(file_list) > 1:
            output = f"""
<details>
  <summary>
  {set_name} {Path(file_list[0]).parent.name}
  </summary>
            """
            for file in file_list:
                output += f"\n  - <a href=\"{path_root}/{file}\">{item_name} {Path(file).stem}</a>\n"

            output += "</details>"
            return output
        if len(file_list) == 1:
            return f" - <a href=\"{path_root}/{file_list[0]}\">{set_name} {Path(file_list[0]).stem}</a>\n"
        raise ValueError("Invalid Dataset!")

    # todo move file iteration to generators too
    for dataset_name in readme_contents:
        paths = readme_contents[dataset_name]

        pdf_files_readme = dict_read_create(pdf_file_entries, dataset_name, [])
        anki_files_readme = dict_read_create(anki_file_entries, dataset_name, [])
        html_files_readme = dict_read_create(html_file_entries, dataset_name, [])

        path_roots = [os.path.relpath(
            abs_target_folder_to_output, os.path.commonpath([abs_target_folder_to_output, os.path.abspath(x)])
        ) for x in paths]
        pdf_files = [list(Path(x).glob('**/*.pdf')) for x in paths]
        anki_files = [list(Path(x).glob('**/*.apkg')) for x in paths]
        html_files = [list(Path(x).glob('**/*.html')) for x in paths]

        if len(pdf_files):
            for i in range(len(path_roots)):
                pdf_files_readme.append(create_dataset_readme(path_roots[i], pdf_files[i], "Sada", ""))

        if len(anki_files):
            for i in range(len(path_roots)):
                anki_files_readme.append(create_dataset_readme(path_roots[i], anki_files[i], "Balíček", ""))

        if len(html_files):
            for i in range(len(path_roots)):
                html_files_readme.append(create_dataset_readme(path_roots[i], html_files[i], "Sada", "Kanji"))

    output_readme = {}
    for dataset_name in readme_contents:
        pdfs = '\n'.join(pdf_file_entries[dataset_name])
        ankis = '\n'.join(anki_file_entries[dataset_name])
        htmls = '\n'.join(html_file_entries[dataset_name])
        dataset_name_title = f"## {dataset_name}" if dataset_name else ""

        output_readme[dataset_name] = f"""
{dataset_name_title}

### PDF Materiály
PDF Soubory obsahují seznam znaků kanji a přidružených slovíček.
{pdfs}

### ANKI Balíčky
Balíčky lze importovat opakovaně do ANKI aplikace. Balíčky se řadí do kolekce 'KanTanJi' 
a umožňují chytré a interaktivní procvičování kanji.
{ankis}

### HTML
HTML Stránky slouží pro vložení interaktivních informací o Kanji do externích webových služeb.
{htmls}
"""
    return output_readme


if not uses_test_data:
    target_folder_to_output = "static"
    data_modification_guard.for_each_entry(clean_files)

    contents = get_readme_contents()
    default_content = contents[""]
    other_contents = []
    del contents[""]

    for dataset_name in contents:
        dataset_readme = target_folder_to_output + "/" + dataset_name + ".md"
        with open(dataset_readme, mode='w+', encoding='utf-8') as file:
            file.write(readme + contents[dataset_name])
        other_contents.append(f"- <a href=\"{dataset_readme}\">{dataset_name}</a>")

    if len(other_contents):
        other_contents = "\n\n ## Další Dostupné Sady \n Trénování Kanji v jiném pořadí.\n" + "\n".join(other_contents)
    else:
        other_contents = ""

    # Write the README.md with links to the PDF files
    with open("README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + default_content + other_contents)

    print("README.md updated with links.")
else:
    target_folder_to_output = ".test"
    data_modification_guard.for_each_entry(clean_files)
    print("Skipping writing README.md: test mode.")

    contents = get_readme_contents()
    default_content = contents[""]
    other_contents = []
    del contents[""]

    for dataset_name in contents:
        dataset_readme = target_folder_to_output + "/" + dataset_name + ".md"
        with open(dataset_readme, mode='w+', encoding='utf-8') as file:
            file.write(readme + contents[dataset_name])
        other_contents.append(f"- <a href=\"{dataset_readme}\">{dataset_name}</a>")

    if len(other_contents):
        other_contents = "\n\n ## Další Dostupné Sady \n Trénování Kanji v jiném pořadí.\n" + "\n".join(other_contents)
    else:
        other_contents = ""

    # Write the README.md with links to the PDF files
    with open(".TEST-README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + default_content + other_contents)

data_modification_guard.save()
