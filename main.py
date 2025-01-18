import traceback
from pathlib import Path
import os
import copy

from src.config import OVERRIDE_VOCAB_SIGNIFICANCE
from src.utils import process_row, hash_id, dict_read_create, parse_ids, sort_kanji_keys
from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data

from src.pdf_generator import generate as generate_pdf
from src.anki_generator import generate as generate_anki
from src.html_generator import generate as generate_html
from utils_data_entitites import DataSet, KanjiEntry, Value, HashGuard
from utils_filesystem import merge_trees, delete_filesystem_node

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

# Parsed values
parsed_metadata = {}
complementary_datasets = {}
kanji_dictionary = {}

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

            ttype = item['type']
            if ttype == 'kanji' or ttype == 'tango':
                id = str(item['kanji'])
                node = kanji_dictionary.get(id)
                if node is None:
                    # Need to re-import to fill in vocabulary items, they might come before kanji is defined
                    # or multiple kanji entries for the same kanji might be present
                    node = KanjiEntry()
                    kanji_dictionary[id] = node

                if ttype == "kanji":
                    if node.filled:
                        print(" -- parse -- ERROR: Kanji Redefinition, ignoring!", id)
                    else:
                        node.fill(item)
                        kanji_dictionary[str(item["kanji"])] = node
                else:
                    node.add_vocabulary_entry(item)

            elif ttype == 'dataset':
                id = str(item["id"])
                node = complementary_datasets.get(id)
                if node is None:
                    node = DataSet(id)
                    complementary_datasets[id] = node
                ids = item.get("ids")
                set_name = str(item.get("setto"))
                if set_name is None:
                    print(" --parse dataset-- Error dataset without name!")
                    continue

                if ids is not None:
                    node.data[hash_id(set_name)] = item, row
                else:
                    node.context_name = set_name

            else:
                # custom type, add to the dataset
                dataset = parsed_metadata.get(ttype)
                if not dataset:
                    dataset = []
                    parsed_metadata[ttype] = dataset
                dataset.append(item)

        except Exception as e:
            print(f"Error on line {row}", e)
            print(traceback.format_exc())



# Now parse datasets if any
for did in complementary_datasets:
    dataset = complementary_datasets[did]
    name = dataset.context_name

    incremental_id = 1
    for dsid in dataset.data:
        data_subset, original_row = dataset.data[dsid]
        subset_name = str(data_subset["setto"])
        kanjis_modified = False
        output = {}

        try:
            order = parse_ids(str(data_subset["ids"]))
            for kanji_id in order:
                kanji = kanji_dictionary.get(kanji_id)
                if kanji is None:
                    raise ValueError(f"Invalid kanji ID {kanji_id} in dataset {name} > {subset_name}.")

                # Do not optimize! get_was_modified must run to create entires!
                kanjis_modified = kanji.get_was_modified(data_modification_guard) or kanjis_modified

                # Kanji is linked to kanji_dictionary by the kanji letter, store context-dependent shared ID
                kanji.set_context_id(did, incremental_id)

                # Updates are consistent, e.g. anki packs use GUID which does not change. Here we create
                # IDs that follow definition order in the dataset.
                kanji_copy = copy.deepcopy(kanji)

                kanji_copy["id"] = Value(incremental_id)
                output[str(kanji_copy["id"])] = kanji_copy

                incremental_id += 1

            # Modification can also be caused by name change
            modified = data_modification_guard.set_complementary_record_and_check_if_updated(dsid, subset_name, did,
                                                                                             original_row)
            dataset.data[dsid] = {
                "id": dsid,
                "name": subset_name,
                "content": output,
                "order": sort_kanji_keys(output),
                "modified": modified or kanjis_modified
            }

        except Exception as e:
            del complementary_datasets[did]
            print(f" --parse dataset-- Error: dataset {subset_name} ignored", e)
            raise e


metadata = {}
# Compute guard also for metadata
for name in parsed_metadata:
    metadata_entries = parsed_metadata[name]
    metadata[name] = {
        "name": name,
        "content": metadata_entries,
        "modified": data_modification_guard.set_record_and_check_if_modified(name, name, metadata_entries)
    }
del parsed_metadata

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
"""

print()
print("Processing started...")
os.makedirs(".temp", exist_ok=True)

# Process all datasets
for dataset in complementary_datasets:
    compl_data = complementary_datasets[dataset]
    if OVERRIDE_VOCAB_SIGNIFICANCE:
        compl_data.adjust_vocabulary_significance(kanji_dictionary)
    compl_data.process(metadata=metadata, guard=data_modification_guard)

target_folder_to_output = None
readme_contents = {}


def clean_files(item, outdated):
    global target_folder_to_output, metadata, readme_contents
    try:
        # Skip no context_name elements - do not create such files
        if not item["context_name"]:
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

    def create_dataset_readme(file_list, set_name, item_name):
        if len(file_list) > 1:
            output = f"""
