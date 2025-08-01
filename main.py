import argparse
import traceback
from pathlib import Path
import os
import copy

from src.logging_utils import set_logging, get_logger
parser = argparse.ArgumentParser(description="Kantanji: Generate Learning Sets from tabular data.")
parser.add_argument("--dry-run", action='store_true', help="If true, all dataset is processed, no output written.")
parser.add_argument("--log-file", type=str, help="If set to path, logs are stored to a file.")

args = parser.parse_args()

dry_run = bool(args.dry_run or os.getenv("KANTANJI_DRY_RUN"))
set_logging(production=not dry_run, output_file=args.log_file)
logger = get_logger()

# Do imports after initialization
from src.config import OVERRIDE_VOCAB_SIGNIFICANCE
from src.utils import process_row, dict_read_create, parse_ids
from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data
# For some reason, when src. is added as prefix the code fails to run due mismatches on class types
from utils_data_entitites import DataSet, KanjiEntry, Value, HashGuard
from utils_filesystem import merge_trees, delete_filesystem_node

# from src.pdf_generator import generate as generate_pdf
from src.anki_generator import generate as generate_anki
from src.html_pdf_generator import generate as generate_pdf2
from src.html_generator import generate as generate_html
from src.json_generator import generate as generate_json


DataSet.set_mode_production(not dry_run)

DataSet.register_processor("Anki Decks", generate_anki)
# DataSet.register_processor("PDF Materials", generate_pdf)
DataSet.register_processor("PDF Materials", generate_pdf2)
DataSet.register_processor("HTML Kanji Pages", generate_html)
DataSet.register_processor("JSON Data Bundle", generate_json)

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

            elif ttype == 'dataset' or ttype == 'subset':
                id = str(item["id"])
                node = complementary_datasets.get(id)
                if node is None:
                    node = DataSet(id)
                    complementary_datasets[id] = node
                set_name = str(item.get("setto"))
                if set_name is None:
                    print(" --parse dataset-- Error dataset without name!")
                    continue

                # Although we respect significance level on sets, we still need to register it here, just avoid rendering resources
                if ttype == 'subset':
                    subset_id = str(item.get("subid"))
                    if subset_id is None:
                        print(" --parse dataset-- Error data subset without sub-id!")
                        continue
                    node.append(subset_id, (item, row))
                else:
                    node.set_context_name(set_name, item.get("kijutsu"))

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

    logger.info("Prepare: Dataset %s (%s)", name, did)

    for dsid in dataset.data_range():
        data_subset, original_row = dataset.data[dsid]
        subset_name_item = data_subset.get("setto")
        subset_name = str(subset_name_item)
        kanjis_modified = False
        output = {}
        output_order = []

        logger.info(" Prepare: Subset %s (%s)", subset_name, dsid)

        try:
            order = parse_ids(data_subset["ids"])
            ignored = subset_name_item.significance > 0

            for kanji_id in order:
                kanji = kanji_dictionary.get(kanji_id)

                if kanji is None:
                    if not ignored:
                        print(
                            f" --parse dataset-- Error: kanji {kanji_id} undefined for dataset {name} > {subset_name}. Skipping...")
                    # Preserve order by increasing the numeric value, then ignore this entry
                    logger.info("  Kanji: %s ignored or invalid.", kanji_id)

                    incremental_id += 1
                    continue

                if not kanji.filled:
                    if not ignored:
                        print(f" --parse dataset-- Error: kanji {kanji_id} in dataset {name} > {subset_name}"
                              f"- kanji not explicitly defined, although vocabulary item might be. Skipping...")
                    # Preserve order by increasing the numeric value, then ignore this entry

                    kanji_id = kanji.set_or_get_context_id(did, incremental_id)
                    if kanji_id == incremental_id:
                        logger.info("  Kanji: %s not filled. Increment ID: %d.", kanji_id, incremental_id)
                        incremental_id += 1
                    else:
                        logger.info("  Kanji: %s not filled - but already encountered.", kanji_id)
                    continue

                # Do not optimize! get_was_modified must run to create entires!
                # If ignored, prevent from recording in the timestamp (problems with files, readme generating, etc.)
                kanjis_modified = not ignored and kanji.get_was_modified(data_modification_guard) or kanjis_modified

                # Kanji is linked to kanji_dictionary by the kanji letter, store context-dependent shared ID
                kanji_dataset_id = kanji.set_or_get_context_id(did, incremental_id)

                # Updates are consistent, e.g. anki packs use GUID which does not change. Here we create
                # IDs that follow definition order in the dataset.
                kanji_copy = copy.deepcopy(kanji)

                kanji_copy["id"] = Value(kanji_dataset_id)

                str_id = str(kanji_dataset_id)
                output[str_id] = kanji_copy
                output_order.append(str_id)

                # Increment only if used
                if kanji_dataset_id == incremental_id:
                    logger.info("  Kanji: %s: Setting increment ID: %d.", kanji_id, incremental_id)
                    incremental_id += 1
                else:
                    logger.info("  Kanji: %s: Already encountered before.", kanji_id)


            dataset_order = str(data_subset.get("junban", None))
            if not dataset_order:
                dataset_order = None
            # Modification can also be caused by name change
            # If ignored, prevent from recording in the timestamp (problems with files, readme generating, etc.)
            modified = not ignored and data_modification_guard.set_complementary_record_and_check_if_updated(
                dsid, subset_name, did, name, original_row, dataset_order)

            dataset.overwrite(dsid, {
                "id": dsid,
                "context_id": did,
                "name": subset_name,
                "content": output,
                "order": output_order,
                "modified": modified or kanjis_modified,
                "ignored": ignored
            })

        except Exception as e:
            del complementary_datasets[did]
            print(f" --parse dataset-- Error: dataset {subset_name} ignored", e)

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

