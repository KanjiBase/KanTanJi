import traceback
from pathlib import Path
import os
import shutil

from src.pdf_generator import generate as generate_pdf
from src.anki_generator import generate as generate_anki
from src.html_generator import generate as generate_html
from src.utils import process_row, HashGuard, check_records_need_update

from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data


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
                                   "No data provider configured: using local test demo data.", data, success_read_method)

if not success_read_method:
    print("Error: Unable to read input data!")
    exit(1)

if not data:
    print("No data found to process: all is up to date.")
    exit(0)


# Create hash guard in the context of method that succeeded reading the input data
data_modification_guard = HashGuard(success_read_method)
parsed_data = {}
parsed_metadata = {}
for dataset_name in data:
    output = []
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
                output.append(item)
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

    if len(output):
        output.sort(key=lambda x: str(x["id"]) + x["type"])
        parsed_data[dataset_name] = {
            "name": entry["name"],
            "content": output,
            "modified": check_records_need_update(entry["id"], entry["name"], output, data_modification_guard)
        }
data = parsed_data
del parsed_data

metadata = {}
# Compute guard also for metadata
for name in parsed_metadata:
    metadata_entries = parsed_metadata[name]
    metadata[name] = {
        "name": name,
        "content": metadata_entries,
        "modified": check_records_need_update(name, name, metadata_entries, data_modification_guard)
    }
del parsed_metadata

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
"""

def filepath_dealer(key):
    folder_path = f".temp/{key}/"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def move_file_path_dealer(key, parent_folder):
    folder_path = f"{parent_folder}/{key}/"
    return folder_path


os.makedirs(".temp", exist_ok=True)

for key in data:
    try:
        generate_anki(key, data[key], metadata, filepath_dealer)
        print(f"Anki cards have been successfully saved:", key)
    except Exception as e:
        print(f"Failed to write file", key, e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_pdf(key, data[key], metadata, filepath_dealer)
        print(f"PDF file generated:", key)
    except Exception as e:
        print(f"Failed to write file", key, e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_html(key, data[key], metadata, filepath_dealer)
        print(f"HTML files generated:   ", key)
    except Exception as e:
        print(f"Failed to write HTML for dataset", key, e)
        print(traceback.format_exc())


target_folder_to_output = None


def delete_filesystem_node(node):
    if os.path.exists(node):
        if os.path.isdir(node):
            shutil.rmtree(node)
        else:
            os.remove(node)

def clean_files(item, outdated):
    global target_folder_to_output, metadata
    try:
        name = item["name"]
        if not outdated and name not in data:
            return

        source = filepath_dealer(name)
        target = move_file_path_dealer(name, target_folder_to_output)
        print("Moving ", name, source, target)

        if outdated:
            delete_filesystem_node(source)
            delete_filesystem_node(target)
        else:
            delete_filesystem_node(target)
            # target_dir = os.path.dirname(target)
            # if target_dir:
            #     os.makedirs(target_dir, exist_ok=True)
            os.replace(source, target)
    except Exception as e:
        print(f"ERROR: Could not clean files for {item}", e)
        print(traceback.format_exc())


def get_readme_content():
    global target_folder_to_output
    readme = ""

    pdf_files = []
    anki_files = []
    html_files = []
    directory_list = [Path(x) for x in Path(target_folder_to_output).rglob('*') if x.is_dir()]
    for dir in directory_list:
        pdf_files.append(dir.glob("*.pdf"))
        anki_files.append(dir.glob("*.apkg"))
        html_files.append({
            "parent": dir.name,
            "data": dir.glob("*.html")
        })

    if len(pdf_files):
        readme += """
## PDF Sady Kanji:
"""
        files = [item for row in pdf_files for item in row]
        files.sort()

        for pdf_file in files:
            readme += f" - <a href=\"{target_folder_to_output}/{pdf_file.parent.name}/{pdf_file.name}\">Sada {pdf_file.parent.name}</a>\n"

    if len(anki_files):
        readme += """
## Anki Balíčky
"""
        files = [item for row in anki_files for item in row]
        files.sort()

        for anki_file in files:
            readme += f" - <a href=\"{target_folder_to_output}/{anki_file.parent.name}/{anki_file.name}\">Balíček {anki_file.parent.name}</a>\n"

    if len(html_files):
        readme += """
## HTML Materiály
"""
        html_files.sort(key=lambda x: x["parent"])

        for item in html_files:
            files = item["data"]
            readme += f"""
<details>
  <summary>
  Sada {item["parent"]}
  </summary>
"""
            for file in files:
                readme += f"  - <a href=\"{target_folder_to_output}/{file.parent.name}/{file.name}\">Kanji {file.stem}</a>\n"
            readme += "</details>"
    return readme


if not uses_test_data:
    target_folder_to_output = "static"
    data_modification_guard.for_outdated_entries(clean_files)

    # Write the README.md with links to the PDF files
    with open("README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + get_readme_content())
    print("README.md updated with links.")
else:
    target_folder_to_output = ".test"
    data_modification_guard.for_outdated_entries(clean_files)
    print("Skipping writing README.md: test mode.")
    print(readme + get_readme_content())

data_modification_guard.save()