<details>
  <summary>
  {set_name} {Path(file_list[0]).parent.name}
  </summary>
            """
            for file in file_list:
                output += f"\n  - <a href=\"{file}\">{item_name} {Path(file).stem}</a>\n"

            output += "</details>"
            return output
        if len(file_list) == 1:
            return f" - <a href=\"{file_list[0]}\">{set_name} {Path(file_list[0]).stem}</a>\n"
        print("Warning: invalid dataset - no output files!", set_name, item_name)

    # todo move file iteration to generators too
    for dataset_name in readme_contents:
        paths = readme_contents[dataset_name]

        pdf_files_readme = dict_read_create(pdf_file_entries, dataset_name, [])
        anki_files_readme = dict_read_create(anki_file_entries, dataset_name, [])
        html_files_readme = dict_read_create(html_file_entries, dataset_name, [])

        pdf_files = [list(Path(x).glob('**/*.pdf')) for x in paths]
        anki_files = [list(Path(x).glob('**/*.apkg')) for x in paths]
        html_files = [list(Path(x).glob('**/*.html')) for x in paths]

        if len(pdf_files):
            for file_list in pdf_files:
                pdf_files_readme.append(create_dataset_readme(file_list, "Sada", ""))

        if len(anki_files):
            for file_list in anki_files:
                anki_files_readme.append(create_dataset_readme(file_list, "Balíček", ""))

        if len(html_files):
            for file_list in html_files:
                html_files_readme.append(create_dataset_readme(file_list, "Sada", "Kanji"))

    output_readme = {}
    for dataset_id in readme_contents:
        dataset = complementary_datasets[dataset_id]
        dataset_name = dataset.context_name

        pdfs = '\n'.join(pdf_file_entries[dataset_id])
        ankis = '\n'.join(anki_file_entries[dataset_id])
        htmls = '\n'.join(html_file_entries[dataset_id])
        dataset_title = f"## {dataset_name}" if dataset_name else dataset_id

        output_readme[dataset_id] = f"""
{dataset_title}

### PDF Materiály
PDF Soubory obsahují seznam znaků kanji a přidružených slovíček.
{pdfs}

### ANKI Balíčky
Balíčky lze importovat opakovaně do ANKI aplikace. Balíčky se řadí do kolekce 'KanTanJi' 
a umožňují chytré a interaktivní procvičování kanji. Balíček obsahuje jak kanji (poznáš podle
toho, že karta otázky obsahuje link na KanjiAlive), tak slovní zásobu ke kanji.
Furiganu zobrazíš kliknutím / tapnutím na kartičku.
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
    readme_output = []

    for dataset_id in contents:
        dataset_readme = dataset_id + ".md"
        dataset = complementary_datasets[dataset_id]
        dataset_name = dataset.context_name

        # Github pages renders nicely by default only README.md :/ cram into one file

        # with open(dataset_readme, mode='w+', encoding='utf-8') as file:
        #     file.write(readme + contents[dataset_id])
        # readme_output.append(f"- <a href=\"{dataset_readme}\">{dataset_name}</a>")
        readme_output.append(contents[dataset_id])

    # if len(readme_output):
    #     readme_output = "\n\n ## Dostupné Sady \n" + "\n".join(readme_output)
    # else:
    #     readme_output = "Nejsou žádné dostupné sady. Dataset není definován!"
    readme_output = "\n\n\n".join(readme_output)

    # Write the README.md with links to the PDF files
    with open("README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + readme_output)

    print("README.md updated with links.")
else:
    target_folder_to_output = ".test"
    data_modification_guard.for_each_entry(clean_files)
    print("Skipping writing README.md: test mode.")

    contents = get_readme_contents()
    readme_output = []
    for dataset_id in contents:
        # In test mode, output to .test folder
        dataset_readme = target_folder_to_output + "/" + dataset_id + ".md"
        dataset = complementary_datasets[dataset_id]
        dataset_name = dataset.context_name

        with open(dataset_readme, mode='w+', encoding='utf-8') as file:
            file.write(readme + contents[dataset_id])
        readme_output.append(f"- <a href=\"{dataset_readme}\">{dataset_name}</a>")

    if len(readme_output):
        readme_output = "\n\n ## Dostupné Sady \n Trénování Kanji\n" + "\n".join(readme_output)
    else:
        readme_output = "Nejsou žádné dostupné sady. Dataset není definován!"

    # Write the README.md with links to the PDF files
    with open(".TEST-README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + readme_output)


data_modification_guard.save()