#### Filtrování karet Anki

Karty KanTanJi lze snadno filtrovat pomocí **tagů**. V současnosti jsou k dispozici tagy:

 - **KanTanJi_Kanji** (karta s kanji)
 - **KanTanJi_Tango** (slovní zásoba související s kanji)
 - **KanTanJi_Learn_Now** (slovní zásoba obsahující pouze kanji, která již byla naučena)
 - **KanTanJi_Learn_Deck** (slovní zásoba obsahující kanji, která se bude učit v aktuálním balíčku)
 - **KanTanJi_Learn_Future** (slovní zásoba obsahující kanji, která ještě nebyla naučena)

Pokud chcete například odstranit všechny karty s kanji a příliš obtížnou slovní zásobu obsahující kanji, 
která ještě nebyla naučena podle pořadí KanTanJi, můžete **pozastavit** karty s tagy 
'KanTanJi_Kanji' a 'KanTanJi_Learn_Future'.

Nejprve v aplikaci Anki **otevřete Prohlížení karet (Browse Cards)**. Poté v možnostech vyberte **filtrovat podle tagu**.
Když jsou zobrazeny pouze požadované karty, opět v možnostech zvolte **vybrat všechny karty** 
a nakonec také v možnostech vyberte **pozastavit (suspend)**.

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


def clean_files(id, item, outdated):
    global target_folder_to_output, metadata, readme_contents, dry_run
    try:
        # Skip no context_name elements - do not create such files
        if not item["context_name"] or dry_run:
            return
        source = data_modification_guard.processing_file_root(item)
        target = data_modification_guard.saving_file_root(item, target_folder_to_output)

        if outdated:
            # Do not delete source, sources will not be committed in github actions
            delete_filesystem_node(target)
            print("Removing ", name, source, target)
        else:
            Path(source).glob('**/*')
            merge_trees(source, target)
            delete_filesystem_node(source)
            print("Moving ", name, source, target)

            context = item["context_id"]
            if context is not None:
                node = dict_read_create(readme_contents, context, [])
                node.append({
                    "path": target,
                    "item": item
                })

    except Exception as e:
        print(f"ERROR: Could not clean files for {item}", e)
        print(traceback.format_exc())


def get_readme_contents():
    global readme_contents, target_folder_to_output
    pdf_file_entries = {}
    anki_file_entries = {}
    html_file_entries = {}
    json_file_entries = {}

    def create_dataset_readme(file_list, set_name, item_name=None):
        if not item_name and len(file_list) > 1:
            return (f"\n#### {set_name} {Path(file_list[0]).parent.name}\n" +
                    "  ".join(map(lambda f: f"<a href=\"{f}\">{Path(f).stem}</a>", file_list)))

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

    def get_sort_attr(x):
        try:
            return int(x['item'].get('junban', 0))
        except (ValueError, TypeError):
            return 0

    # todo move file iteration to generators too
    for dataset_id in readme_contents:
        elements = readme_contents[dataset_id]
        elements = sorted(elements, key=get_sort_attr)

        pdf_files_readme = dict_read_create(pdf_file_entries, dataset_id, [])
        anki_files_readme = dict_read_create(anki_file_entries, dataset_id, [])
        html_files_readme = dict_read_create(html_file_entries, dataset_id, [])
        json_files_readme = dict_read_create(json_file_entries, dataset_id, [])

        pdf_files = [list(Path(x["path"]).glob('**/*.pdf')) for x in elements]
        anki_files = [list(Path(x["path"]).glob('**/*.apkg')) for x in elements]
        html_files = [list(Path(x["path"]).glob('**/*.html')) for x in elements]
        json_files = [list(Path(x["path"]).glob('**/*.json')) for x in elements]

        if len(pdf_files):
            for file_list in pdf_files:
                pdf_files_readme.append(create_dataset_readme(file_list, "PDF Seznam", ""))

        if len(anki_files):
            for file_list in anki_files:
                anki_files_readme.append(create_dataset_readme(file_list, "Balíček", ""))

        if len(html_files):
            for file_list in html_files:
                html_files_readme.append(create_dataset_readme(file_list, "Kanji Stránky"))

        if len(json_files):
            for file_list in json_files:
                json_files_readme.append(create_dataset_readme(file_list, "JSON Datový Balíček"))

    output_readme = {}
    for dataset_id in readme_contents:
        dataset = complementary_datasets[dataset_id]
        dataset_name = dataset.context_name

        pdfs = '\n'.join(filter(bool, pdf_file_entries[dataset_id]))
        ankis = '\n'.join(filter(bool, anki_file_entries[dataset_id]))
        htmls = '\n'.join(filter(bool, html_file_entries[dataset_id]))
        jsons = '\n'.join(filter(bool, json_file_entries[dataset_id]))
        dataset_title = f"## {dataset_name}" if dataset_name else dataset_id

        output_readme[dataset_id] = f"""
{dataset_title}
{dataset.description if dataset.description else ""}
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

### Datové Balíčky
Slouží pro import do dalších aplikací, například [Lively Wallpaper](https://github.com/KanjiBase/LivelyKanji).
{jsons}
"""
    return output_readme


if not uses_test_data and not dry_run:
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
